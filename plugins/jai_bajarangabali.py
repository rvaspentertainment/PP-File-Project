from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from helper.utils import (
    progress_for_pyrogram, humanbytes, convert, 
    sanitize_filename, download_thumbnail, clean_file
)
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from bot import app  # Premium client
import os
import re
import time
import logging


# Pattern to extract episode number
def extract_episode_number(filename):
    """Extract episode number from filename"""
    patterns = [
        r'(?:E|EP|Episode)\s*(\d+)',
        r'S\d+E(\d+)',
        r'\s+(\d+)\s+',
        r'-\s*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "01"


async def handle_jai_bajarangabali(client, message: Message):
    """
    Special handler for Jai Bajarangabali files
    Auto-processes and uploads to specific channel
    """
    file_path = None
    thumb_path = None
    ms = None
    
    try:
        # Get media info
        if message.document:
            file = message.document
            filename = file.file_name
            file_size = file.file_size
        elif message.video:
            file = message.video
            filename = file.file_name or "video.mp4"
            file_size = file.file_size
        else:
            return await message.reply_text("**Unsupported file type!**")
        
        # Extract quality from brackets [720p]
        bracket_match = re.search(r'\[(\d+p)\]', filename)
        if bracket_match:
            quality = bracket_match.group(1)
            # Remove existing quality tags
            new_name = re.sub(r'\d+p', '', filename)
            new_name = re.sub(r'\[.*?\]', '', new_name)
            
            # Add quality before extension
            name_parts = new_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]} {quality}.{name_parts[1]}"
            else:
                new_name = f"{new_name} {quality}"
            
            # Clean up
            new_name = re.sub(r'\.+', '.', new_name)
            new_name = re.sub(r'\s+', ' ', new_name).strip()
        else:
            new_name = filename
            quality = "Unknown"
        
        # Extract episode number
        episode_number = extract_episode_number(filename)
        
        # Select upload client
        upload_client = app if app and Config.STRING_SESSION else client
        
        # Prepare file paths
        safe_filename = sanitize_filename(new_name)
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        file_path = os.path.join(downloads_dir, safe_filename)
        thumb_path = os.path.join(downloads_dir, f"thumb_jai_{episode_number}.jpg")
        
        # Status message
        status_text = "🔄 **Auto-Processing Jai Bajarangabali...**\n"
        status_text += "📥 Downloading..."
        if app and Config.STRING_SESSION:
            status_text += "\n✅ Premium Mode (4GB)"
        
        ms = await message.reply_text(status_text)
        
        # Download file
        try:
            await upload_client.download_media(
                message=message,
                file_name=file_path,
                progress=progress_for_pyrogram,
                progress_args=("📥 Downloading...", ms, time.time())
            )
        except Exception as e:
            await ms.edit(f"❌ **Download Failed!**\n\n`{str(e)}`")
            return
        
        if not os.path.exists(file_path):
            await ms.edit("❌ **Download failed! File not found.**")
            return
        
        logging.info(f"✅ Downloaded: {file_path} ({humanbytes(os.path.getsize(file_path))})")
        
        # Extract metadata
        duration = 0
        try:
            await ms.edit("📊 Extracting metadata...")
            metadata = extractMetadata(createParser(file_path))
            if metadata and metadata.has("duration"):
                duration = metadata.get('duration').seconds
        except Exception as e:
            logging.error(f"Metadata error: {e}")
        
        # Download thumbnail
        ph_path = None
        try:
            await ms.edit("🎨 Preparing thumbnail...")
            if download_thumbnail(Config.JAI_BAJARANGABALI_THUMB, thumb_path):
                ph_path = thumb_path
        except Exception as e:
            logging.error(f"Thumbnail error: {e}")
        
        # Prepare caption
        try:
            caption = f"**Jai Bajarangabali Episode {episode_number}**\n\n"
            caption += f"📺 Quality: {quality}\n"
            caption += f"💾 Size: {humanbytes(file_size)}\n"
            caption += f"⏱ Duration: {convert(duration)}\n\n"
            caption += "@pp_bots"
        except:
            caption = f"**Jai Bajarangabali Episode {episode_number}**\n\n@pp_bots"
        
        # Upload to channel
        await ms.edit("📤 Uploading to channel...")
        
        try:
            await upload_client.send_video(
                Config.JAI_BAJARANGABALI_CHANNEL,
                video=file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("📤 Uploading...", ms, time.time())
            )
            
            await ms.edit(
                f"✅ **Successfully Uploaded!**\n\n"
                f"**Episode:** {episode_number}\n"
                f"**Quality:** {quality}\n"
                f"**Size:** {humanbytes(file_size)}\n\n"
                f"Uploaded to Jai Bajarangabali Channel"
            )
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Upload error: {error_msg}")
            await ms.edit(f"❌ **Upload Failed!**\n\n`{error_msg}`")
    
    except Exception as e:
        logging.error(f"Jai Bajarangabali handler error: {e}")
        try:
            if ms:
                await ms.edit(f"❌ **Error:** `{str(e)}`")
            else:
                await message.reply_text(f"❌ **Error:** `{str(e)}`")
        except:
            pass
    
    finally:
        # Cleanup
        clean_file(file_path)
        clean_file(thumb_path)


def is_jai_bajarangabali_file(filename):
    """Check if filename starts with 'Jai Bajarangabali'"""
    if not filename:
        return False
    
    return filename.lower().startswith("jai bajarangabali")
