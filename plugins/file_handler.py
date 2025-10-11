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
from plugins.extract import handle_extract_mode_media
from plugins.merge import handle_merge_mode_media
from plugins.remove_streams import handle_remove_streams_mode
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
import uuid
import shutil


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
    
    print(f"\n{'='*60}")
    print(f"[MAIN HANDLER] New media file received from user {user_id}")
    
    # Get user settings
    media_mode = await pp_bots.get_media_mode(user_id)
    print(f"[MAIN HANDLER] Media mode: {media_mode}")
    
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
    
    print(f"[MAIN HANDLER] File: {filename}")
    print(f"[MAIN HANDLER] Size: {humanbytes(file_size)}")
    print(f"[MAIN HANDLER] Type: {media_type}")
    print(f"[MAIN HANDLER] File ID: {file.file_id}")
    
    # Check for Jai Bajarangabali special handling (Priority)
    if is_jai_bajarangabali_file(filename):
        print(f"[MAIN HANDLER] Routing to Jai Bajarangabali handler")
        return await handle_jai_bajarangabali(client, message)
    
    # Route to appropriate handler based on mode
    try:
        if media_mode == "rename":
            print(f"[MAIN HANDLER] Routing to RENAME mode")
            await handle_rename_mode(client, message, file, filename, file_size, media_type)
        
        elif media_mode == "trim":
            print(f"[MAIN HANDLER] Routing to TRIM mode")
            await handle_trim_mode_media(client, message, file, filename, file_size)
        
        elif media_mode == "extract":
            print(f"[MAIN HANDLER] Routing to EXTRACT mode")
            # Show extract/remove options
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_audio_{file.file_id}"),
                    InlineKeyboardButton("📝 Extract Subs", callback_data=f"extract_subs_{file.file_id}")
                ],
                [
                    InlineKeyboardButton("🗑️ Remove Streams", callback_data=f"show_remove_options_{file.file_id}")
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="close")]
            ])
            
            await message.reply_text(
                f"**🎵 EXTRACT/REMOVE MODE**\n\n"
                f"**File:** {filename}\n"
                f"**Size:** {humanbytes(file_size)}\n\n"
                f"**Choose action:**",
                reply_markup=keyboard
            )
        
        elif media_mode == "merge":
            print(f"[MAIN HANDLER] Routing to MERGE mode")
            await handle_merge_mode_media(client, message, file, filename, file_size, media_type)
        
        elif media_mode == "compress":
            print(f"[MAIN HANDLER] Routing to COMPRESS mode")
            await handle_compress_mode_media(client, message, file, filename, file_size)
        
        elif media_mode == "autotrim":
            print(f"[MAIN HANDLER] AUTOTRIM mode (not implemented)")
            # Future implementation
            await message.reply_text(
                "**🤖 Auto Trim Mode**\n\n"
                "This feature is coming soon!\n\n"
                "Use `/media trim` for manual trimming."
            )
        
        else:
            print(f"[MAIN HANDLER] Unknown mode, defaulting to RENAME")
            # Default to rename if unknown mode
            await handle_rename_mode(client, message, file, filename, file_size, media_type)
            
    except Exception as e:
        logging.error(f"Error in media handler: {e}")
        print(f"[MAIN HANDLER ERROR] {e}")
        await message.reply_text(f"**❌ Error processing file:** `{e}`")


# Callback to show remove streams options
@Client.on_callback_query(filters.regex("^show_remove_options_"))
async def show_remove_options_callback(client, query):
    """Show remove streams options"""
    file_id = query.data.split("_")[-1]
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 Remove Audio", callback_data=f"remove_all_audio_{file_id}"),
            InlineKeyboardButton("📝 Remove Subs", callback_data=f"remove_all_subs_{file_id}")
        ],
        [
            InlineKeyboardButton("🔇📝 Remove Both", callback_data=f"remove_both_{file_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=f"extract_audio_{file_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="close")
        ]
    ])
    
    await query.message.edit_text(
        "**🗑️ REMOVE STREAMS**\n\n"
        "**Choose what to remove:**\n\n"
        "• Remove Audio - Keep only video\n"
        "• Remove Subs - Keep video + audio\n"
        "• Remove Both - Video only",
        reply_markup=keyboard
    )


async def handle_rename_mode(client, message, file, filename, file_size, media_type):
    """Handle file renaming with templates or word replacement"""
    print(f"\n{'='*60}")
    print(f"[RENAME MODE] Started")
    
    user_id = message.from_user.id
    format_template = await pp_bots.get_format_template(user_id)
    media_preference = await pp_bots.get_media_preference(user_id)
    upload_channel = await pp_bots.get_upload_channel(user_id)
    
    print(f"[RENAME MODE] Format template: {format_template}")
    print(f"[RENAME MODE] Media preference: {media_preference}")
    print(f"[RENAME MODE] Upload channel: {upload_channel}")
    
    # Check file size
    max_size = Config.MAX_FILE_SIZE if (app and Config.STRING_SESSION) else Config.MAX_FILE_SIZE_NON_PREMIUM
    if file_size > max_size:
        size_gb = file_size / (1024 * 1024 * 1024)
        max_gb = max_size / (1024 * 1024 * 1024)
        print(f"[RENAME MODE] File too large: {size_gb:.2f} GB > {max_gb:.2f} GB")
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
            print(f"[RENAME MODE] Duplicate request detected (elapsed: {elapsed}s)")
            return
    renaming_operations[file_id] = datetime.now()
    
    print(f"[STEP 1] Original filename: {filename}")
    
    # Determine new filename
    _, file_extension = os.path.splitext(filename)
    print(f"[STEP 1] File extension: {file_extension}")
    
    if format_template:
        # Use template
        new_filename = format_template
        
        # Replace episode
        episode = extract_episode_number(filename)
        if episode:
            new_filename = new_filename.replace("[episode]", f"EP{episode}", 1)
            print(f"[STEP 2] Episode extracted: {episode}")
        
        # Replace quality
        quality = extract_quality(filename)
        new_filename = new_filename.replace("[quality]", quality)
        print(f"[STEP 2] Quality extracted: {quality}")
        
        new_filename = f"{new_filename}{file_extension}"
        print(f"[STEP 2] Template applied: {new_filename}")
    else:
        # Use word removal/replacement
        remove_words = await pp_bots.get_remove_words(user_id)
        replace_words = await pp_bots.get_replace_words(user_id)
        
        print(f"[STEP 2] Remove words: {remove_words}")
        print(f"[STEP 2] Replace words: {replace_words}")
        
        # Check caption first, then filename
        if message.caption:
            print(f"[STEP 2] Caption found: {message.caption}")
            # Check if caption has extension
            if any(message.caption.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm']):
                new_filename = message.caption
                print(f"[STEP 2] Using caption as filename")
            else:
                new_filename = filename
                print(f"[STEP 2] Caption has no extension, using original filename")
        else:
            new_filename = filename
            print(f"[STEP 2] No caption, using original filename")
        
        # Apply removals and replacements
        name_without_ext = os.path.splitext(new_filename)[0]
        name_without_ext = apply_word_removal(name_without_ext, remove_words)
        name_without_ext = apply_word_replacement(name_without_ext, replace_words)
        new_filename = f"{name_without_ext}{file_extension}"
        print(f"[STEP 2] After word removal/replacement: {new_filename}")
    
    # Sanitize filename
    new_filename = sanitize_filename(new_filename)
    print(f"[STEP 3] Sanitized filename: {new_filename}")
    
    # Setup paths
    downloads_dir = "downloads"
    metadata_dir = "Metadata"
    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    
    print(f"[STEP 4] Directories created/verified")
    
    # Create full paths
    renamed_file_path = os.path.join(downloads_dir, new_filename)
    metadata_file_path = os.path.join(metadata_dir, new_filename)
    
    print(f"[STEP 4] Download path: {renamed_file_path}")
    print(f"[STEP 4] Metadata path: {metadata_file_path}")
    
    # Download
    download_msg = await message.reply_text("📥 Downloading...")
    
    try:
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        print(f"[STEP 5] Starting download...")
        print(f"[STEP 5] Using client: {'Premium (app)' if upload_client == app else 'Normal (client)'}")
        print(f"[STEP 5] File ID: {file.file_id}")
        print(f"[STEP 5] Target path: {renamed_file_path}")
        print(f"[STEP 5] Directory exists: {os.path.exists(downloads_dir)}")
        
        # ✅ METHOD 1: Try downloading with simplified filename first
        # Create a safe temporary filename
        import uuid
        temp_filename = f"temp_{uuid.uuid4().hex[:8]}{file_extension}"
        temp_file_path = os.path.join(downloads_dir, temp_filename)
        
        print(f"[STEP 5] Trying download with temp filename: {temp_filename}")
        
        temp_path = await upload_client.download_media(
            message,
            file_name=temp_file_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", download_msg, time.time())
        )
        
        print(f"[STEP 6] Download complete!")
        print(f"[STEP 6] Returned path: {temp_path}")
        print(f"[STEP 6] Path type: {type(temp_path)}")
        
        # Check if download returned None
        if temp_path is None:
            print(f"[STEP 6] Download returned None, trying alternative method...")
            
            # ✅ METHOD 2: Try with just directory
            temp_path = await upload_client.download_media(
                message,
                file_name=downloads_dir,
                progress=progress_for_pyrogram,
                progress_args=("📥 Downloading (retry)...", download_msg, time.time())
            )
            
            print(f"[STEP 6] Retry returned: {temp_path}")
            
            if temp_path is None:
                # ✅ METHOD 3: Try without any file_name parameter
                print(f"[STEP 6] Still None, trying without file_name parameter...")
                temp_path = await upload_client.download_media(
                    message,
                    progress=progress_for_pyrogram,
                    progress_args=("📥 Downloading (final retry)...", download_msg, time.time())
                )
                
                print(f"[STEP 6] Final retry returned: {temp_path}")
                
                if temp_path is None:
                    raise ValueError("All download methods failed - file could not be downloaded")
        
        # Verify file exists
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"Downloaded file not found at: {temp_path}")
        
        file_stat = os.stat(temp_path)
        print(f"[STEP 6] File verified successfully")
        print(f"[STEP 6] File size: {humanbytes(file_stat.st_size)}")
        print(f"[STEP 6] Downloaded to: {temp_path}")
        
        # Now rename/move the file to our desired name
        if temp_path != renamed_file_path:
            print(f"[STEP 6] Renaming file...")
            print(f"[STEP 6] From: {temp_path}")
            print(f"[STEP 6] To: {renamed_file_path}")
            
            # Remove target if exists
            if os.path.exists(renamed_file_path):
                os.remove(renamed_file_path)
                print(f"[STEP 6] Removed existing target file")
            
            # Use shutil.move for cross-directory moves
            import shutil
            shutil.move(temp_path, renamed_file_path)
            path = renamed_file_path
            print(f"[STEP 6] ✅ File moved successfully")
        else:
            path = temp_path
            print(f"[STEP 6] File already has correct name")
        
        # Final verification
        if not os.path.exists(path):
            raise FileNotFoundError(f"File missing after rename: {path}")
        
        print(f"[STEP 6] Final path: {path}")
        print(f"[STEP 6] Final size: {humanbytes(os.path.getsize(path))}")
        
    except Exception as e:
        print(f"[ERROR STEP 5/6] Download failed: {type(e).__name__}: {e}")
        logging.error(f"Download error: {e}", exc_info=True)
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        return await download_msg.edit(f"**❌ Download Error:** `{e}`")
    
    # Add metadata if enabled
    await download_msg.edit("🔄 Processing...")
    
    metadata_added = False
    _bool_metadata = await pp_bots.get_metadata(user_id)
    
    print(f"[STEP 7] Metadata enabled: {_bool_metadata}")
    
    if _bool_metadata:
        metadata = await pp_bots.get_metadata_code(user_id)
        if metadata:
            print(f"[STEP 7] Metadata text: {metadata}")
            
            cmd = f'ffmpeg -i "{renamed_file_path}" -map 0 -c:s copy -c:a copy -c:v copy -metadata title="{metadata}" -metadata author="{metadata}" -metadata:s:s title="{metadata}" -metadata:s:a title="{metadata}" -metadata:s:v title="{metadata}" "{metadata_file_path}"'
            
            print(f"[STEP 7] FFmpeg command: {cmd[:200]}...")
            
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                
                print(f"[STEP 7] FFmpeg return code: {process.returncode}")
                
                if process.returncode == 0 and os.path.exists(metadata_file_path):
                    metadata_added = True
                    path = metadata_file_path
                    print(f"[STEP 7] ✅ Metadata added successfully")
                    print(f"[STEP 7] New file size: {humanbytes(os.path.getsize(path))}")
                else:
                    print(f"[STEP 7] ❌ Metadata failed")
                    if stderr:
                        stderr_text = stderr.decode()[:500]
                        print(f"[STEP 7] FFmpeg stderr: {stderr_text}")
            except asyncio.TimeoutError:
                logging.warning("Metadata addition timed out")
                print(f"[ERROR STEP 7] Metadata timeout (>300s)")
            except Exception as e:
                logging.error(f"Metadata error: {e}")
                print(f"[ERROR STEP 7] Metadata exception: {type(e).__name__}: {e}")
    
    if not metadata_added:
        path = renamed_file_path
        print(f"[STEP 7] Using original downloaded file (no metadata)")
    
    print(f"[STEP 8] Final file for upload: {path}")
    print(f"[STEP 8] File exists: {os.path.exists(path)}")
    
    # Upload
    upload_msg = await download_msg.edit("📤 Uploading...")
    
    try:
        # Get caption
        c_caption = await pp_bots.get_caption(user_id)
        print(f"[STEP 9] Caption template: {c_caption}")
        
        # Get duration if video
        duration = 0
        if media_type == "video":
            try:
                print(f"[STEP 9] Extracting video metadata...")
                metadata = extractMetadata(createParser(path))
                if metadata and metadata.has("duration"):
                    duration = metadata.get('duration').seconds
                print(f"[STEP 9] Video duration: {duration}s")
            except Exception as e:
                print(f"[STEP 9] Could not extract duration: {e}")
                pass
        
        caption = c_caption.format(
            filename=new_filename,
            filesize=humanbytes(file_size),
            duration=convert(duration)
        ) if c_caption else f"**{new_filename}**"
        
        print(f"[STEP 10] Final caption: {caption[:100]}...")
        
        # Get thumbnail
        ph_path = None
        c_thumb = await pp_bots.get_thumbnail(user_id)
        
        if c_thumb:
            print(f"[STEP 11] Custom thumbnail set, downloading...")
            try:
                ph_path = await client.download_media(c_thumb)
                print(f"[STEP 11] Custom thumbnail downloaded: {ph_path}")
            except Exception as e:
                print(f"[STEP 11] Custom thumbnail download failed: {e}")
        elif media_type == "video" and message.video and message.video.thumbs:
            print(f"[STEP 11] Using video thumbnail...")
            try:
                ph_path = await client.download_media(message.video.thumbs[0].file_id)
                print(f"[STEP 11] Video thumbnail downloaded: {ph_path}")
            except Exception as e:
                print(f"[STEP 11] Video thumbnail download failed: {e}")
        else:
            print(f"[STEP 11] No thumbnail available")
        
        if ph_path:
            try:
                print(f"[STEP 11] Processing thumbnail...")
                img = Image.open(ph_path).convert("RGB")
                img = img.resize((320, 320))
                img.save(ph_path, "JPEG")
                print(f"[STEP 11] Thumbnail processed: 320x320")
            except Exception as e:
                logging.error(f"Thumbnail processing error: {e}")
                print(f"[ERROR STEP 11] Thumbnail processing failed: {e}")
                clean_file(ph_path)
                ph_path = None
        
        # Upload destination
        upload_to = upload_channel if upload_channel else message.chat.id
        upload_client = app if (app and Config.STRING_SESSION) else client
        
        print(f"[STEP 12] Upload destination: {upload_to}")
        print(f"[STEP 12] Upload client: {'Premium (app)' if upload_client == app else 'Normal (client)'}")
        
        # Get media preference
        final_media_type = media_preference or media_type
        print(f"[STEP 12] Upload as: {final_media_type}")
        
        # Upload based on type
        print(f"[STEP 13] Starting upload...")
        
        if final_media_type == "document":
            print(f"[STEP 13] Uploading as DOCUMENT")
            sent = await upload_client.send_document(
                upload_to,
                document=path,
                thumb=ph_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        elif final_media_type == "video":
            print(f"[STEP 13] Uploading as VIDEO")
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
            print(f"[STEP 13] Uploading as AUDIO")
            sent = await upload_client.send_audio(
                upload_to,
                audio=path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", upload_msg, time.time())
            )
        
        print(f"[STEP 14] ✅ Upload complete!")
        print(f"[STEP 14] Message ID: {sent.id}")
        
        # Confirmation
        if upload_channel:
            try:
                channel_info = await client.get_chat(upload_channel)
                print(f"[STEP 15] Uploaded to channel: {channel_info.title}")
                await upload_msg.edit(
                    f"**✅ Upload Complete!**\n\n"
                    f"**Uploaded to:** {channel_info.title}\n"
                    f"**File:** {new_filename}\n"
                    f"**Size:** {humanbytes(file_size)}"
                )
            except Exception as e:
                print(f"[STEP 15] Could not get channel info: {e}")
                await upload_msg.edit("**✅ Upload Complete!**")
        else:
            print(f"[STEP 15] Uploaded to current chat")
            await upload_msg.delete()
        
        # Cleanup thumbnail
        if ph_path:
            clean_file(ph_path)
            print(f"[CLEANUP] Thumbnail deleted")
        
    except Exception as e:
        await upload_msg.edit(f"**❌ Upload Error:** `{e}`")
        logging.error(f"Upload error: {e}", exc_info=True)
        print(f"[ERROR STEP 12-15] Upload failed: {type(e).__name__}: {e}")
    
    finally:
        # Cleanup files
        print(f"[CLEANUP] Starting file cleanup...")
        clean_file(renamed_file_path)
        print(f"[CLEANUP] Deleted: {renamed_file_path}")
        clean_file(metadata_file_path)
        print(f"[CLEANUP] Deleted: {metadata_file_path}")
        if file_id in renaming_operations:
            del renaming_operations[file_id]
            print(f"[CLEANUP] Removed from operations dict")
        
        print(f"[RENAME MODE] Completed")
        print(f"{'='*60}\n")
