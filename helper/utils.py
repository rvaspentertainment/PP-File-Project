import math, time, os, re, shutil
from datetime import datetime
from pytz import timezone
from config import Config, Txt 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import requests
import logging


async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 5.00) == 0 or current == total:        
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "{0}{1}".format(
            ''.join(["⬢" for i in range(math.floor(percentage / 5))]),
            ''.join(["⬡" for i in range(20 - math.floor(percentage / 5))])
        )            
        tmp = progress + Txt.PROGRESS_BAR.format( 
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),            
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",               
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ CANCEL ✖️", callback_data="close")]])                                               
            )
        except:
            pass


def humanbytes(size):    
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2] 


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)


async def send_log(b, u):
    if Config.LOG_CHANNEL:
        try:
            curr = datetime.now(timezone("Asia/Kolkata"))
            date = curr.strftime('%d %B, %Y')
            time = curr.strftime('%I:%M:%S %p')
            await b.send_message(
                Config.LOG_CHANNEL,
                f"**--New User Started The Bot--**\n\n"
                f"User: {u.mention}\n"
                f"ID: `{u.id}`\n"
                f"Username: @{u.username}\n\n"
                f"Date: {date}\n"
                f"Time: {time}\n\n"
                f"By: {b.mention}"
            )
        except Exception as e:
            logging.error(f"Error sending log: {e}")


def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    return filename


def beautify_filename(filename):
    """Make filename more readable"""
    # Remove extra dots
    filename = re.sub(r'\.+', '.', filename)
    # Remove extra spaces
    filename = re.sub(r'\s+', ' ', filename)
    # Capitalize words
    return filename.strip()


def get_disk_space():
    """Get available disk space in bytes"""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return disk.free
    except:
        return 0


def download_thumbnail(url, save_path):
    """Download thumbnail from URL"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        logging.error(f"Thumbnail download error: {e}")
        return False


def clean_file(file_path):
    """Safely remove file if exists"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logging.error(f"Error removing file {file_path}: {e}")
    return False


def clean_directory(directory):
    """Clean all files in directory"""
    try:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logging.error(f"Error removing {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error cleaning directory {directory}: {e}")


def apply_word_removal(text, remove_words):
    """Remove specified words from text"""
    if not remove_words:
        return text
    
    for word in remove_words:
        # Remove word (case sensitive to preserve intentional casing)
        text = text.replace(word, '')
    
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def apply_word_replacement(text, replace_dict):
    """Replace words in text based on dictionary"""
    if not replace_dict:
        return text
    
    for old, new in replace_dict.items():
        # Replace word (case sensitive)
        text = text.replace(old, new)
    
    return text


def clean_underscores_dots(text):
    """
    Clean filename by replacing underscores and dots with spaces
    Handles patterns like: movie.2022.360p or movie_2022_360p
    """
    # Replace underscores with spaces
    text = text.replace('_', ' ')
    
    # Replace dots with spaces (except in numbers like 1.5, 2.0 etc)
    text = text.replace('.', ' ')
    
    # Remove multiple consecutive spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing spaces
    text = text.strip()
    
    return text


async def apply_all_transformations(filename, user_id, pp_bots):
    """
    Apply all transformations in order:
    1. Add prefix
    2. Remove words
    3. Replace words
    4. Clean underscores/dots to spaces
    5. Add suffix
    """
    name, ext = os.path.splitext(filename)
    
    # Step 1: Get prefix
    prefix = await pp_bots.get_prefix(user_id)
    if prefix:
        name = f"{prefix} {name}"
        logging.info(f"[TRANSFORM] After prefix: {name}")
    
    # Step 2: Remove words
    remove_words = await pp_bots.get_remove_words(user_id)
    if remove_words:
        name = apply_word_removal(name, remove_words)
        logging.info(f"[TRANSFORM] After removal: {name}")
    
    # Step 3: Replace words
    replace_words = await pp_bots.get_replace_words(user_id)
    if replace_words:
        name = apply_word_replacement(name, replace_words)
        logging.info(f"[TRANSFORM] After replacement: {name}")
    
    # Step 4: Clean underscores and dots
    name = clean_underscores_dots(name)
    logging.info(f"[TRANSFORM] After cleaning: {name}")
    
    # Step 5: Get suffix
    suffix = await pp_bots.get_suffix(user_id)
    if suffix:
        name = f"{name} {suffix}"
        logging.info(f"[TRANSFORM] After suffix: {name}")
    
    # Final cleanup
    name = re.sub(r'\s+', ' ')
    name = name.strip()
    
    return f"{name}{ext}"


def get_file_extension(filename):
    """Get file extension"""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_video_file(filename):
    """Check if file is video"""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v']
    return get_file_extension(filename) in video_extensions


def is_audio_file(filename):
    """Check if file is audio"""
    audio_extensions = ['.mp3', '.m4a', '.aac', '.opus', '.flac', '.wav', '.ogg']
    return get_file_extension(filename) in audio_extensions


def is_subtitle_file(filename):
    """Check if file is subtitle"""
    subtitle_extensions = ['.srt', '.ass', '.vtt', '.sub']
    return get_file_extension(filename) in subtitle_extensions


def parse_time(time_str):
    """Parse time string to seconds (HH:MM:SS or MM:SS or SS)"""
    try:
        parts = time_str.strip().split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        elif len(parts) == 1:
            return int(parts[0])
    except:
        return None
    return None


def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


async def get_media_info(file_path):
    """Get media file information"""
    try:
        from hachoir.metadata import extractMetadata
        from hachoir.parser import createParser
        
        parser = createParser(file_path)
        if parser:
            metadata = extractMetadata(parser)
            if metadata:
                info = {
                    'duration': 0,
                    'width': 0,
                    'height': 0,
                    'has_audio': False,
                    'has_video': False
                }
                
                if metadata.has("duration"):
                    info['duration'] = metadata.get('duration').seconds
                if metadata.has("width"):
                    info['width'] = metadata.get('width')
                if metadata.has("height"):
                    info['height'] = metadata.get('height')
                if metadata.has("audio_codec"):
                    info['has_audio'] = True
                if metadata.has("video_codec"):
                    info['has_video'] = True
                    
                return info
    except Exception as e:
        logging.error(f"Error getting media info: {e}")
    
    return None


def check_premium_client(app):
    """Check if premium client is available and has premium"""
    try:
        if app and hasattr(app, 'me') and app.me:
            return getattr(app.me, 'is_premium', False)
        return False
    except:
        return False
