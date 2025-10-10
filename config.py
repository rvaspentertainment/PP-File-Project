import re, os, time
id_pattern = re.compile(r'^.\d+$') 

class Config(object):
    # pyro client config
    API_ID    = os.environ.get("API_ID", "")
    API_HASH  = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

    # Premium user session for 4GB upload
    STRING_SESSION = os.environ.get("STRING_SESSION", "")

    # database config
    DB_NAME = os.environ.get("DB_NAME","pp_bots")     
    DB_URL  = os.environ.get("DB_URL","")
 
    # other configs
    BOT_UPTIME  = time.time()
    START_PIC   = os.environ.get("START_PIC", "")
    ADMIN       = [int(admin) if id_pattern.search(admin) else admin for admin in os.environ.get('ADMIN', '').split()]
    FORCE_SUB_CHANNELS = os.environ.get('FORCE_SUB_CHANNELS', 'pp_bots').split(',')
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
    PORT = int(os.environ.get("PORT", "8080"))
    
    # File size limits
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4GB in bytes
    MAX_FILE_SIZE_NON_PREMIUM = 2 * 1024 * 1024 * 1024  # 2GB for non-premium
    
    # Special handler config
    JAI_BAJARANGABALI_CHANNEL = int(os.environ.get("JAI_BAJARANGABALI_CHANNEL", "-1002987317144"))
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
    # Text configuration
        
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

    MEDIA_MODE_TXT = """<b>🎬 MEDIA PROCESSING MODE</b>

**Select Processing Mode:**

├ 📝 **Rename** - Rename files with template
├ ✂️ **Trim** - Cut/trim videos
├ 🎵 **Extract** - Extract audio/subtitles
├ 🔗 **Merge** - Merge multiple files
├ 🎞️ **Compress** - Compress to multiple qualities
└ 🤖 **Auto Trim** - Auto detection & trim

**Current Mode:** `{current_mode}`

Select mode using buttons below:"""

    COMPRESS_TXT = """<b>🎞️ VIDEO COMPRESSION</b>

**Available Qualities:**
├ 1080p (Full HD) - 3000k bitrate
├ 720p (HD) - 2000k bitrate
├ 576p (SD) - 1500k bitrate
├ 480p (SD) - 1000k bitrate
└ 360p (Low) - 500k bitrate

**How to Use:**
Send video file in compress mode
Or use: /compress 720p,480p,360p

**Features:**
✓ Multiple quality output
✓ Fast encoding (H.264)
✓ Maintains aspect ratio
✓ Auto thumbnail generation"""

    TRIM_TXT = """<b>✂️ VIDEO TRIMMING</b>

**Manual Trim:**
1. Enable trim mode: /media trim
2. Send video file
3. Enter start time (HH:MM:SS)
4. Enter end time (HH:MM:SS)

**Auto Trim:**
1. Enable: /media autotrim
2. Send video or link
3. Bot detects intro/outro automatically
4. Trimmed video delivered

**Trim from Link:**
<code>/autotrim video_link</code>
<code>/autotrim video_link intro_title</code>"""

    MERGE_TXT = """<b>🔗 FILE MERGING</b>

**How to Merge:**
1. Enable: /media merge
2. Choose merge type:
   ├ Video + Video
   ├ Video + Audio
   ├ Video + Subtitle
   └ Multiple files

3. Send files one by one
4. Type 'done' when finished
5. Bot merges and sends

**Supported Formats:**
├ Videos: MP4, MKV, AVI, MOV
├ Audio: MP3, AAC, M4A, OPUS
└ Subtitles: SRT, ASS, VTT"""

    EXTRACT_TXT = """<b>🎵 AUDIO/SUBTITLE EXTRACTION</b>

**Extract Audio:**
1. Enable: /media extract
2. Send video file
3. Select: Extract Audio
4. Choose format (MP3/M4A/OPUS)

**Extract Subtitles:**
1. Enable: /media extract
2. Send video file
3. Select: Extract Subtitles
4. Choose language/format

**Features:**
✓ High quality extraction
✓ Multiple format support
✓ Fast processing"""

    WORD_REPLACEMENT_TXT = """<b>🔄 WORD REPLACEMENT SYSTEM</b>

**Remove Words:**
<code>/remove word1,word2,word3</code>
Example: <code>/remove [Hindi],WEB-DL,x264</code>

**Replace Words:**
<code>/replace old:new,old2:new2</code>
Example: <code>/replace S01:Season 1,EP:Episode</code>

**Clear All:**
<code>/clearwords</code>

**How It Works:**
├ Checks file caption first
├ Falls back to filename
├ Applies removals first
└ Then applies replacements

**Current Settings:**
├ Remove: `{remove}`
└ Replace: `{replace}`"""

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

    SEND_METADATA = """<b>📋 Enter Custom Metadata</b>

Send the metadata text you want to add to files.

**Example:**
<code>Telegram: @pp_bots</code>

This will be embedded in video metadata."""

    JAI_BAJARANGABALI_CAPTION = """**Jai Bajarangabali Episode {episode}**

📺 Quality: {quality}
💾 Size: {filesize}
⏱ Duration: {duration}

@pp_bots"""
