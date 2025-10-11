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


# ==================== REMOVE STREAMS HANDLERS ====================

async def handle_remove_streams_mode(client, message, file, filename, file_size):
    """Show remove streams options"""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 Remove All Audio", callback_data=f"remove_all_audio_{file.file_id}"),
            InlineKeyboardButton("📝 Remove All Subs", callback_data=f"remove_all_subs_{file.file_id}")
        ],
        [
            InlineKeyboardButton("🔇📝 Remove Both", callback_data=f"remove_both_{file.file_id}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        f"**🗑️ REMOVE STREAMS**\n\n"
        f"**File:** {filename}\n"
        f"**Size:** {humanbytes(file_size)}\n\n"
        f"**What do you want to remove?**\n\n"
        f"• Remove All Audio - Keep only video\n"
        f"• Remove All Subs - Keep video + audio\n"
        f"• Remove Both - Video only",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex("^remove_all_audio_"))
async def remove_all_audio_callback(client, query: CallbackQuery):
    """Remove all audio streams from video"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**🔇 Removing audio streams...**")
    
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
        output_name = f"{os.path.splitext(filename)[0]}_no_audio.mp4"
        output_path = os.path.join(downloads_dir, output_name)
        
        await query.message.edit_text("**📥 Downloading video...**")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        await upload_client.download_media(
            file_msg,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", query.message, time.time())
        )
        
        # Remove audio using FFmpeg (-an = no audio)
        await query.message.edit_text("**🔇 Removing audio...**")
        
        cmd = f'ffmpeg -i "{video_path}" -c:v copy -an "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            await query.message.edit_text("**📤 Uploading video...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename=output_name,
                filesize=humanbytes(os.path.getsize(output_path)),
                duration="--"
            ) if c_caption else (
                f"**🔇 Audio Removed**\n\n"
                f"**Original:** {filename}\n"
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
            
            await upload_client.send_video(
                upload_to,
                video=output_path,
                caption=caption,
                thumb=ph_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", query.message, time.time())
            )
            
            await query.message.edit_text("**✅ Audio removed successfully!**")
            
            clean_file(ph_path)
        else:
            error_msg = stderr.decode()[:200] if stderr else "Unknown error"
            await query.message.edit_text(f"**❌ Failed to remove audio!**\n\n`{error_msg}`")
        
        # Cleanup
        clean_file(video_path)
        clean_file(output_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Remove audio error: {e}")


@Client.on_callback_query(filters.regex("^remove_all_subs_"))
async def remove_all_subs_callback(client, query: CallbackQuery):
    """Remove all subtitle streams from video"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**📝 Removing subtitle streams...**")
    
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
        output_name = f"{os.path.splitext(filename)[0]}_no_subs.mp4"
        output_path = os.path.join(downloads_dir, output_name)
        
        await query.message.edit_text("**📥 Downloading video...**")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        await upload_client.download_media(
            file_msg,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", query.message, time.time())
        )
        
        # Remove subtitles using FFmpeg (-sn = no subtitles)
        await query.message.edit_text("**📝 Removing subtitles...**")
        
        cmd = f'ffmpeg -i "{video_path}" -c:v copy -c:a copy -sn "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            await query.message.edit_text("**📤 Uploading video...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename=output_name,
                filesize=humanbytes(os.path.getsize(output_path)),
                duration="--"
            ) if c_caption else (
                f"**📝 Subtitles Removed**\n\n"
                f"**Original:** {filename}\n"
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
            
            await upload_client.send_video(
                upload_to,
                video=output_path,
                caption=caption,
                thumb=ph_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", query.message, time.time())
            )
            
            await query.message.edit_text("**✅ Subtitles removed successfully!**")
            
            clean_file(ph_path)
        else:
            error_msg = stderr.decode()[:200] if stderr else "Unknown error"
            await query.message.edit_text(f"**❌ Failed to remove subtitles!**\n\n`{error_msg}`")
        
        # Cleanup
        clean_file(video_path)
        clean_file(output_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Remove subtitles error: {e}")


@Client.on_callback_query(filters.regex("^remove_both_"))
async def remove_both_callback(client, query: CallbackQuery):
    """Remove both audio and subtitle streams (video only)"""
    file_id = query.data.split("_")[-1]
    user_id = query.from_user.id
    
    await query.message.edit_text("**🔇📝 Removing audio and subtitles...**")
    
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
        output_name = f"{os.path.splitext(filename)[0]}_video_only.mp4"
        output_path = os.path.join(downloads_dir, output_name)
        
        await query.message.edit_text("**📥 Downloading video...**")
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        await upload_client.download_media(
            file_msg,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", query.message, time.time())
        )
        
        # Remove both audio and subtitles using FFmpeg
        await query.message.edit_text("**🔇📝 Removing audio and subtitles...**")
        
        cmd = f'ffmpeg -i "{video_path}" -c:v copy -an -sn "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            await query.message.edit_text("**📤 Uploading video...**")
            
            # Get caption
            c_caption = await pp_bots.get_caption(user_id)
            caption = c_caption.format(
                filename=output_name,
                filesize=humanbytes(os.path.getsize(output_path)),
                duration="--"
            ) if c_caption else (
                f"**🎬 Video Only**\n\n"
                f"**Original:** {filename}\n"
                f"**Size:** {humanbytes(os.path.getsize(output_path))}\n"
                f"**Note:** Audio and subtitles removed\n\n"
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
            
            await upload_client.send_video(
                upload_to,
                video=output_path,
                caption=caption,
                thumb=ph_path,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", query.message, time.time())
            )
            
            await query.message.edit_text("**✅ Audio and subtitles removed successfully!**")
            
            clean_file(ph_path)
        else:
            error_msg = stderr.decode()[:200] if stderr else "Unknown error"
            await query.message.edit_text(f"**❌ Failed to remove streams!**\n\n`{error_msg}`")
        
        # Cleanup
        clean_file(video_path)
        clean_file(output_path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Remove both streams error: {e}")


# ==================== COMMAND HANDLER ====================

@Client.on_message(filters.private & filters.command("removestreams"))
async def remove_streams_command(client, message):
    """Remove streams command"""
    await message.reply_text(
        "**🗑️ REMOVE STREAMS**\n\n"
        "**How to use:**\n"
        "1. Set mode: `/media extract`\n"
        "2. Send video file\n"
        "3. Choose what to remove\n\n"
        "**Options:**\n"
        "• Remove All Audio - Keep only video\n"
        "• Remove All Subs - Keep video + audio\n"
        "• Remove Both - Video only\n\n"
        "**Use cases:**\n"
        "• Reduce file size\n"
        "• Remove unwanted audio tracks\n"
        "• Clean up subtitle tracks\n"
        "• Create video-only files\n\n"
        "Set mode now:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Enable Remove Mode", callback_data="mode_extract")]
        ])
    )
