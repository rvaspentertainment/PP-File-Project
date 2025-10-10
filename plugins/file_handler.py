from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.database import pp_bots
from helper.utils import (
    progress_for_pyrogram, humanbytes, convert,
    sanitize_filename, apply_word_removal, apply_word_replacement,
    clean_file, get_file_extension
)
from config import Config
from plugins.jai_bajarangabali import is_jai_bajarangabali_file, handle_jai_bajarangabali
from PIL import Image
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from bot import app
from datetime import datetime
import os
import time
import re
import asyncio
import logging


renaming_operations = {}

# Episode patterns
pattern1 = re.compile(r"S(\d+)(?:E|EP)(\d+)")
pattern2 = re.compile(r"S(\d+)\s*(?:E|EP|-\s*EP)(\d+)")
pattern3 = re.compile(r"(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)")
pattern3_2 = re.compile(r"(?:\s*-\s*(\d+)\s*)")
pattern4 = re.compile(r"S(\d+)[^\d]*(\d+)", re.IGNORECASE)
patternX = re.compile(r"(\d+)")

# Quality patterns
pattern5 = re.compile(r"\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b", re.IGNORECASE)
pattern6 = re.compile(r"[([<{]?\s*4k\s*[)\]>}]?", re.IGNORECASE)
pattern7 = re.compile(r"[([<{]?\s*2k\s*[)\]>}]?", re.IGNORECASE)
pattern8 = re.compile(r"[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b", re.IGNORECASE)
pattern9 = re.compile(r"[([<{]?\s*4kX264\s*[)\]>}]?", re.IGNORECASE)
pattern10 = re.compile(r"[([<{]?\s*4kx265\s*[)\]>}]?", re.IGNORECASE)


def extract_quality(filename):
    """Extract video quality from filename"""
    for pattern in [pattern5, pattern6, pattern7, pattern8, pattern9, pattern10]:
        match = re.search(pattern, filename)
        if match:
            if pattern == pattern5:
                return match.group(1) or match.group(2)
            elif pattern == pattern6:
                return "4k"
            elif pattern == pattern7:
                return "2k"
            elif pattern == pattern8:
                return "HdRip"
            elif pattern == pattern9:
                return "4kX264"
            elif pattern == pattern10:
                return "4kx265"
    return "Unknown"


def extract_episode_number(filename):
    """Extract episode number from filename"""
    for pattern in [pattern1, pattern2, pattern3, pattern3_2, pattern4, patternX]:
        match = re.search(pattern, filename)
        if match:
            if pattern == pattern1 or pattern == pattern2 or pattern == pattern4:
                return match.group(2)
            else:
                return match.group(1)
    return None


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_media_files(client, message: Message):
    """Main handler for all media files"""
    user_id = message.from_user.id
    
    # Get user settings
    media_mode = await pp_bots.get_media_mode(user_id)
    
    # Get file info
    if message.document:
        file = message.document
        filename = file.file_name
        file_size = file.file_size
        media_type = "document"
    elif message.video:
        file = message.video
        filename = file.file_name or "video.mp4"
        file_size = file.file_size
        media_type = "video"
    elif message.audio:
        file = message.audio
        filename = file.file_name or "audio.mp3"
        file_size = file.file_size
        media_type = "audio"
    else:
        return
    
    # Check for Jai Bajarangabali special handling
    if is_jai_bajarangabali_file(filename):
        return await handle_jai_bajarangabali(client, message)
    
    # Route to appropriate handler based on mode
    if media_mode == "rename":
        await handle_rename_mode(client, message, file, filename, file_size, media_type)
    elif media_mode == "trim":
        await handle_trim_mode(client, message, file, filename, file_size)
    elif media_mode == "extract":
        await handle_extract_mode(client, message, file, filename, file_size)
    elif media_mode == "merge":
        await handle_merge_mode(client, message, file, filename, file_size, media_type)
    elif media_mode == "compress":
        await handle_compress_mode(client, message, file, filename, file_size)
    elif media_mode == "autotrim":
        await handle_autotrim_mode(client, message, file, filename, file_size)


async def handle_rename_mode(client, message, file, filename, file_size, media_type):
    """Handle file renaming with templates or word replacement"""
    user_id = message.from_user.id
    format_template = await pp_bots.get_format_template(user_id)
    media_preference = await pp_bots.get_media_preference(user_id)
    upload_channel = await pp_bots.get_upload_channel(user_id)
    
    # Check file size
    max_size = Config.MAX_FILE_SIZE if (app and Config.STRING_SESSION) else Config.MAX_FILE_SIZE_NON_PREMIUM
    if file_size > max_size:
        size_gb = file_size / (1024 * 1024 * 1024)
        max_gb = max_size / (1024 * 1024 * 1024)
        return await message.reply_text(
            f"**❌ File Too Large!**\n\n"
            f"**File Size:** {size_gb:.2f} GB\n"
            f"**Maximum:** {max_gb:.2f} GB\n\n"
            f"{'💡 Add premium session for 4GB support' if not Config.STRING_SESSION else ''}"
        )
    
    # Check for duplicate processing
    file_id = file.file_id
    if file_id in renaming_operations:
        elapsed = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed < 10:
            return
    renaming_operations[file_id] = datetime.now()
    
    # Determine new filename
    _, file_extension = os.path.splitext(filename)
    
    if format_template:
        # Use template
        new_filename = format_template
        
        # Replace episode
        episode = extract_episode_number(filename)
        if episode:
            new_filename = new_filename.replace("[episode]", f"EP{episode}", 1)
        
        # Replace quality
        quality = extract_quality(filename)
        new_filename = new_filename.replace("[quality]", quality)
        
        new_filename = f"{new_filename}{file_extension}"
    else:
        # Use word removal/replacement
        remove_words = await pp_bots.get_remove_words(user_id)
        replace_words = await pp_bots.get_replace_words(user_id)
        
        # Check caption first
        if message.caption:
            # Check if caption has extension
            if any(message.caption.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']):
                new_filename = message.caption
            else:
                new_filename = filename
        else:
            new_filename = filename
        
        # Apply removals
        name_without_ext = os.path.splitext(new_filename)[0]
        name_without_ext = apply_word_removal(name_without_ext, remove_words)
        name_without_ext = apply_word_replacement(name_without_ext, replace_words)
        new_filename = f"{name_without_ext}{file_extension}"
    
    # Sanitize filename
    new_filename = sanitize_filename(new_filename)
    
    # Setup paths
    downloads_dir = "downloads"
    metadata_dir = "Metadata"
    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    
    renamed_file_path = os.path.join(downloads_dir, new_filename)
    metadata_file_path = os.path.join(metadata_dir, new_filename)
    
    # Download
    download_msg = await message.reply_text("📥 Downloading...")
    
    try:
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        path = await upload_client.download_media(
            message,
            file_name=renamed_file_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", download_msg, time.time())
        )
    except Exception as e:
        del renaming_operations[file_id]
        return await download_msg.edit(f"**❌ Download Error:** `{e}`")
    
    # Add metadata if enabled
    await download_msg.edit("🔄 Processing...")
    
    metadata_added = False
    _bool_metadata = await pp_bots.get_metadata(user_id)
    
    if _bool_metadata:
        metadata = await pp_bots.get_metadata_code(user_id)
        if metadata:
            cmd = f'ffmpeg -i "{renamed_file_path}" -map 0 -c:s copy -c:a copy -c:v copy -metadata title="{metadata}" -metadata author="{metadata}" -metadata:s:s title="{metadata}" -metadata:s:a title="{metadata}" -metadata:s:v title="{metadata}" "{metadata_file_path}"'
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(process.communicate(), timeout=300)
                
                if process.returncode == 0 and os.path.exists(metadata_file_path):
                    metadata_added = True
                    path = metadata_file_path
            except:
                pass
    
    if not metadata_added:
        path = renamed_file_path
    
    # Upload
    upload_msg = await download_msg.edit("📤 Uploading...")
    
    try:
        # Get caption
        c_caption = await pp_bots.get_caption(user_id)
        caption = c_caption.format(
            filename=new_filename,
            filesize=humanbytes(file_size),
            duration=convert(0)
        ) if c_caption else f"**{new_filename}**"
        
        # Get thumbnail
        ph_path = None
        c_thumb = await pp_bots.get_thumbnail(user_id)
        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and message.video and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)
        
        if ph_path:
            img = Image.open(ph_path).convert("RGB")
            img = img.resize((320, 320))
            img.save(ph_path, "JPEG")
        
        # Upload destination
        upload_to = upload_channel if upload_channel else message.chat.id
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        # Get media preference
        final_media_type = media_preference or media_type
        
        # Upload
        if final_media_type == "document":
            sent = await upload_client.send_document(
                upload_to,
                document=path,
                thumb=ph_path,
                duration=0,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        elif final_media_type == "audio":
            sent = await upload_client.send_audio(
                upload_to,
                audio=path,
                caption=caption,
                thumb=ph_path,
                duration=0,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        
        # Confirmation
        if upload_channel:
            try:
                channel_info = await client.get_chat(upload_channel)
                await upload_msg.edit(
                    f"**✅ Upload Complete!**\n\n"
                    f"**Uploaded to:** {channel_info.title}\n"
                    f"**File:** {new_filename}\n"
                    f"**Size:** {humanbytes(file_size)}"
                )
            except:
                await upload_msg.edit("**✅ Upload Complete!**")
        else:
            await upload_msg.delete()
        
        # Cleanup
        clean_file(ph_path)
        
    except Exception as e:
        await upload_msg.edit(f"**❌ Upload Error:** `{e}`")
    
    finally:
        clean_file(renamed_file_path)
        clean_file(metadata_file_path)
        if file_id in renaming_operations:
            del renaming_operations[file_id]


async def handle_trim_mode(client, message, file, filename, file_size):
    """Handle video trimming"""
    user_id = message.from_user.id
    
    await message.reply_text(
        "**✂️ Trim Mode Active**\n\n"
        "Please send start time (HH:MM:SS or MM:SS):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_trim")]
        ])
    )
    
    # Store file info for later processing
    # This will be handled by a separate listener


async def handle_extract_mode(client, message, file, filename, file_size):
    """Handle audio/subtitle extraction"""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_audio_{file.file_id}"),
            InlineKeyboardButton("📝 Extract Subtitles", callback_data=f"extract_subs_{file.file_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        "**🎵 Extract Mode**\n\n"
        "What do you want to extract?",
        reply_markup=keyboard
    )


async def handle_merge_mode(client, message, file, filename, file_size, media_type):
    """Handle file merging"""
    user_id = message.from_user.id
    
    # Add to merge queue
    file_info = {
        'file_id': file.file_id,
        'filename': filename,
        'size': file_size,
        'type': media_type,
        'message_id': message.id
    }
    
    await pp_bots.add_to_merge_queue(user_id, file_info)
    queue = await pp_bots.get_merge_queue(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done - Merge Now", callback_data="merge_now")],
        [InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_merge_queue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        f"**🔗 Merge Queue**\n\n"
        f"**Files in queue:** {len(queue)}\n"
        f"**Latest added:** {filename}\n\n"
        f"Send more files or click 'Done' to merge.",
        reply_markup=keyboard
    )


async def handle_compress_mode(client, message, file, filename, file_size):
    """Handle video compression"""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📺 1080p", callback_data=f"comp_1080p_{file.file_id}"),
            InlineKeyboardButton("📺 720p", callback_data=f"comp_720p_{file.file_id}")
        ],
        [
            InlineKeyboardButton("📺 576p", callback_data=f"comp_576p_{file.file_id}"),
            InlineKeyboardButton("📺 480p", callback_data=f"comp_480p_{file.file_id}")
        ],
        [
            InlineKeyboardButton("📺 360p", callback_data=f"comp_360p_{file.file_id}"),
            InlineKeyboardButton("🎬 All Qualities", callback_data=f"comp_all_{file.file_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        "**🎞️ Compression Mode**\n\n"
        "**Select quality to compress:**\n"
        f"**Original:** {filename}\n"
        f"**Size:** {humanbytes(file_size)}\n\n"
        "💡 Select 'All Qualities' for multiple outputs",
        reply_markup=keyboard
    )


async def handle_autotrim_mode(client, message, file, filename, file_size):
    """Handle auto trim with detection"""
    user_id = message.from_user.id
    
    await message.reply_text(
        "**🤖 Auto Trim Mode**\n\n"
        "This will automatically detect intro/outro and trim the video.\n\n"
        "⏳ Processing will take some time...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Start Auto Trim", callback_data=f"autotrim_start_{file.file_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
    )


# Callback handlers for extract mode
@Client.on_callback_query(filters.regex("^extract_audio_"))
async def extract_audio_callback(client, query):
    """Extract audio from video"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**🎵 Extracting audio...**")
    
    try:
        # Get file
        file = await client.get_messages(query.message.chat.id, query.message.reply_to_message.id)
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Download
        if file.video:
            filename = file.video.file_name or "video.mp4"
        elif file.document:
            filename = file.document.file_name
        
        video_path = os.path.join(downloads_dir, filename)
        audio_path = os.path.join(downloads_dir, f"{os.path.splitext(filename)[0]}.mp3")
        
        await query.message.edit_text("📥 Downloading video...")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        await upload_client.download_media(file, file_name=video_path)
        
        # Extract audio using ffmpeg
        await query.message.edit_text("🎵 Extracting audio...")
        
        cmd = f'ffmpeg -i "{video_path}" -vn -acodec libmp3lame -q:a 2 "{audio_path}"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(audio_path):
            await query.message.edit_text("📤 Uploading audio...")
            
            await client.send_audio(
                query.message.chat.id,
                audio=audio_path,
                caption=f"**🎵 Extracted Audio**\n\nFrom: {filename}"
            )
            
            await query.message.edit_text("**✅ Audio extracted successfully!**")
        else:
            await query.message.edit_text("**❌ Audio extraction failed!**")
        
        # Cleanup
        clean_file(video_path)
        clean_file(audio_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")


@Client.on_callback_query(filters.regex("^extract_subs_"))
async def extract_subs_callback(client, query):
    """Extract subtitles from video"""
    file_id = query.data.split("_")[-1]
    
    await query.message.edit_text("**📝 Extracting subtitles...**")
    
    try:
        # Get file
        file = await client.get_messages(query.message.chat.id, query.message.reply_to_message.id)
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        if file.video:
            filename = file.video.file_name or "video.mp4"
        elif file.document:
            filename = file.document.file_name
        
        video_path = os.path.join(downloads_dir, filename)
        subs_path = os.path.join(downloads_dir, f"{os.path.splitext(filename)[0]}.srt")
        
        await query.message.edit_text("📥 Downloading video...")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        await upload_client.download_media(file, file_name=video_path)
        
        # Extract subtitles using ffmpeg
        await query.message.edit_text("📝 Extracting subtitles...")
        
        cmd = f'ffmpeg -i "{video_path}" -map 0:s:0 "{subs_path}"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(subs_path):
            await query.message.edit_text("📤 Uploading subtitles...")
            
            await client.send_document(
                query.message.chat.id,
                document=subs_path,
                caption=f"**📝 Extracted Subtitles**\n\nFrom: {filename}"
            )
            
            await query.message.edit_text("**✅ Subtitles extracted successfully!**")
        else:
            await query.message.edit_text("**❌ No subtitles found in video!**")
        
        # Cleanup
        clean_file(video_path)
        clean_file(subs_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")


# Callback handler for merge
@Client.on_callback_query(filters.regex("merge_now"))
async def merge_now_callback(client, query):
    """Merge files in queue"""
    user_id = query.from_user.id
    
    queue = await pp_bots.get_merge_queue(user_id)
    
    if len(queue) < 2:
        return await query.answer("❌ Need at least 2 files to merge!", show_alert=True)
    
    await query.message.edit_text("**🔗 Merging files...**\n\nThis may take a while...")
    
    try:
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Download all files
        file_paths = []
        for idx, file_info in enumerate(queue):
            await query.message.edit_text(f"**📥 Downloading file {idx+1}/{len(queue)}...**")
            
            file_msg = await client.get_messages(query.message.chat.id, file_info['message_id'])
            file_path = os.path.join(downloads_dir, f"merge_{idx}_{file_info['filename']}")
            
            upload_client = app if (app and Config.STRING_SESSION) else client
            await upload_client.download_media(file_msg, file_name=file_path)
            file_paths.append(file_path)
        
        # Create concat file
        concat_file = os.path.join(downloads_dir, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for path in file_paths:
                f.write(f"file '{path}'\n")
        
        # Merge using ffmpeg
        await query.message.edit_text("**🔗 Merging videos...**")
        
        output_path = os.path.join(downloads_dir, "merged_output.mp4")
        cmd = f'ffmpeg -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            await query.message.edit_text("**📤 Uploading merged file...**")
            
            await client.send_video(
                query.message.chat.id,
                video=output_path,
                caption=f"**🔗 Merged Video**\n\n{len(queue)} files merged successfully!"
            )
            
            await query.message.edit_text("**✅ Files merged successfully!**")
            
            # Clear queue
            await pp_bots.clear_merge_queue(user_id)
        else:
            await query.message.edit_text("**❌ Merge failed!**")
        
        # Cleanup
        for path in file_paths:
            clean_file(path)
        clean_file(concat_file)
        clean_file(output_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")


@Client.on_callback_query(filters.regex("clear_merge_queue"))
async def clear_merge_callback(client, query):
    """Clear merge queue"""
    user_id = query.from_user.id
    await pp_bots.clear_merge_queue(user_id)
    await query.answer("✅ Queue cleared!", show_alert=True)
    await query.message.edit_text("**✅ Merge queue cleared!**")


# Compression callback handlers
@Client.on_callback_query(filters.regex("^comp_"))
async def compress_callback(client, query):
    """Handle compression"""
    parts = query.data.split("_")
    quality = parts[1]
    file_id = parts[2]
    
    await query.message.edit_text(f"**🎞️ Compressing to {quality}...**")
    
    try:
        # Get file
        file = await client.get_messages(query.message.chat.id, query.message.reply_to_message.id)
        
        if quality == "all":
            qualities = ['1080p', '720p', '576p', '480p', '360p']
        else:
            qualities = [quality]
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        if file.video:
            filename = file.video.file_name or "video.mp4"
        elif file.document:
            filename = file.document.file_name
        
        video_path = os.path.join(downloads_dir, filename)
        
        await query.message.edit_text("📥 Downloading video...")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        await upload_client.download_media(file, file_name=video_path)
        
        for qual in qualities:
            await query.message.edit_text(f"**🎞️ Compressing to {qual}...**")
            
            resolution = Config.COMPRESSION_QUALITIES[qual]['resolution']
            bitrate = Config.COMPRESSION_QUALITIES[qual]['bitrate']
            
            output_name = f"{os.path.splitext(filename)[0]}_{qual}.mp4"
            output_path = os.path.join(downloads_dir, output_name)
            
            cmd = f'ffmpeg -i "{video_path}" -vf scale={resolution} -b:v {bitrate} -c:a copy "{output_path}"'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                await query.message.edit_text(f"**📤 Uploading {qual}...**")
                
                await client.send_video(
                    query.message.chat.id,
                    video=output_path,
                    caption=f"**🎞️ Compressed Video**\n\nQuality: {qual}\nOriginal: {filename}"
                )
                
                clean_file(output_path)
        
        await query.message.edit_text("**✅ Compression complete!**")
        clean_file(video_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        elif final_media_type == "video":
            sent = await upload_client.send_video(
                upload_to,
                video=path,
                caption=caption,
                thumb=ph_
