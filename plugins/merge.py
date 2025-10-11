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
    
    # Count different types
    videos = sum(1 for f in queue if f['type'] == 'video' or f['type'] == 'document')
    audios = sum(1 for f in queue if f['type'] == 'audio')
    
    # Show queue status with type indicators
    files_list = []
    for idx, f in enumerate(queue):
        type_icon = "🎬" if f['type'] in ['video', 'document'] else "🎵" if f['type'] == 'audio' else "📝"
        files_list.append(f"{idx+1}. {type_icon} `{f['filename']}`")
    
    files_display = "\n".join(files_list)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done - Merge Now", callback_data="merge_now")],
        [InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_merge_queue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    await message.reply_text(
        f"**🔗 MERGE QUEUE**\n\n"
        f"**Files in queue:** {len(queue)}\n"
        f"**Videos:** {videos} | **Audio:** {audios}\n"
        f"**Latest added:** {filename}\n\n"
        f"**Queue:**\n{files_display}\n\n"
        f"💡 **Supported merges:**\n"
        f"• Multiple videos → One video\n"
        f"• Video + Audio → Video with audio\n"
        f"• Video + Subtitle → Video with subs\n"
        f"• Video + Audio + Subtitle → All combined\n\n"
        f"Send more files or click 'Done'",
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
        "**🔗 Analyzing files...**\n\n"
        "Determining merge type..."
    )
    
    try:
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Separate files by type
        video_files = []
        audio_files = []
        subtitle_files = []
        
        # Download all files
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
                
                # Categorize by type
                if file_info['type'] in ['video', 'document']:
                    # Check if it's actually a subtitle file
                    if file_info['filename'].lower().endswith(('.srt', '.ass', '.vtt', '.sub')):
                        subtitle_files.append(file_path)
                    else:
                        video_files.append(file_path)
                elif file_info['type'] == 'audio':
                    audio_files.append(file_path)
                
            except Exception as e:
                logging.error(f"Download error for file {idx}: {e}")
                continue
        
        if not video_files and not audio_files:
            await query.message.edit_text("**❌ No valid video or audio files found!**")
            return
        
        # Determine merge type and execute
        if len(video_files) > 1 and not audio_files and not subtitle_files:
            # Multiple videos - Concatenate
            result_path = await merge_multiple_videos(query, video_files, downloads_dir)
        elif len(video_files) == 1 and audio_files and not subtitle_files:
            # Video + Audio(s)
            result_path = await merge_video_with_audio(query, video_files[0], audio_files, downloads_dir)
        elif len(video_files) == 1 and subtitle_files and not audio_files:
            # Video + Subtitle(s)
            result_path = await merge_video_with_subtitles(query, video_files[0], subtitle_files, downloads_dir)
        elif len(video_files) == 1 and audio_files and subtitle_files:
            # Video + Audio + Subtitles (All in one)
            result_path = await merge_video_audio_subtitles(query, video_files[0], audio_files, subtitle_files, downloads_dir)
        else:
            # Complex merge with multiple videos and other files
            await query.message.edit_text(
                "**❌ Unsupported merge combination!**\n\n"
                "**Supported:**\n"
                "• Multiple videos only\n"
                "• 1 Video + Audio(s)\n"
                "• 1 Video + Subtitle(s)\n"
                "• 1 Video + Audio(s) + Subtitle(s)"
            )
            return
        
        if result_path and os.path.exists(result_path):
            await upload_merged_file(client, query, result_path, user_id, len(queue))
            clean_file(result_path)
        
        # Cleanup all downloaded files
        for path in video_files + audio_files + subtitle_files:
            clean_file(path)
        
    except Exception as e:
        await query.message.edit_text(f"**❌ Error:** `{e}`")
        logging.error(f"Merge error: {e}")


async def merge_multiple_videos(query, video_files, downloads_dir):
    """Merge multiple video files into one"""
    await query.message.edit_text(
        f"**🔗 Merging {len(video_files)} videos...**\n\n"
        "Please wait..."
    )
    
    output_path = os.path.join(downloads_dir, "merged_videos.mp4")
    
    # Create concat file
    concat_file = os.path.join(downloads_dir, "concat_list.txt")
    with open(concat_file, 'w') as f:
        for path in video_files:
            f.write(f"file '{path}'\n")
    
    # Try concat demuxer first
    cmd = f'ffmpeg -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"'
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    # If fails, try filter_complex
    if process.returncode != 0 or not os.path.exists(output_path):
        await query.message.edit_text("**🔗 Re-encoding and merging...**")
        
        inputs = " ".join([f'-i "{path}"' for path in video_files])
        filters = "".join([f"[{i}:v][{i}:a]" for i in range(len(video_files))])
        filter_complex = f'{filters}concat=n={len(video_files)}:v=1:a=1[outv][outa]'
        
        cmd = f'ffmpeg {inputs} -filter_complex "{filter_complex}" -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -c:a aac "{output_path}"'
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
    
    clean_file(concat_file)
    
    if process.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        error_msg = stderr.decode()[:200] if stderr else "Unknown error"
        await query.message.edit_text(f"**❌ Merge failed!**\n\n`{error_msg}`")
        return None


async def merge_video_with_audio(query, video_path, audio_files, downloads_dir):
    """Merge video with audio tracks"""
    await query.message.edit_text(
        "**🎵 Adding audio to video...**\n\n"
        "Please wait..."
    )
    
    output_path = os.path.join(downloads_dir, "video_with_audio.mp4")
    
    # Build ffmpeg command
    inputs = f'-i "{video_path}"'
    for audio in audio_files:
        inputs += f' -i "{audio}"'
    
    # Map video and all audio tracks
    maps = "-map 0:v"
    for i in range(len(audio_files)):
        maps += f" -map {i+1}:a"
    
    cmd = f'ffmpeg {inputs} {maps} -c:v copy -c:a aac -shortest "{output_path}"'
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        error_msg = stderr.decode()[:200] if stderr else "Unknown error"
        await query.message.edit_text(f"**❌ Audio merge failed!**\n\n`{error_msg}`")
        return None


async def merge_video_with_subtitles(query, video_path, subtitle_files, downloads_dir):
    """Merge video with subtitle tracks"""
    await query.message.edit_text(
        "**📝 Adding subtitles to video...**\n\n"
        "Please wait..."
    )
    
    output_path = os.path.join(downloads_dir, "video_with_subs.mkv")  # MKV for subtitle support
    
    # Build ffmpeg command
    inputs = f'-i "{video_path}"'
    for sub in subtitle_files:
        inputs += f' -i "{sub}"'
    
    # Map video, audio and all subtitle tracks
    maps = "-map 0:v -map 0:a"
    for i in range(len(subtitle_files)):
        maps += f" -map {i+1}"
    
    cmd = f'ffmpeg {inputs} {maps} -c:v copy -c:a copy -c:s srt "{output_path}"'
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        error_msg = stderr.decode()[:200] if stderr else "Unknown error"
        await query.message.edit_text(f"**❌ Subtitle merge failed!**\n\n`{error_msg}`")
        return None


async def merge_video_audio_subtitles(query, video_path, audio_files, subtitle_files, downloads_dir):
    """Merge video with audio and subtitle tracks"""
    await query.message.edit_text(
        "**🎬 Combining video, audio & subtitles...**\n\n"
        "Please wait..."
    )
    
    output_path = os.path.join(downloads_dir, "complete_merge.mkv")  # MKV for full support
    
    # Build ffmpeg command
    inputs = f'-i "{video_path}"'
    for audio in audio_files:
        inputs += f' -i "{audio}"'
    for sub in subtitle_files:
        inputs += f' -i "{sub}"'
    
    # Map everything
    maps = "-map 0:v"
    
    # Map audio tracks
    for i in range(len(audio_files)):
        maps += f" -map {i+1}:a"
    
    # Map subtitle tracks
    for i in range(len(subtitle_files)):
        maps += f" -map {i+1+len(audio_files)}"
    
    cmd = f'ffmpeg {inputs} {maps} -c:v copy -c:a aac -c:s srt "{output_path}"'
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        error_msg = stderr.decode()[:200] if stderr else "Unknown error"
        await query.message.edit_text(f"**❌ Complete merge failed!**\n\n`{error_msg}`")
        return None


async def upload_merged_file(client, query, file_path, user_id, total_files):
    """Upload the merged file"""
    await query.message.edit_text("**📤 Uploading merged file...**")
    
    # Get caption
    c_caption = await pp_bots.get_caption(user_id)
    caption = c_caption.format(
        filename=os.path.basename(file_path),
        filesize=humanbytes(os.path.getsize(file_path)),
        duration="--"
    ) if c_caption else (
        f"**🔗 Merged File**\n\n"
        f"**Files merged:** {total_files}\n"
        f"**Size:** {humanbytes(os.path.getsize(file_path))}\n\n"
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
        video=file_path,
        caption=caption,
        thumb=ph_path,
        progress=progress_for_pyrogram,
        progress_args=("📤 Uploading...", query.message, time.time())
    )
    
    await query.message.edit_text(
        f"**✅ Merge complete!**\n\n"
        f"**Merged {total_files} files successfully!**"
    )
    
    # Clear queue
    await pp_bots.clear_merge_queue(user_id)
    
    clean_file(ph_path)


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


# ==================== COMMAND HANDLER ====================

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
            "2. Send files to merge\n"
            "3. Click 'Done - Merge Now'\n\n"
            "**Supported merges:**\n"
            "• Multiple videos → One video\n"
            "• Video + Audio → Video with audio track\n"
            "• Video + Subtitle → Video with subtitles\n"
            "• Video + Audio + Subtitle → All combined\n\n"
            "**Examples:**\n"
            "• Send video.mp4 + audio.mp3 → Video with new audio\n"
            "• Send video.mkv + eng.srt + hin.srt → Video with 2 subs\n"
            "• Send video + audio1.mp3 + audio2.mp3 + sub.srt → All in one\n\n"
            "Set mode now:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Enable Merge Mode", callback_data="mode_merge")]
            ])
        )
