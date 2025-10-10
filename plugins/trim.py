from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.database import pp_bots
from helper.utils import progress_for_pyrogram, humanbytes, parse_time, format_time, clean_file
from config import Config
from bot import app
import os
import time
import asyncio
import logging
from pyromod.exceptions import ListenerTimeout


# Store trim sessions
trim_sessions = {}


@Client.on_message(filters.private & filters.command("trim"))
async def trim_command(client, message):
    """Trim video command"""
    user_id = message.from_user.id
    
    try:
        # Check if link provided
        parts = message.text.split(maxsplit=2)
        
        if len(parts) >= 2:
            video_link = parts[1]
            intro_title = parts[2] if len(parts) == 3 else None
            
            # Handle link-based trimming
            await trim_from_link(client, message, video_link, intro_title)
        else:
            # Show manual trim instructions
            await message.reply_text(
                "**✂️ VIDEO TRIMMING**\n\n"
                "**Two ways to trim:**\n\n"
                "**1. From Link:**\n"
                "<code>/trim video_link</code>\n"
                "<code>/trim video_link intro_title</code>\n\n"
                "**2. Send Video File:**\n"
                "Set mode: /media trim\n"
                "Then send video file\n\n"
                "**Examples:**\n"
                "<code>/trim https://example.com/video.mp4</code>\n"
                "<code>/trim https://example.com/video.mp4 Custom_Intro</code>"
            )
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{e}`")


async def trim_from_link(client, message, video_link, intro_title=None):
    """Trim video from download link"""
    user_id = message.from_user.id
    
    ms = await message.reply_text("**📥 Downloading video from link...**")
    
    try:
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Download using requests
        import requests
        filename = f"video_{user_id}_{int(time.time())}.mp4"
        video_path = os.path.join(downloads_dir, filename)
        
        response = requests.get(video_link, stream=True, timeout=60)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(video_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if int(percent) % 10 == 0:
                            await ms.edit(f"**📥 Downloading: {percent:.1f}%**")
        
        await ms.edit("**✂️ Ready to trim! Send start time (HH:MM:SS or MM:SS):**")
        
        # Get start time
        try:
            start_msg = await client.listen(message.chat.id, filters=filters.text, timeout=60)
            start_time = parse_time(start_msg.text)
            
            if start_time is None:
                await ms.edit("**❌ Invalid start time format!**")
                clean_file(video_path)
                return
            
            await ms.edit("**✂️ Now send end time (HH:MM:SS or MM:SS):**")
            
            # Get end time
            end_msg = await client.listen(message.chat.id, filters=filters.text, timeout=60)
            end_time = parse_time(end_msg.text)
            
            if end_time is None:
                await ms.edit("**❌ Invalid end time format!**")
                clean_file(video_path)
                return
            
            # Trim video
            await ms.edit("**✂️ Trimming video...**")
            
            trimmed_path = os.path.join(downloads_dir, f"trimmed_{filename}")
            
            cmd = f'ffmpeg -i "{video_path}" -ss {start_time} -to {end_time} -c copy "{trimmed_path}"'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(trimmed_path):
                await ms.edit("**📤 Uploading trimmed video...**")
                
                upload_client = app if (app and Config.STRING_SESSION) else client
                
                caption = f"**✂️ Trimmed Video**\n\n"
                caption += f"**Start:** {format_time(start_time)}\n"
                caption += f"**End:** {format_time(end_time)}\n"
                caption += f"**Duration:** {format_time(end_time - start_time)}\n\n"
                if intro_title:
                    caption += f"**Intro:** {intro_title}\n\n"
                caption += "@pp_bots"
                
                await upload_client.send_video(
                    message.chat.id,
                    video=trimmed_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("📤 Uploading...", ms, time.time())
                )
                
                await ms.edit("**✅ Trimmed video uploaded!**")
            else:
                await ms.edit("**❌ Trimming failed!**")
            
            # Cleanup
            clean_file(video_path)
            clean_file(trimmed_path)
            
        except ListenerTimeout:
            await ms.edit("**⏰ Timeout! Please try again.**")
            clean_file(video_path)
            
    except Exception as e:
        await ms.edit(f"**❌ Error:** `{e}`")
        logging.error(f"Trim from link error: {e}")


async def handle_trim_mode_media(client, message, file, filename, file_size):
    """Handle trim mode when user sends video file"""
    user_id = message.from_user.id
    
    # Ask for start time
    ask_msg = await message.reply_text(
        "**✂️ TRIM VIDEO**\n\n"
        "Send start time in format:\n"
        "• HH:MM:SS (e.g., 00:05:30)\n"
        "• MM:SS (e.g., 05:30)\n"
        "• SS (e.g., 330)\n\n"
        "Or click cancel:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_trim")]
        ])
    )
    
    try:
        # Listen for start time
        start_msg = await client.listen(message.chat.id, filters=filters.text, timeout=120)
        start_time = parse_time(start_msg.text)
        
        if start_time is None:
            return await ask_msg.edit("**❌ Invalid start time! Please use /media trim and try again.**")
        
        # Ask for end time
        await ask_msg.edit(
            f"**✂️ TRIM VIDEO**\n\n"
            f"**Start time set:** {format_time(start_time)}\n\n"
            f"Now send end time:"
        )
        
        end_msg = await client.listen(message.chat.id, filters=filters.text, timeout=120)
        end_time = parse_time(end_msg.text)
        
        if end_time is None:
            return await ask_msg.edit("**❌ Invalid end time! Please try again.**")
        
        if end_time <= start_time:
            return await ask_msg.edit("**❌ End time must be greater than start time!**")
        
        # Download and trim
        await ask_msg.edit("**📥 Downloading video...**")
        
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        video_path = os.path.join(downloads_dir, filename)
        trimmed_path = os.path.join(downloads_dir, f"trimmed_{filename}")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        await upload_client.download_media(
            message,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", ask_msg, time.time())
        )
        
        # Trim video
        await ask_msg.edit("**✂️ Trimming video...**")
        
        cmd = f'ffmpeg -i "{video_path}" -ss {start_time} -to {end_time} -c copy "{trimmed_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(trimmed_path):
            await ask_msg.edit("**📤 Uploading trimmed video...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename=f"trimmed_{filename}",
                filesize=humanbytes(os.path.getsize(trimmed_path)),
                duration=format_time(end_time - start_time)
            ) if c_caption else (
                f"**✂️ Trimmed Video**\n\n"
                f"**Original:** {filename}\n"
                f"**Start:** {format_time(start_time)}\n"
                f"**End:** {format_time(end_time)}\n"
                f"**Duration:** {format_time(end_time - start_time)}\n\n"
                f"@pp_bots"
            )
            
            # Get thumbnail
            ph_path = None
            c_thumb = await pp_bots.get_thumbnail(user_id)
            if c_thumb:
                ph_path = await client.download_media(c_thumb)
            
            # Check channel upload
            upload_channel = await pp_bots.get_upload_channel(user_id)
            upload_to = upload_channel if upload_channel else message.chat.id
            
            await upload_client.send_video(
                upload_to,
                video=trimmed_path,
                caption=caption,
                thumb=ph_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", ask_msg, time.time())
            )
            
            if upload_channel:
                await ask_msg.edit("**✅ Trimmed video uploaded to channel!**")
            else:
                await ask_msg.delete()
            
            clean_file(ph_path)
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            await ask_msg.edit(f"**❌ Trimming failed!**\n\n`{error_msg[:200]}`")
        
        # Cleanup
        clean_file(video_path)
        clean_file(trimmed_path)
        
    except ListenerTimeout:
        await ask_msg.edit("**⏰ Timeout! Trim cancelled. Please try again.**")
    except Exception as e:
        await ask_msg.edit(f"**❌ Error:** `{e}`")
        logging.error(f"Trim error: {e}")


@Client.on_callback_query(filters.regex("cancel_trim"))
async def cancel_trim_callback(client, query):
    """Cancel trim operation"""
    await query.message.edit_text("**✅ Trim cancelled!**")
    await query.answer()
