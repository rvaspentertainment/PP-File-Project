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
from plugins.trim import handle_trim_mode_media
from plugins.compress import handle_compress_mode_media
from plugins.extract_merge import handle_extract_mode_media, handle_merge_mode_media
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
    """Main handler for all media files - Routes to appropriate processor"""
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
    
    # Check for Jai Bajarangabali special handling (Priority)
    if is_jai_bajarangabali_file(filename):
        return await handle_jai_bajarangabali(client, message)
    
    # Route to appropriate handler based on mode
    try:
        if media_mode == "rename":
            await handle_rename_mode(client, message, file, filename, file_size, media_type)
        elif media_mode == "trim":
            await handle_trim_mode_media(client, message, file, filename, file_size)
        elif media_mode == "extract":
            await handle_extract_mode_media(client, message, file, filename, file_size)
        elif media_mode == "merge":
            await handle_merge_mode_media(client, message, file, filename, file_size, media_type)
        elif media_mode == "compress":
            await handle_compress_mode_media(client, message, file, filename, file_size)
        elif media_mode == "autotrim":
            # Future implementation
            await message.reply_text(
                "**🤖 Auto Trim Mode**\n\n"
                "This feature is coming soon!\n\n"
                "Use `/media trim` for manual trimming."
            )
        else:
            # Default to rename if unknown mode
            await handle_rename_mode(client, message, file, filename, file_size, media_type)
    except Exception as e:
        logging.error(f"Error in media handler: {e}")
        await message.reply_text(f"**❌ Error processing file:** `{e}`")


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
            f"{'💡 Add premium session for 4GB support' if not Config.STRING_SESSION else 'Premium session active but file exceeds 4GB limit'}"
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
        
        # Check caption first, then filename
        if message.caption:
            # Check if caption has extension
            if any(message.caption.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm']):
                new_filename = message.caption
            else:
                new_filename = filename
        else:
            new_filename = filename
        
        # Apply removals and replacements
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
        if file_id in renaming_operations:
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
            except asyncio.TimeoutError:
                logging.warning("Metadata addition timed out")
            except Exception as e:
                logging.error(f"Metadata error: {e}")
    
    if not metadata_added:
        path = renamed_file_path
    
    # Upload
    upload_msg = await download_msg.edit("📤 Uploading...")
    
    try:
        # Get caption
        c_caption = await pp_bots.get_caption(user_id)
        
        # Get duration if video
        duration = 0
        if media_type == "video":
            try:
                metadata = extractMetadata(createParser(path))
                if metadata and metadata.has("duration"):
                    duration = metadata.get('duration').seconds
            except:
                pass
        
        caption = c_caption.format(
            filename=new_filename,
            filesize=humanbytes(file_size),
            duration=convert(duration)
        ) if c_caption else f"**{new_filename}**"
        
        # Get thumbnail
        ph_path = None
        c_thumb = await pp_bots.get_thumbnail(user_id)
        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and message.video and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)
        
        if ph_path:
            try:
                img = Image.open(ph_path).convert("RGB")
                img = img.resize((320, 320))
                img.save(ph_path, "JPEG")
            except Exception as e:
                logging.error(f"Thumbnail processing error: {e}")
                clean_file(ph_path)
                ph_path = None
        
        # Upload destination
        upload_to = upload_channel if upload_channel else message.chat.id
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        # Get media preference
        final_media_type = media_preference or media_type
        
        # Upload based on type
        if final_media_type == "document":
            sent = await upload_client.send_document(
                upload_to,
                document=path,
                thumb=ph_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        elif final_media_type == "video":
            sent = await upload_client.send_video(
                upload_to,
                video=path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        elif final_media_type == "audio":
            sent = await upload_client.send_audio(
                upload_to,
                audio=path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
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
        
        # Cleanup thumbnail
        clean_file(ph_path)
        
    except Exception as e:
        await upload_msg.edit(f"**❌ Upload Error:** `{e}`")
        logging.error(f"Upload error: {e}")
    
    finally:
        # Cleanup files only after successful operations
        clean_file(renamed_file_path)
        clean_file(metadata_file_path)
        if file_id in renaming_operations:
            del renaming_operations[file_id]
