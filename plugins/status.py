from pyrogram import Client, filters
from config import Config
from helper.database import AshutoshGoswami24
from datetime import datetime
import time


@Client.on_message(filters.private & filters.command("status"))
async def status_command(client, message):
    """Show bot status and user settings"""
    user_id = message.from_user.id
    
    # Get user settings
    format_template = await AshutoshGoswami24.get_format_template(user_id)
    media_preference = await AshutoshGoswami24.get_media_preference(user_id)
    upload_channel = await AshutoshGoswami24.get_upload_channel(user_id)
    caption = await AshutoshGoswami24.get_caption(user_id)
    thumbnail = await AshutoshGoswami24.get_thumbnail(user_id)
    metadata_enabled = await AshutoshGoswami24.get_metadata(user_id)
    
    # Bot uptime
    uptime = time.time() - Config.BOT_UPTIME
    uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
    
    # Premium status
    if Config.STRING_SESSION:
        upload_limit = "4 GB (Premium)"
        premium_status = "✅ Active"
    else:
        upload_limit = "2 GB (Standard)"
        premium_status = "❌ Not Active"
    
    # Channel status
    if upload_channel:
        try:
            channel = await client.get_chat(upload_channel)
            channel_status = f"✅ {channel.title}"
        except:
            channel_status = f"⚠️ Invalid ({upload_channel})"
    else:
        channel_status = "❌ Not Set"
    
    status_text = f"""
**🤖 Bot Status & Your Settings**

**📊 Bot Information:**
├ ⏱️ Uptime: `{uptime_str}`
├ 💎 Premium Session: {premium_status}
└ 📤 Upload Limit: `{upload_limit}`

**⚙️ Your Settings:**
├ 📝 Auto Rename Format: `{format_template or 'Not Set'}`
├ 🎬 Media Preference: `{media_preference or 'Default'}`
├ 📢 Upload Channel: {channel_status}
├ 🖼️ Custom Thumbnail: {'✅ Set' if thumbnail else '❌ Not Set'}
├ ✏️ Custom Caption: {'✅ Set' if caption else '❌ Not Set'}
└ 📋 Metadata: {'✅ Enabled' if metadata_enabled else '❌ Disabled'}

**💡 Quick Commands:**
• /autorename - Set rename format
• /setchannel - Setup channel upload
• /setmedia - Set media type
• /help - Show all commands
"""
    
    await message.reply_text(status_text)


@Client.on_message(filters.private & filters.command("mysettings"))
async def my_settings(client, message):
    """Show only user settings"""
    user_id = message.from_user.id
    
    format_template = await AshutoshGoswami24.get_format_template(user_id)
    media_preference = await AshutoshGoswami24.get_media_preference(user_id)
    upload_channel = await AshutoshGoswami24.get_upload_channel(user_id)
    
    if upload_channel:
        try:
            channel = await client.get_chat(upload_channel)
            channel_info = f"✅ {channel.title} (`{upload_channel}`)"
        except:
            channel_info = f"⚠️ Invalid Channel ID: `{upload_channel}`"
    else:
        channel_info = "❌ Not configured"
    
    settings_text = f"""
**⚙️ Your Current Settings**

**📝 Auto Rename Format:**
`{format_template or 'Not Set - Use /autorename to set'}`

**🎬 Media Type Preference:**
`{media_preference or 'Default (Based on file type)'}`

**📢 Channel Upload:**
{channel_info}

**🔧 Configure:**
• /autorename <format> - Set format
• /setmedia <type> - Set media type
• /setchannel <id> - Set channel
• /delchannel - Remove channel
"""
    
    await message.reply_text(settings_text)
