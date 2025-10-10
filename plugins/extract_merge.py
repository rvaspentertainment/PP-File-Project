from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.database import pp_bots
from helper.utils import progress_for_pyrogram, humanbytes, clean_file
from config import Config
from bot import app
import os
import time
import asyncio
import logging


# ==================== EXTRACT HANDLERS ====================

async def handle_extract_mode_media(client, message, file, filename, file_size):
    """Handle extract mode when user sends video"""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_audio_{file.file_id}"),
            InlineKeyboardButton("📝 Extract Subtitles", callback_data=f"extract_subs_{file.file_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        f"**🎵 EXTRACT MODE**\n\n"
        f"**File:** {filename}\n"
        f"**Size:** {humanbytes(file_size)}\n\n"
        f"**What do you want to extract?**",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex("^extract_audio_"))
async def extract_audio_callback(client, query: CallbackQuery):
    """Extract audio from video"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**🎵 Extracting audio...**")
    
    try:
        file_msg = query.message.reply_to_message
        
        if file_msg.video:
            file = file_msg.video
            filename = file.file_name or "video.mp4"
        elif file_msg.document:
            file = file_msg.document
            filename = file.file_name
        else:
            return await query.message.edit_text("**❌ Invalid file type!**")
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        video_path = os.path.join(downloads_dir, filename)
        audio_path = os.path.join(downloads_dir, f"{os.path.splitext(filename)[0]}.mp3")
        
        await query.message.edit_text("**📥 Downloading video...**")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        await upload_client.download_media(
            file_msg,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", query.message, time.time())
        )
        
        # Extract subtitles using FFmpeg
        await query.message.edit_text("**📝 Extracting subtitles...**")
        
        cmd = f'ffmpeg -i "{video_path}" -map 0:s:0 "{subs_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(subs_path):
            await query.message.edit_text("**📤 Uploading subtitles...**")
            
            caption = f"**📝 Extracted Subtitles**\n\nFrom: {filename}\n\n@pp_bots"
            
            # Check channel
            upload_channel = await pp_bots.get_upload_channel(user_id)
            upload_to = upload_channel if upload_channel else query.message.chat.id
            
            await client.send_document(
                upload_to,
                document=subs_path,
                caption=caption
            )
            
            await query.message.edit_text("**✅ Subtitles extracted successfully!**")
        else:
            await query.message.edit_text(
                "**❌ No subtitles found in video!**\n\n"
                "This video doesn't contain embedded subtitles."
            )
        
        # Cleanup
        clean_file(video_path)
        clean_file(subs_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Extract subtitles error: {e}")


# ==================== MERGE HANDLERS ====================

async def handle_merge_mode_media(client, message, file, filename, file_size, media_type):
    """Handle merge mode when user sends file"""
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
    
    # Show queue status
    files_list = "\n".join([f"{idx+1}. `{f['filename']}`" for idx, f in enumerate(queue)])
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done - Merge Now", callback_data="merge_now")],
        [InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_merge_queue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        f"**🔗 MERGE QUEUE**\n\n"
        f"**Files in queue:** {len(queue)}\n"
        f"**Latest added:** {filename}\n\n"
        f"**Queue:**\n{files_list}\n\n"
        f"💡 Send more files or click 'Done' to merge.",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex("merge_now"))
async def merge_now_callback(client, query: CallbackQuery):
    """Merge files in queue"""
    user_id = query.from_user.id
    
    queue = await pp_bots.get_merge_queue(user_id)
    
    if len(queue) < 2:
        return await query.answer("❌ Need at least 2 files to merge!", show_alert=True)
    
    await query.message.edit_text(
        "**🔗 Merging files...**\n\n"
        "This may take several minutes..."
    )
    
    try:
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Download all files
        file_paths = []
        for idx, file_info in enumerate(queue):
            await query.message.edit_text(
                f"**📥 Downloading file {idx+1}/{len(queue)}...**\n\n"
                f"`{file_info['filename']}`"
            )
            
            try:
                file_msg = await client.get_messages(query.message.chat.id, file_info['message_id'])
                file_path = os.path.join(downloads_dir, f"merge_{idx}_{file_info['filename']}")
                
                upload_client = app if (app and Config.STRING_SESSION) else client
                
                await upload_client.download_media(
                    file_msg,
                    file_name=file_path,
                    progress=progress_for_pyrogram,
                    progress_args=(f"📥 File {idx+1}/{len(queue)}", query.message, time.time())
                )
                
                file_paths.append(file_path)
            except Exception as e:
                logging.error(f"Download error for file {idx}: {e}")
                continue
        
        if len(file_paths) < 2:
            await query.message.edit_text("**❌ Failed to download enough files for merging!**")
            return
        
        # Create concat file for FFmpeg
        concat_file = os.path.join(downloads_dir, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for path in file_paths:
                f.write(f"file '{path}'\n")
        
        # Merge using FFmpeg
        await query.message.edit_text(
            f"**🔗 Merging {len(file_paths)} videos...**\n\n"
            "Please wait..."
        )
        
        output_path = os.path.join(downloads_dir, "merged_output.mp4")
        
        # Try concat demuxer first (fastest)
        cmd = f'ffmpeg -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # If concat fails, try filter_complex (slower but works with different codecs)
        if process.returncode != 0 or not os.path.exists(output_path):
            await query.message.edit_text(
                "**🔗 Re-encoding and merging...**\n\n"
                "This may take longer..."
            )
            
            # Build filter_complex command
            inputs = " ".join([f'-i "{path}"' for path in file_paths])
            filters = "".join([f"[{i}:v][{i}:a]" for i in range(len(file_paths))])
            filter_complex = f'{filters}concat=n={len(file_paths)}:v=1:a=1[outv][outa]'
            
            cmd = f'ffmpeg {inputs} -filter_complex "{filter_complex}" -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -c:a aac "{output_path}"'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            await query.message.edit_text("**📤 Uploading merged file...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename="merged_output.mp4",
                filesize=humanbytes(os.path.getsize(output_path)),
                duration="--"
            ) if c_caption else (
                f"**🔗 Merged Video**\n\n"
                f"**Files merged:** {len(file_paths)}\n"
                f"**Size:** {humanbytes(os.path.getsize(output_path))}\n\n"
                f"@pp_bots"
            )
            
            # Get thumbnail
            ph_path = None
            c_thumb = await pp_bots.get_thumbnail(user_id)
            if c_thumb:
                ph_path = await client.download_media(c_thumb)
            
            # Check channel
            upload_channel = await pp_bots.get_upload_channel(user_id)
            upload_to = upload_channel if upload_channel else query.message.chat.id
            
            upload_client = app if (app and Config.STRING_SESSION) else client
            
            await upload_client.send_video(
                upload_to,
                video=output_path,
                caption=caption,
                thumb=ph_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", query.message, time.time())
            )
            
            await query.message.edit_text(
                f"**✅ Merge complete!**\n\n"
                f"**Merged {len(file_paths)} files successfully!**"
            )
            
            # Clear queue
            await pp_bots.clear_merge_queue(user_id)
            
            clean_file(ph_path)
        else:
            error_msg = stderr.decode()[:300] if stderr else "Unknown error"
            await query.message.edit_text(
                f"**❌ Merge failed!**\n\n"
                f"```{error_msg}```"
            )
        
        # Cleanup
        for path in file_paths:
            clean_file(path)
        clean_file(concat_file)
        clean_file(output_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Merge error: {e}")


@Client.on_callback_query(filters.regex("clear_merge_queue"))
async def clear_merge_callback(client, query: CallbackQuery):
    """Clear merge queue"""
    user_id = query.from_user.id
    await pp_bots.clear_merge_queue(user_id)
    await query.answer("✅ Queue cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ Merge queue cleared!**\n\n"
        "Start adding files again to merge."
    )


# ==================== COMMAND HANDLERS ====================

@Client.on_message(filters.private & filters.command("extract"))
async def extract_command(client, message):
    """Extract audio/subtitles command"""
    await message.reply_text(
        "**🎵 EXTRACT MODE**\n\n"
        "**How to use:**\n"
        "1. Set mode: `/media extract`\n"
        "2. Send video file\n"
        "3. Choose what to extract\n\n"
        "**Features:**\n"
        "• Extract Audio (MP3)\n"
        "• Extract Subtitles (SRT)\n"
        "• High quality output\n\n"
        "Set mode now:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Enable Extract Mode", callback_data="mode_extract")]
        ])
    )


@Client.on_message(filters.private & filters.command("merge"))
async def merge_command(client, message):
    """Merge files command"""
    user_id = message.from_user.id
    queue = await pp_bots.get_merge_queue(user_id)
    
    if queue:
        files_list = "\n".join([f"{idx+1}. `{f['filename']}`" for idx, f in enumerate(queue)])
        
        await message.reply_text(
            f"**🔗 MERGE QUEUE**\n\n"
            f"**Files in queue:** {len(queue)}\n\n"
            f"**Queue:**\n{files_list}\n\n"
            f"Send more files or merge now:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Merge Now", callback_data="merge_now")],
                [InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_merge_queue")]
            ])
        )
    else:
        await message.reply_text(
            "**🔗 MERGE MODE**\n\n"
            "**How to use:**\n"
            "1. Set mode: `/media merge`\n"
            "2. Send first video file\n"
            "3. Send second video file\n"
            "4. Send more files (optional)\n"
            "5. Click 'Done - Merge Now'\n\n"
            "**Supported:**\n"
            "• Multiple videos\n"
            "• Video + Audio\n"
            "• Video + Subtitles\n\n"
            "Set mode now:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Enable Merge Mode", callback_data="mode_merge")]
            ])
        )

        
        await upload_client.download_media(
            file_msg,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", query.message, time.time())
        )
        
        # Extract audio using FFmpeg
        await query.message.edit_text("**🎵 Extracting audio...**")
        
        cmd = f'ffmpeg -i "{video_path}" -vn -acodec libmp3lame -q:a 2 "{audio_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(audio_path):
            await query.message.edit_text("**📤 Uploading audio...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename=os.path.basename(audio_path),
                filesize=humanbytes(os.path.getsize(audio_path)),
                duration="--"
            ) if c_caption else (
                f"**🎵 Extracted Audio**\n\n"
                f"**From:** {filename}\n"
                f"**Size:** {humanbytes(os.path.getsize(audio_path))}\n\n"
                f"@pp_bots"
            )
            
            # Check channel
            upload_channel = await pp_bots.get_upload_channel(user_id)
            upload_to = upload_channel if upload_channel else query.message.chat.id
            
            await upload_client.send_audio(
                upload_to,
                audio=audio_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", query.message, time.time())
            )
            
            await query.message.edit_text("**✅ Audio extracted successfully!**")
        else:
            error_msg = stderr.decode()[:200] if stderr else "Unknown error"
            await query.message.edit_text(f"**❌ Extraction failed!**\n\n`{error_msg}`")
        
        # Cleanup
        clean_file(video_path)
        clean_file(audio_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Extract audio error: {e}")


@Client.on_callback_query(filters.regex("^extract_subs_"))
async def extract_subs_callback(client, query: CallbackQuery):
    """Extract subtitles from video"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**📝 Extracting subtitles...**")
    
    try:
        file_msg = query.message.reply_to_message
        
        if file_msg.video:
            file = file_msg.video
            filename = file.file_name or "video.mp4"
        elif file_msg.document:
            file = file_msg.document
            filename = file.file_name
        else:
            return await query.message.edit_text("**❌ Invalid file type!**")
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        video_path = os.path.join(downloads_dir, filename)
        subs_path = os.path.join(downloads_dir, f"{os.path.splitext(filename)[0]}.srt")
        
        await query.message.edit_text("**📥 Downloading video...**")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
