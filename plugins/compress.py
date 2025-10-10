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


@Client.on_message(filters.private & filters.command("compress"))
async def compress_command(client, message):
    """Compress video command"""
    user_id = message.from_user.id
    
    try:
        # Check if qualities provided
        parts = message.text.split(maxsplit=1)
        
        if len(parts) == 2:
            qualities_str = parts[1]
            qualities = [q.strip() for q in qualities_str.split(',')]
            
            # Validate qualities
            valid_qualities = list(Config.COMPRESSION_QUALITIES.keys())
            invalid = [q for q in qualities if q not in valid_qualities]
            
            if invalid:
                return await message.reply_text(
                    f"**❌ Invalid qualities:** `{', '.join(invalid)}`\n\n"
                    f"**Available qualities:**\n" +
                    "\n".join([f"• `{q}`" for q in valid_qualities])
                )
            
            # Save qualities
            await pp_bots.set_compression_qualities(user_id, qualities)
            await message.reply_text(
                f"**✅ Compression qualities set!**\n\n"
                f"**Selected:** {', '.join(qualities)}\n\n"
                f"Now send a video file to compress."
            )
        else:
            # Show instructions
            await message.reply_text(
                "**🎞️ VIDEO COMPRESSION**\n\n"
                "**Usage:**\n"
                "<code>/compress 720p,480p,360p</code>\n\n"
                "**Available Qualities:**\n"
                "• `1080p` - Full HD (3000k)\n"
                "• `720p` - HD (2000k)\n"
                "• `576p` - SD (1500k)\n"
                "• `480p` - SD (1000k)\n"
                "• `360p` - Low (500k)\n\n"
                "**Examples:**\n"
                "<code>/compress 720p</code> - Single quality\n"
                "<code>/compress 720p,480p,360p</code> - Multiple\n"
                "<code>/compress all</code> - All qualities\n\n"
                "Or set mode and send video:\n"
                "<code>/media compress</code>"
            )
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{e}`")


async def handle_compress_mode_media(client, message, file, filename, file_size):
    """Handle compress mode when user sends video"""
    user_id = message.from_user.id
    
    # Check saved qualities
    saved_qualities = await pp_bots.get_compression_qualities(user_id)
    
    if saved_qualities:
        # Use saved qualities
        await compress_video(client, message, file, filename, file_size, saved_qualities)
    else:
        # Show quality selection
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📺 1080p", callback_data=f"comp_single_1080p_{file.file_id}"),
                InlineKeyboardButton("📺 720p", callback_data=f"comp_single_720p_{file.file_id}")
            ],
            [
                InlineKeyboardButton("📺 576p", callback_data=f"comp_single_576p_{file.file_id}"),
                InlineKeyboardButton("📺 480p", callback_data=f"comp_single_480p_{file.file_id}")
            ],
            [
                InlineKeyboardButton("📺 360p", callback_data=f"comp_single_360p_{file.file_id}"),
                InlineKeyboardButton("🎬 All Qualities", callback_data=f"comp_all_{file.file_id}")
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        await message.reply_text(
            f"**🎞️ COMPRESSION**\n\n"
            f"**Original:** {filename}\n"
            f"**Size:** {humanbytes(file_size)}\n\n"
            f"**Select quality to compress:**\n"
            f"💡 Click 'All Qualities' for multiple outputs",
            reply_markup=keyboard
        )


async def compress_video(client, message, file, filename, file_size, qualities):
    """Compress video to specified qualities"""
    user_id = message.from_user.id
    
    ms = await message.reply_text("**📥 Downloading video...**")
    
    try:
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        video_path = os.path.join(downloads_dir, filename)
        
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        # Download video
        await upload_client.download_media(
            message,
            file_name=video_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", ms, time.time())
        )
        
        # Compress each quality
        for idx, quality in enumerate(qualities, 1):
            await ms.edit(f"**🎞️ Compressing to {quality}... ({idx}/{len(qualities)})**")
            
            resolution = Config.COMPRESSION_QUALITIES[quality]['resolution']
            bitrate = Config.COMPRESSION_QUALITIES[quality]['bitrate']
            
            output_name = f"{os.path.splitext(filename)[0]}_{quality}.mp4"
            output_path = os.path.join(downloads_dir, output_name)
            
            # FFmpeg command for compression
            cmd = f'ffmpeg -i "{video_path}" -vf scale={resolution}:force_original_aspect_ratio=decrease -c:v libx264 -b:v {bitrate} -c:a aac -b:a 128k -preset fast "{output_path}"'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                await ms.edit(f"**📤 Uploading {quality}... ({idx}/{len(qualities)})**")
                
                # Get caption
                c_caption = await pp_bots.get_caption(user_id)
                caption = c_caption.format(
                    filename=output_name,
                    filesize=humanbytes(os.path.getsize(output_path)),
                    duration="--"
                ) if c_caption else (
                    f"**🎞️ Compressed Video**\n\n"
                    f"**Quality:** {quality}\n"
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
                upload_to = upload_channel if upload_channel else message.chat.id
                
                await upload_client.send_video(
                    upload_to,
                    video=output_path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=(f"📤 Uploading {quality}...", ms, time.time())
                )
                
                clean_file(ph_path)
                clean_file(output_path)
            else:
                error_msg = stderr.decode()[:200] if stderr else "Unknown error"
                logging.error(f"Compression failed for {quality}: {error_msg}")
                await ms.edit(f"**❌ Compression failed for {quality}!**\n\n`{error_msg}`")
                await asyncio.sleep(3)
        
        await ms.edit(f"**✅ Compression complete!**\n\n**Compressed {len(qualities)} quality versions**")
        clean_file(video_path)
        
    except Exception as e:
        await ms.edit(f"**❌ Error:** `{e}`")
        logging.error(f"Compression error: {e}")


@Client.on_callback_query(filters.regex("^comp_single_"))
async def compress_single_callback(client, query: CallbackQuery):
    """Handle single quality compression"""
    parts = query.data.split("_")
    quality = parts[2]
    file_id = parts[3]
    
    user_id = query.from_user.id
    
    # Get file from reply
    try:
        file_msg = query.message.reply_to_message
        if file_msg.video:
            file = file_msg.video
            filename = file.file_name or "video.mp4"
            file_size = file.file_size
        elif file_msg.document:
            file = file_msg.document
            filename = file.file_name
            file_size = file.file_size
        else:
            return await query.answer("❌ Invalid file!", show_alert=True)
        
        await query.message.delete()
        await compress_video(client, file_msg, file, filename, file_size, [quality])
        
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


@Client.on_callback_query(filters.regex("^comp_all_"))
async def compress_all_callback(client, query: CallbackQuery):
    """Handle all qualities compression"""
    file_id = query.data.split("_")[-1]
    
    # Get file from reply
    try:
        file_msg = query.message.reply_to_message
        if file_msg.video:
            file = file_msg.video
            filename = file.file_name or "video.mp4"
            file_size = file.file_size
        elif file_msg.document:
            file = file_msg.document
            filename = file.file_name
            file_size = file.file_size
        else:
            return await query.answer("❌ Invalid file!", show_alert=True)
        
        await query.message.delete()
        
        # Compress all qualities
        all_qualities = list(Config.COMPRESSION_QUALITIES.keys())
        await compress_video(client, file_msg, file, filename, file_size, all_qualities)
        
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)
