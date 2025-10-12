import re, os, time

id_pattern = re.compile(r'^.\d+$') 

class Config(object):
    # pyro client config
    API_ID    = os.environ.get("API_ID", "")
    API_HASH  = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

    # Premium user session for 4GB upload (OPTIONAL)
    STRING_SESSION = os.environ.get("STRING_SESSION", "")

    # database config
    DB_NAME = os.environ.get("DB_NAME","pp_bots")     
    DB_URL  = os.environ.get("DB_URL","")
 
    # other configs
    BOT_UPTIME  = time.time()
    START_PIC   = os.environ.get("START_PIC", "")
    
    # ADMIN - Parse safely
    admin_str = os.environ.get('ADMIN', '')
    if admin_str:
        ADMIN = [int(admin) if id_pattern.search(admin) else admin for admin in admin_str.split()]
    else:
        ADMIN = []
    
    # FORCE_SUB_CHANNELS - Parse safely (OPTIONAL)
    fsub_str = os.environ.get('FORCE_SUB_CHANNELS', '')
    if fsub_str and fsub_str.strip():
        FORCE_SUB_CHANNELS = [ch.strip() for ch in fsub_str.split(',') if ch.strip()]
    else:
        FORCE_SUB_CHANNELS = []
    
    # LOG_CHANNEL - Parse safely (OPTIONAL)
    log_channel_str = os.environ.get("LOG_CHANNEL", "0")
    try:
        LOG_CHANNEL = int(log_channel_str)
    except:
        LOG_CHANNEL = 0
    
    PORT = int(os.environ.get("PORT", "8080"))
    
    # File size limits
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB in bytes
    MAX_FILE_SIZE_NON_PREMIUM = 2 * 1024 * 1024 * 1024  # 2GB for non-premium
    
    # Special handler config (OPTIONAL)
    jai_channel_str = os.environ.get("JAI_BAJARANGABALI_CHANNEL", "-1002987317144")
    try:
        JAI_BAJARANGABALI_CHANNEL = int(jai_channel_str)
    except:
        JAI_BAJARANGABALI_CHANNEL = 0
    
    JAI_BAJARANGABALI_THUMB = os.environ.get("JAI_BAJARANGABALI_THUMB", "https://envs.sh/zcf.jpg")
    
    # Compression presets
    COMPRESSION_QUALITIES = {
        '1080p': {'resolution': '1920:1080', 'bitrate': '3000k'},
        '720p': {'resolution': '1280:720', 'bitrate': '2000k'},
        '576p': {'resolution': '1024:576', 'bitrate': '1500k'},
        '480p': {'resolution': '854:480', 'bitrate': '1000k'},
        '360p': {'resolution': '640:360', 'bitrate': '500k'}
    }
    
    # Media processing modes
    MEDIA_MODES = ['rename', 'trim', 'extract', 'merge', 'compress', 'autotrim']
    
    # webhook configuration     
    WEBHOOK = bool(os.environ.get("WEBHOOK", "True"))


class Txt(object):
    # Text configuration (same as before - keeping it short here)
        
    START_TXT = """Hello {} 👋
    
🎬 **Welcome to Advanced Media Bot!**

**✨ Main Features:**
├ 📝 Auto Rename with Templates
├ 🎞️ Video Compression (Multi-Quality)
├ ✂️ Trim Videos (Manual & Auto)
├ 🔗 Merge Videos/Audio/Subtitles
├ 🎵 Extract Audio/Subtitles
├ 🔄 Word Replacement System
├ 🖼️ Custom Thumbnails & Captions
├ 📤 Channel Auto-Upload
└ 💎 4GB Upload Support (Premium)

**🎯 Quick Start:**
• Send any media file to process
• Use /settings to configure bot
• Use /help for detailed guide

<b>Powered By @pp_bots</b>
"""
    
    HELP_TXT = """<b>📚 HELP MENU</b>

**⚙️ SETTINGS COMMANDS:**
├ /settings - Open Settings Panel
├ /autorename <format> - Set rename format
├ /autorename none - Clear format (use word replacement)
└ /status - View current settings

**📝 WORD REPLACEMENT:**
├ /remove word1,word2 - Remove words
├ /replace old:new,old2:new2 - Replace words
└ /clearwords - Clear replacement list

**🎬 MEDIA PROCESSING:**
├ /media rename - Rename mode
├ /media trim - Trim videos
├ /media extract - Extract audio/subtitles
├ /media merge - Merge files
├ /media compress - Compress videos
└ /media autotrim - Auto trim with detection

**🎞️ SPECIAL FEATURES:**
├ /autotrim <link> - Auto trim from link
├ /compress <qualities> - Compress (e.g., 720p,480p)
└ Special: "Jai Bajarangabali" auto-handler

**📢 CHANNEL UPLOAD:**
├ /setchannel <id> - Set upload channel
├ /viewchannel - View channel
└ /delchannel - Remove channel

**🎨 CUSTOMIZATION:**
├ Send photo - Set thumbnail
├ /viewthumb - View thumbnail
├ /delthumb - Delete thumbnail
├ /set_caption - Set custom caption
├ /see_caption - View caption
└ /del_caption - Delete caption

**📊 METADATA:**
├ /metadata - Manage metadata
└ Automatically added to files

<b>Need Support? @pp_bots</b>"""
    
    FILE_NAME_TXT = """<b><u>📝 SETUP AUTO RENAME FORMAT</u></b>

**Available Keywords:**
├ `[episode]` - Episode Number
├ `[quality]` - Video Resolution
├ `{filename}` - Original filename
├ `{filesize}` - File size
└ `{duration}` - Video duration

**Examples:**
<code>/autorename Naruto S01[episode] [quality] @pp_bots</code>
<code>/autorename Movie [quality] [Dual Audio]</code>

**Clear Format:**
<code>/autorename none</code>
<i>Then use /remove and /replace commands</i>

**Your Current Format:**
<code>{format_template}</code>"""
    
    ABOUT_TXT = """<b>🤖 BOT INFORMATION</b>

<b>📛 Bot Name:</b> Advanced Media Bot
<b>📝 Language:</b> <a href='https://python.org'>Python 3.10+</a>
<b>📚 Framework:</b> <a href='https://pyrogram.org'>Pyrogram 2.0</a>
<b>⚡ Server:</b> High-Performance VPS
<b>💾 Database:</b> MongoDB
<b>🎥 Media Engine:</b> FFmpeg
<b>🧑‍💻 Developer:</b> <a href='https://t.me/pp_bots'>PP Bots</a>

<b>✨ Version:</b> 3.0 Advanced
<b>📅 Last Update:</b> October 2025

<b>♻️ Powered By:</b> @pp_bots"""
    
    THUMBNAIL_TXT = """<b><u>🖼️ THUMBNAIL SETUP</u></b>
    
**How to Set:**
⦿ Simply send any photo to me
⦿ It will be saved as your thumbnail

**Commands:**
├ /viewthumb - View current thumbnail
└ /delthumb - Delete thumbnail

**Note:** Thumbnail applies to all uploads"""

    CAPTION_TXT = """<b><u>📝 CAPTION SETUP</u></b>
    
**Set Custom Caption:**
<code>/set_caption Your caption here</code>

**Available Variables:**
├ `{filename}` - File name
├ `{filesize}` - File size
└ `{duration}` - Duration

**Example:**
<code>/set_caption 📕 {filename}
🔗 Size: {filesize}
⏰ Duration: {duration}
@pp_bots</code>

**Commands:**
├ /see_caption - View caption
└ /del_caption - Delete caption"""

    CHANNEL_TXT = """<b><u>📢 CHANNEL UPLOAD SETUP</u></b>
    
**Setup Steps:**
1️⃣ Add bot as admin in your channel
2️⃣ Forward any message from channel to @userinfobot
3️⃣ Copy the channel ID
4️⃣ Use command below

**Commands:**
├ /setchannel -100123456789
├ /viewchannel - View settings
└ /delchannel - Remove channel

**Note:** All processed files will auto-upload to your channel!"""

    SETTINGS_TXT = """<b>⚙️ BOT SETTINGS</b>

**Current Configuration:**
├ 📝 Rename Format: `{format}`
├ 🎬 Media Mode: `{mode}`
├ 📢 Upload Channel: `{channel}`
├ 🖼️ Thumbnail: `{thumb}`
├ ✏️ Caption: `{caption}`
├ 📋 Metadata: `{metadata}`
└ 💎 Premium: `{premium}`

**Word Replacement:**
├ Remove Words: `{remove_words}`
└ Replace Words: `{replace_words}`

Use buttons below to configure ⬇️"""

    PROGRESS_BAR = """<b>\n
╭━━━━❰ᴘʀᴏɢʀᴇss ʙᴀʀ❱━➣
┣⪼ 🗃️ Size: {1} | {2}
┣⪼ ⏳️ Done: {0}%
┣⪼ 🚀 Speed: {3}/s
┣⪼ ⏰️ ETA: {4}
╰━━━━━━━━━━━━━━━➣ </b>"""
    
    DONATE_TXT = """<b>🥲 Thanks For Showing Interest In Donation! ❤️</b>
    
If You Like My Bots & Projects, You Can 🎁 Donate Me Any Amount From 10 Rs Upto Your Choice.
    
<b>My UPI - ppbots@ybl</b>

<b>Support keeps us running!</b> 💖"""
