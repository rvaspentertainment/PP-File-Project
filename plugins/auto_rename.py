from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helper.database import pp_bots
from config import Txt


@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    """Set auto rename format template"""
    user_id = message.from_user.id

    try:
        # Extract the format from the command
        format_template = message.text.split("/autorename", 1)[1].strip()
        
        # Check if user wants to clear format
        if format_template.lower() == "none":
            await pp_bots.set_format_template(user_id, None)
            return await message.reply_text(
                "**✅ Auto Rename Format Cleared!**\n\n"
                "Now the bot will use word removal and replacement system.\n\n"
                "**Next Steps:**\n"
                "• Use /remove to remove unwanted words\n"
                "• Use /replace to replace words\n"
                "• Use /viewwords to see your settings",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
                ])
            )
        
        # Save the format template to the database
        await pp_bots.set_format_template(user_id, format_template)

        await message.reply_text(
            f"**✅ Auto Rename Format Updated!**\n\n"
            f"**Your Format:** `{format_template}`\n\n"
            f"**Available Keywords:**\n"
            f"• `[episode]` - Episode number\n"
            f"• `[quality]` - Video quality\n\n"
            f"**Example Output:**\n"
            f"`{format_template.replace('[episode]', 'EP05').replace('[quality]', '720p')}`\n\n"
            f"💡 Send any file to test the format!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗑️ Clear Format", callback_data="clear_format"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
                ]
            ])
        )
        
    except IndexError:
        # Show help if no format provided
        current_format = await pp_bots.get_format_template(user_id)
        
        await message.reply_text(
            Txt.FILE_NAME_TXT.format(format_template=current_format or "Not Set"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
            ])
        )


@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    """Set media type preference"""
    user_id = message.from_user.id
    
    try:
        media_type = message.text.split("/setmedia", 1)[1].strip().lower()
        
        if media_type not in ['document', 'video', 'audio']:
            return await message.reply_text(
                "**❌ Invalid media type!**\n\n"
                "**Available types:**\n"
                "• `document`\n"
                "• `video`\n"
                "• `audio`\n\n"
                "**Example:** `/setmedia video`",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📄 Document", callback_data="media_pref_document"),
                        InlineKeyboardButton("🎬 Video", callback_data="media_pref_video")
                    ],
                    [
                        InlineKeyboardButton("🎵 Audio", callback_data="media_pref_audio"),
                        InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
                    ]
                ])
            )

        # Save the preferred media type to the database
        await pp_bots.set_media_preference(user_id, media_type)

        media_icons = {
            'document': '📄',
            'video': '🎬',
            'audio': '🎵'
        }
        
        await message.reply_text(
            f"**✅ Media Preference Updated!**\n\n"
            f"**Selected Type:** {media_icons[media_type]} {media_type.capitalize()}\n\n"
            f"All files will now be uploaded as {media_type}.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
            ])
        )
        
    except IndexError:
        # Show options if no type provided
        current_type = await pp_bots.get_media_preference(user_id)
        
        await message.reply_text(
            f"**🎬 Media Type Preference**\n\n"
            f"**Current:** {current_type or 'Default (Auto-detect)'}\n\n"
            f"**Usage:** `/setmedia <type>`\n\n"
            f"**Available Types:**\n"
            f"• `document` - Upload as document\n"
            f"• `video` - Upload as video\n"
            f"• `audio` - Upload as audio\n\n"
            f"Click buttons below to set:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📄 Document", callback_data="media_pref_document"),
                    InlineKeyboardButton("🎬 Video", callback_data="media_pref_video")
                ],
                [
                    InlineKeyboardButton("🎵 Audio", callback_data="media_pref_audio"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
                ]
            ])
        )


# Callback handlers for media preference
@Client.on_callback_query(filters.regex("^media_pref_"))
async def media_pref_callback(client, query):
    """Handle media preference selection via callback"""
    user_id = query.from_user.id
    media_type = query.data.split("_")[-1]
    
    await pp_bots.set_media_preference(user_id, media_type)
    
    media_icons = {
        'document': '📄',
        'video': '🎬',
        'audio': '🎵'
    }
    
    await query.answer(f"✅ Set to {media_type.capitalize()}", show_alert=True)
    
    await query.message.edit_text(
        f"**✅ Media Preference Updated!**\n\n"
        f"**Selected Type:** {media_icons[media_type]} {media_type.capitalize()}\n\n"
        f"All files will now be uploaded as {media_type}.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
        ])
    )


@Client.on_message(filters.private & filters.command("media"))
async def media_mode_command(client, message):
    """Set media processing mode"""
    user_id = message.from_user.id
    
    try:
        mode = message.text.split("/media", 1)[1].strip().lower()
        
        valid_modes = ['rename', 'trim', 'extract', 'merge', 'compress', 'autotrim']
        
        if mode not in valid_modes:
            return await message.reply_text(
                "**❌ Invalid mode!**\n\n"
                "**Available modes:**\n"
                "• `rename` - Rename files\n"
                "• `trim` - Trim videos\n"
                "• `extract` - Extract audio/subtitles\n"
                "• `merge` - Merge files\n"
                "• `compress` - Compress videos\n"
                "• `autotrim` - Auto trim\n\n"
                "**Example:** `/media trim`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
                ])
            )
        
        await pp_bots.set_media_mode(user_id, mode)
        
        mode_descriptions = {
            'rename': '📝 **Rename Mode**\n\nRename files using templates or word replacement.',
            'trim': '✂️ **Trim Mode**\n\nTrim videos to specific start/end times.',
            'extract': '🎵 **Extract Mode**\n\nExtract audio or subtitles from videos.',
            'merge': '🔗 **Merge Mode**\n\nMerge multiple videos, audios or subtitles.',
            'compress': '🎞️ **Compress Mode**\n\nCompress videos to multiple qualities.',
            'autotrim': '🤖 **Auto Trim Mode**\n\nAutomatically detect and trim videos.'
        }
        
        await message.reply_text(
            f"**✅ Media Mode Changed!**\n\n"
            f"{mode_descriptions[mode]}\n\n"
            f"Send a file to process in this mode.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Open Settings", callback_data="open_settings")]
            ])
        )
        
    except IndexError:
        # Show current mode and options
        current_mode = await pp_bots.get_media_mode(user_id)
        
        await message.reply_text(
            f"**🎬 Media Processing Mode**\n\n"
            f"**Current Mode:** {current_mode.capitalize()}\n\n"
            f"**Available Modes:**\n"
            f"• `/media rename` - Rename files\n"
            f"• `/media trim` - Trim videos\n"
            f"• `/media extract` - Extract audio/subs\n"
            f"• `/media merge` - Merge files\n"
            f"• `/media compress` - Compress videos\n"
            f"• `/media autotrim` - Auto trim\n\n"
            f"Or use buttons in settings panel:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Open Settings", callback_data="set_media_mode")]
            ])
        )
