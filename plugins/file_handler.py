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
from bot import app as premium_client
from datetime import datetime
import os
import time
import re
import asyncio
import logging
import uuid
import shutil


renaming_operations = {}


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
            await message.reply_text(
                "**🤖 Auto Trim Mode**\n\n"
                "This feature is coming soon!\n\n"
                "Use `/media trim` for manual trimming."
            )
        
        else:
            print(f"[MAIN HANDLER] Unknown mode, defaulting to RENAME")
            await handle_rename_mode(client, message, file, filename, file_size, media_type)
            
    except Exception as e:
        logging.error(f"Error in media handler: {e}")
        print(f"[MAIN HANDLER ERROR] {e}")
        await message.reply_text(f"**❌ Error processing file:** `{e}`")


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
    """Handle file renaming with new advanced caption logic"""
    print(f"\n{'='*60}")
    print(f"[RENAME MODE] Started")
    
    user_id = message.from_user.id
    media_preference = await pp_bots.get_media_preference(user_id)
    upload_channel = await pp_bots.get_upload_channel(user_id)
    
    print(f"[RENAME MODE] Media preference: {media_preference}")
    print(f"[RENAME MODE] Upload channel: {upload_channel}")
    
    # ✅ Check if premium client is available
    use_premium = False
    if premium_client and Config.STRING_SESSION:
        try:
            me = await premium_client.get_me()
            if me:
                use_premium = True
                print(f"[RENAME MODE] Premium client available: {me.first_name}")
        except Exception as e:
            print(f"[RENAME MODE] Premium client not available: {e}")
    
    # Check file size
    max_size = Config.MAX_FILE_SIZE if use_premium else Config.MAX_FILE_SIZE_NON_PREMIUM
    if file_size > max_size:
        size_gb = file_size / (1024 * 1024 * 1024)
        max_gb = max_size / (1024 * 1024 * 1024)
        print(f"[RENAME MODE] File too large: {size_gb:.2f} GB > {max_gb:.2f} GB")
        return await message.reply_text(
            f"**❌ File Too Large!**\n\n"
            f"**File Size:** {size_gb:.2f} GB\n"
            f"**Maximum:** {max_gb:.2f} GB\n\n"
            f"{'💡 Add premium session for 4GB support' if not use_premium else 'Premium session active but file exceeds 4GB limit'}"
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
    
    # Get file extension
    _, file_extension = os.path.splitext(filename)
    print(f"[STEP 1] File extension: {file_extension}")
    
    # Get remove and replace words
    remove_words = await pp_bots.get_remove_words(user_id)
    replace_words = await pp_bots.get_replace_words(user_id)
    
    print(f"[STEP 2] Remove words: {remove_words}")
    print(f"[STEP 2] Replace words: {replace_words}")
    print(f"[STEP 2] Caption: {message.caption}")
    
    # ✅ NEW ADVANCED LOGIC
    new_filename = None
    ask_user = False
    
    # Check if caption has extension
    caption_has_extension = False
    if message.caption:
        caption_lower = message.caption.lower()
        caption_has_extension = any(caption_lower.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.mp3', '.flac', '.wav', '.m4a'])
    
    if message.caption:
        print(f"[STEP 2] Caption provided: {message.caption}")
        print(f"[STEP 2] Caption has extension: {caption_has_extension}")
        
        # CASE 1: Caption WITH extension + Remove/Replace words exist
        if caption_has_extension and (remove_words or replace_words):
            print(f"[STEP 2] CASE 1: Caption with extension + remove/replace exists")
            # Use caption, apply remove/replace
            name_without_ext = os.path.splitext(message.caption)[0]
            caption_ext = os.path.splitext(message.caption)[1]
            
            if remove_words:
                name_without_ext = apply_word_removal(name_without_ext, remove_words)
                print(f"[STEP 2] After removal: {name_without_ext}")
            
            if replace_words:
                name_without_ext = apply_word_replacement(name_without_ext, replace_words)
                print(f"[STEP 2] After replacement: {name_without_ext}")
            
            new_filename = f"{name_without_ext}{caption_ext}"
            print(f"[STEP 2] ✅ Result: {new_filename}")
        
        # CASE 2: Caption WITHOUT extension (use filename + apply remove/replace if exists)
        elif not caption_has_extension:
            print(f"[STEP 2] CASE 2: Caption without extension")
            # Use original filename
            name_without_ext = os.path.splitext(filename)[0]
            
            if remove_words or replace_words:
                print(f"[STEP 2] Remove/Replace exists - applying")
                
                if remove_words:
                    name_without_ext = apply_word_removal(name_without_ext, remove_words)
                    print(f"[STEP 2] After removal: {name_without_ext}")
                
                if replace_words:
                    name_without_ext = apply_word_replacement(name_without_ext, replace_words)
                    print(f"[STEP 2] After replacement: {name_without_ext}")
                
                new_filename = f"{name_without_ext}{file_extension}"
                print(f"[STEP 2] ✅ Result: {new_filename}")
            else:
                print(f"[STEP 2] No remove/replace - will ask user")
                ask_user = True
        
        # CASE 3: Caption WITH extension + NO Remove/Replace
        elif caption_has_extension and not remove_words and not replace_words:
            print(f"[STEP 2] CASE 3: Caption with extension + no remove/replace")
            print(f"[STEP 2] Will ask user for new name")
            ask_user = True
    
    else:
        # No caption provided
        print(f"[STEP 2] No caption provided")
        
        if remove_words or replace_words:
            # Apply remove/replace to filename
            print(f"[STEP 2] Remove/Replace exists - applying to filename")
            name_without_ext = os.path.splitext(filename)[0]
            
            if remove_words:
                name_without_ext = apply_word_removal(name_without_ext, remove_words)
                print(f"[STEP 2] After removal: {name_without_ext}")
            
            if replace_words:
                name_without_ext = apply_word_replacement(name_without_ext, replace_words)
                print(f"[STEP 2] After replacement: {name_without_ext}")
            
            new_filename = f"{name_without_ext}{file_extension}"
            print(f"[STEP 2] ✅ Result: {new_filename}")
        else:
            # No caption, no remove/replace - ask user
            print(f"[STEP 2] No remove/replace - will ask user")
            ask_user = True
    
    # Ask user if needed
    if ask_user:
        print(f"[STEP 2] Asking user for new filename")
        
        try:
            response = await client.ask(
                user_id,
                f"**📝 RENAME FILE**\n\n"
                f"**Current Name:** `{filename}`\n"
                f"**Size:** {humanbytes(file_size)}\n\n"
                f"**Send new filename (with extension):**\n"
                f"Example: `My_Video{file_extension}`\n\n"
                f"⏱️ You have 60 seconds to reply.\n"
                f"Send /cancel to cancel.",
                timeout=60
            )
            
            if response.text == "/cancel":
                await response.request.delete()
                await response.delete()
                if file_id in renaming_operations:
                    del renaming_operations[file_id]
                return await message.reply_text("**❌ Rename cancelled.**")
            
            # Use user's response
            user_filename = response.text.strip()
            
            # Add extension if missing
            if not any(user_filename.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.mp3', '.flac', '.wav', '.m4a']):
                user_filename = f"{user_filename}{file_extension}"
            
            new_filename = user_filename
            print(f"[STEP 2] ✅ User provided: {new_filename}")
            
            # Delete ask messages
            try:
                await response.request.delete()
                await response.delete()
            except:
                pass
            
            # ✅ NEW: After user provides name, apply remove/replace
            remove_words = await pp_bots.get_remove_words(user_id)
            replace_words = await pp_bots.get_replace_words(user_id)
            
            if remove_words or replace_words:
                print(f"[STEP 2] Applying remove/replace after user input")
                name_without_ext = os.path.splitext(new_filename)[0]
                
                if remove_words:
                    name_without_ext = apply_word_removal(name_without_ext, remove_words)
                    print(f"[STEP 2] After removal: {name_without_ext}")
                
                if replace_words:
                    name_without_ext = apply_word_replacement(name_without_ext, replace_words)
                    print(f"[STEP 2] After replacement: {name_without_ext}")
                
                new_filename = f"{name_without_ext}{file_extension}"
                print(f"[STEP 2] After remove/replace: {new_filename}")
            
        except asyncio.TimeoutError:
            new_filename = filename
            print(f"[STEP 2] ⏱️ Timeout - using original filename")
            await message.reply_text("**⏱️ Timeout!** Using original filename.", quote=True)
            await asyncio.sleep(2)
    
    # Sanitize filename
    new_filename = sanitize_filename(new_filename)
    print(f"[STEP 3] Sanitized filename: {new_filename}")
    
    # ✅ NEW: Apply prefix, suffix, and clean underscores/dots
    name_without_ext = os.path.splitext(new_filename)[0]
    
    # Get prefix and suffix
    prefix = await pp_bots.get_prefix(user_id)
    suffix = await pp_bots.get_suffix(user_id)
    
    print(f"[STEP 3] Prefix: {prefix}")
    print(f"[STEP 3] Suffix: {suffix}")
    
    # Apply prefix
    if prefix:
        name_without_ext = f"{prefix} {name_without_ext}"
        print(f"[STEP 3] After prefix: {name_without_ext}")
    
    # Clean underscores and dots to spaces
    name_without_ext = name_without_ext.replace('_', ' ')
    name_without_ext = name_without_ext.replace('.', ' ')
    # Remove multiple consecutive spaces
    import re
    name_without_ext = re.sub(r'\s+', ' ', name_without_ext)
    name_without_ext = name_without_ext.strip()
    print(f"[STEP 3] After cleaning _/.: {name_without_ext}")
    
    # Apply suffix
    if suffix:
        name_without_ext = f"{name_without_ext} {suffix}"
        print(f"[STEP 3] After suffix: {name_without_ext}")
    
    # Final filename
    new_filename = f"{name_without_ext}{file_extension}"
    new_filename = sanitize_filename(new_filename)
    print(f"[STEP 3] Final filename: {new_filename}")
    
    # Setup paths
    downloads_dir = "downloads"
    metadata_dir = "Metadata"
    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    
    print(f"[STEP 4] Directories created/verified")
    
    # Create paths
    temp_filename = f"temp_{uuid.uuid4().hex[:8]}{file_extension}"
    temp_file_path = os.path.join(downloads_dir, temp_filename)
    renamed_file_path = os.path.join(downloads_dir, new_filename)
    metadata_file_path = os.path.join(metadata_dir, new_filename)
    
    print(f"[STEP 4] Temp path: {temp_file_path}")
    print(f"[STEP 4] Final path: {renamed_file_path}")
    print(f"[STEP 4] Metadata path: {metadata_file_path}")
    
    # Download
    download_msg = await message.reply_text("📥 Downloading...")
    
    try:
        # ✅ Smart client selection for download
        if file_size > Config.MAX_FILE_SIZE_NON_PREMIUM and use_premium:
            download_client = premium_client
            print(f"[STEP 5] Using PREMIUM client for download (large file)")
        else:
            download_client = client
            print(f"[STEP 5] Using BOT client for download")
        
        print(f"[STEP 5] Starting download...")
        print(f"[STEP 5] File ID: {file.file_id}")
        
        # Download
        temp_path = await download_client.download_media(
            message,
            file_name=temp_file_path,
            progress=progress_for_pyrogram,
            progress_args=("📥 Downloading...", download_msg, time.time())
        )
        
        print(f"[STEP 6] Download result: {temp_path}")
        
        # Fallback to premium if bot failed
        if temp_path is None and download_client != premium_client and use_premium:
            print(f"[STEP 6] Bot client failed, trying premium client...")
            download_client = premium_client
            
            temp_path = await download_client.download_media(
                message,
                file_name=temp_file_path,
                progress=progress_for_pyrogram,
                progress_args=("📥 Downloading (premium)...", download_msg, time.time())
            )
            
            print(f"[STEP 6] Premium download result: {temp_path}")
        
        if temp_path is None:
            raise ValueError("Download failed - returned None")
        
        # Verify file
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"Downloaded file not found at: {temp_path}")
        
        file_stat = os.stat(temp_path)
        print(f"[STEP 6] ✅ File verified - Size: {humanbytes(file_stat.st_size)}")
        
        # Rename to final filename
        if temp_path != renamed_file_path:
            print(f"[STEP 6] Renaming file...")
            
            if os.path.exists(renamed_file_path):
                os.remove(renamed_file_path)
            
            shutil.move(temp_path, renamed_file_path)
            path = renamed_file_path
            print(f"[STEP 6] ✅ File renamed")
        else:
            path = temp_path
        
        print(f"[STEP 6] Final path: {path}")
        
    except Exception as e:
        print(f"[ERROR STEP 5/6] Download failed: {type(e).__name__}: {e}")
        logging.error(f"Download error: {e}", exc_info=True)
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        return await download_msg.edit(f"**❌ Download Error:** `{e}`")
    
    # Add metadata
    await download_msg.edit("🔄 Processing...")
    
    metadata_added = False
    _bool_metadata = await pp_bots.get_metadata(user_id)
    
    print(f"[STEP 7] Metadata enabled: {_bool_metadata}")
    
    if _bool_metadata:
        metadata = await pp_bots.get_metadata_code(user_id)
        if metadata:
            print(f"[STEP 7] Adding metadata: {metadata}")
            
            metadata_escaped = metadata.replace('"', '\\"').replace("'", "\\'")
            
            cmd = f'ffmpeg -i "{renamed_file_path}" -map 0 -c:s copy -c:a copy -c:v copy -metadata title="{metadata_escaped}" -metadata author="{metadata_escaped}" -metadata:s:s title="{metadata_escaped}" -metadata:s:a title="{metadata_escaped}" -metadata:s:v title="{metadata_escaped}" "{metadata_file_path}"'
            
            print(f"[STEP 7] Running FFmpeg...")
            
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
                    print(f"[STEP 7] ✅ Metadata added")
                else:
                    print(f"[STEP 7] ❌ Metadata failed")
            except asyncio.TimeoutError:
                logging.warning("Metadata addition timed out")
                print(f"[ERROR STEP 7] Timeout")
            except Exception as e:
                logging.error(f"Metadata error: {e}")
                print(f"[ERROR STEP 7] {e}")
    
    if not metadata_added:
        path = renamed_file_path
        print(f"[STEP 7] No metadata added")
    
    # Upload
    upload_msg = await download_msg.edit("📤 Uploading...")
    
    try:
        # Get caption
        c_caption = await pp_bots.get_caption(user_id)
        
        # Get duration
        duration = 0
        if media_type == "video":
            try:
                metadata = extractMetadata(createParser(path))
                if metadata and metadata.has("duration"):
                    duration = metadata.get('duration').seconds
                print(f"[STEP 9] Video duration: {duration}s")
            except:
                pass
        
        caption = c_caption.format(
            filename=new_filename,
            filesize=humanbytes(file_size),
            duration=convert(duration)
        ) if c_caption else f"**{new_filename}**"
        
        print(f"[STEP 10] Caption ready")
        
        # Get thumbnail
        ph_path = None
        c_thumb = await pp_bots.get_thumbnail(user_id)
        
        if c_thumb:
            try:
                print(f"[STEP 11] Downloading custom thumbnail...")
                ph_path = await client.download_media(c_thumb)
                print(f"[STEP 11] Custom thumbnail downloaded")
            except Exception as e:
                print(f"[STEP 11] Custom thumbnail failed: {e}")
                ph_path = None
        elif media_type == "video" and message.video and message.video.thumbs:
            try:
                print(f"[STEP 11] Downloading video thumbnail...")
                ph_path = await client.download_media(message.video.thumbs[0].file_id)
                print(f"[STEP 11] Video thumbnail downloaded")
            except Exception as e:
                print(f"[STEP 11] Video thumbnail failed: {e}")
                ph_path = None
        
        if ph_path:
            try:
                print(f"[STEP 11] Processing thumbnail...")
                img = Image.open(ph_path).convert("RGB")
                img = img.resize((320, 320))
                img.save(ph_path, "JPEG")
                print(f"[STEP 11] Thumbnail processed")
            except Exception as e:
                print(f"[STEP 11] Thumbnail processing failed: {e}")
                clean_file(ph_path)
                ph_path = None
        else:
            print(f"[STEP 11] No thumbnail available")
        
        # ✅ CRITICAL: Smart client selection for upload
        upload_to = upload_channel if upload_channel else message.chat.id
        
        # Use premium client for large files
        if file_size > Config.MAX_FILE_SIZE_NON_PREMIUM:
            if use_premium:
                upload_client = premium_client
                print(f"[STEP 12] Using PREMIUM client for upload (file > 2GB)")
            else:
                raise Exception("File larger than 2GB but premium client not available")
        else:
            upload_client = client
            print(f"[STEP 12] Using BOT client for upload (file <= 2GB)")
        
        # Verify upload client is ready
        try:
            await upload_client.get_me()
            print(f"[STEP 12] Upload client verified and ready")
        except Exception as e:
            print(f"[STEP 12] Upload client verification failed: {e}")
            if upload_client == premium_client and client:
                print(f"[STEP 12] Falling back to bot client")
                upload_client = client
            else:
                raise Exception(f"Upload client not ready: {e}")
        
        final_media_type = media_preference or media_type
        
        print(f"[STEP 13] Uploading as {final_media_type}...")
        print(f"[STEP 13] File size: {humanbytes(file_size)}")
        print(f"[STEP 13] Upload to: {upload_to}")
        
        # Upload
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
        
        print(f"[STEP 14] ✅ Upload complete!")
        
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
        logging.error(f"Upload error: {e}", exc_info=True)
        print(f"[ERROR STEP 12-15] {e}")
    
    finally:
        # Cleanup
        print(f"[CLEANUP] Cleaning up...")
        clean_file(renamed_file_path)
        clean_file(metadata_file_path)
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        
        print(f"[RENAME MODE] Completed")
        print(f"{'='*60}\n")
