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


# ==================== COMMAND HANDLER ====================

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
