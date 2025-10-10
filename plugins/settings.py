from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.database import pp_bots
from config import Config, Txt


@Client.on_message(filters.private & filters.command("settings"))
async def settings_command(client, message):
    """Show settings panel"""
    user_id = message.from_user.id
    
    # Get all user settings
    format_template = await pp_bots.get_format_template(user_id)
    media_mode = await pp_bots.get_media_mode(user_id)
    upload_channel = await pp_bots.get_upload_channel(user_id)
    thumbnail = await pp_bots.get_thumbnail(user_id)
    caption = await pp_bots.get_caption(user_id)
    metadata_enabled = await pp_bots.get_metadata(user_id)
    remove_words = await pp_bots.get_remove_words(user_id)
    replace_words = await pp_bots.get_replace_words(user_id)
    
    # Format settings text
    format_text = format_template if format_template else "Not Set"
    mode_text = media_mode.capitalize()
    channel_text = f"Set (ID: {upload_channel})" if upload_channel else "Not Set"
    thumb_text = "✅ Set" if thumbnail else "❌ Not Set"
    caption_text = "✅ Set" if caption else "❌ Not Set"
    metadata_text = "✅ Enabled" if metadata_enabled else "❌ Disabled"
    premium_text = "✅ Active (4GB)" if Config.STRING_SESSION else "❌ Not Active (2GB)"
    remove_text = f"{len(remove_words)} words" if remove_words else "None"
    replace_text = f"{len(replace_words)} pairs" if replace_words else "None"
    
    settings_text = Txt.SETTINGS_TXT.format(
        format=format_text,
        mode=mode_text,
        channel=channel_text,
        thumb=thumb_text,
        caption=caption_text,
        metadata=metadata_text,
        premium=premium_text,
        remove_words=remove_text,
        replace_words=replace_text
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Rename Format", callback_data="set_format"),
            InlineKeyboardButton("🎬 Media Mode", callback_data="set_media_mode")
        ],
        [
            InlineKeyboardButton("📢 Channel", callback_data="set_channel"),
            InlineKeyboardButton("🖼️ Thumbnail", callback_data="set_thumb")
        ],
        [
            InlineKeyboardButton("✏️ Caption", callback_data="set_caption"),
            InlineKeyboardButton("📋 Metadata", callback_data="set_metadata")
        ],
        [
            InlineKeyboardButton("🔄 Word Replace", callback_data="word_replace_menu"),
            InlineKeyboardButton("🗑️ Remove Words", callback_data="remove_words_menu")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_settings"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])
    
    await message.reply_text(settings_text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex("refresh_settings"))
async def refresh_settings_callback(client, query: CallbackQuery):
    """Refresh settings display"""
    user_id = query.from_user.id
    
    # Get all user settings
    format_template = await pp_bots.get_format_template(user_id)
    media_mode = await pp_bots.get_media_mode(user_id)
    upload_channel = await pp_bots.get_upload_channel(user_id)
    thumbnail = await pp_bots.get_thumbnail(user_id)
    caption = await pp_bots.get_caption(user_id)
    metadata_enabled = await pp_bots.get_metadata(user_id)
    remove_words = await pp_bots.get_remove_words(user_id)
    replace_words = await pp_bots.get_replace_words(user_id)
    
    format_text = format_template if format_template else "Not Set"
    mode_text = media_mode.capitalize()
    channel_text = f"Set (ID: {upload_channel})" if upload_channel else "Not Set"
    thumb_text = "✅ Set" if thumbnail else "❌ Not Set"
    caption_text = "✅ Set" if caption else "❌ Not Set"
    metadata_text = "✅ Enabled" if metadata_enabled else "❌ Disabled"
    premium_text = "✅ Active (4GB)" if Config.STRING_SESSION else "❌ Not Active (2GB)"
    remove_text = f"{len(remove_words)} words" if remove_words else "None"
    replace_text = f"{len(replace_words)} pairs" if replace_words else "None"
    
    settings_text = Txt.SETTINGS_TXT.format(
        format=format_text,
        mode=mode_text,
        channel=channel_text,
        thumb=thumb_text,
        caption=caption_text,
        metadata=metadata_text,
        premium=premium_text,
        remove_words=remove_text,
        replace_words=replace_text
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Rename Format", callback_data="set_format"),
            InlineKeyboardButton("🎬 Media Mode", callback_data="set_media_mode")
        ],
        [
            InlineKeyboardButton("📢 Channel", callback_data="set_channel"),
            InlineKeyboardButton("🖼️ Thumbnail", callback_data="set_thumb")
        ],
        [
            InlineKeyboardButton("✏️ Caption", callback_data="set_caption"),
            InlineKeyboardButton("📋 Metadata", callback_data="set_metadata")
        ],
        [
            InlineKeyboardButton("🔄 Word Replace", callback_data="word_replace_menu"),
            InlineKeyboardButton("🗑️ Remove Words", callback_data="remove_words_menu")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_settings"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])
    
    await query.message.edit_text(settings_text, reply_markup=keyboard)
    await query.answer("✅ Settings refreshed!")


@Client.on_callback_query(filters.regex("set_media_mode"))
async def media_mode_callback(client, query: CallbackQuery):
    """Show media mode selection"""
    user_id = query.from_user.id
    current_mode = await pp_bots.get_media_mode(user_id)
    
    text = Txt.MEDIA_MODE_TXT.format(current_mode=current_mode.capitalize())
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Rename", callback_data="mode_rename"),
            InlineKeyboardButton("✂️ Trim", callback_data="mode_trim")
        ],
        [
            InlineKeyboardButton("🎵 Extract", callback_data="mode_extract"),
            InlineKeyboardButton("🔗 Merge", callback_data="mode_merge")
        ],
        [
            InlineKeyboardButton("🎞️ Compress", callback_data="mode_compress"),
            InlineKeyboardButton("🤖 Auto Trim", callback_data="mode_autotrim")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex("mode_"))
async def set_mode_callback(client, query: CallbackQuery):
    """Set media mode"""
    user_id = query.from_user.id
    mode = query.data.split("_")[1]
    
    await pp_bots.set_media_mode(user_id, mode)
    
    mode_names = {
        'rename': '📝 Rename Mode',
        'trim': '✂️ Trim Mode',
        'extract': '🎵 Extract Mode',
        'merge': '🔗 Merge Mode',
        'compress': '🎞️ Compress Mode',
        'autotrim': '🤖 Auto Trim Mode'
    }
    
    await query.answer(f"✅ {mode_names[mode]} activated!", show_alert=True)
    
    # Show mode-specific instructions
    instructions = {
        'rename': "**Rename Mode Active**\n\nSend any file to rename it based on your format template or word replacements.",
        'trim': Txt.TRIM_TXT,
        'extract': Txt.EXTRACT_TXT,
        'merge': Txt.MERGE_TXT,
        'compress': Txt.COMPRESS_TXT,
        'autotrim': Txt.TRIM_TXT
    }
    
    await query.message.edit_text(
        instructions.get(mode, f"**{mode_names[mode]} Active!**"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("set_format"))
async def format_info_callback(client, query: CallbackQuery):
    """Show format setup info"""
    user_id = query.from_user.id
    format_template = await pp_bots.get_format_template(user_id)
    
    text = Txt.FILE_NAME_TXT.format(format_template=format_template or "Not Set")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Clear Format", callback_data="clear_format")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])
    
    await query.message.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex("clear_format"))
async def clear_format_callback(client, query: CallbackQuery):
    """Clear format template"""
    user_id = query.from_user.id
    await pp_bots.set_format_template(user_id, None)
    await query.answer("✅ Format cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ Format Template Cleared!**\n\n"
        "Now word removal/replacement will be used.\n\n"
        "Use /autorename to set new format.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("set_channel"))
async def channel_info_callback(client, query: CallbackQuery):
    """Show channel setup info"""
    await query.message.edit_text(
        Txt.CHANNEL_TXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
    )


@Client.on_callback_query(filters.regex("set_thumb"))
async def thumb_info_callback(client, query: CallbackQuery):
    """Show thumbnail setup info"""
    await query.message.edit_text(
        Txt.THUMBNAIL_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="delete_thumb")],
            [
                InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
    )


@Client.on_callback_query(filters.regex("delete_thumb"))
async def delete_thumb_callback(client, query: CallbackQuery):
    """Delete thumbnail"""
    user_id = query.from_user.id
    await pp_bots.set_thumbnail(user_id, None)
    await query.answer("✅ Thumbnail deleted!", show_alert=True)
    await query.message.edit_text(
        "**✅ Thumbnail Deleted Successfully!**\n\n"
        "Send a new photo to set thumbnail.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("set_caption"))
async def caption_info_callback(client, query: CallbackQuery):
    """Show caption setup info"""
    await query.message.edit_text(
        Txt.CAPTION_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Caption", callback_data="delete_caption")],
            [
                InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
    )


@Client.on_callback_query(filters.regex("delete_caption"))
async def delete_caption_callback(client, query: CallbackQuery):
    """Delete caption"""
    user_id = query.from_user.id
    await pp_bots.set_caption(user_id, None)
    await query.answer("✅ Caption deleted!", show_alert=True)
    await query.message.edit_text(
        "**✅ Caption Deleted Successfully!**\n\n"
        "Use /set_caption to set new caption.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("set_metadata"))
async def metadata_toggle_callback(client, query: CallbackQuery):
    """Toggle metadata"""
    user_id = query.from_user.id
    current = await pp_bots.get_metadata(user_id)
    
    # Toggle
    new_state = not current
    await pp_bots.set_metadata(user_id, new_state)
    
    status = "Enabled ✅" if new_state else "Disabled ❌"
    await query.answer(f"Metadata {status}", show_alert=True)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Metadata: {status}", callback_data="set_metadata")],
        [InlineKeyboardButton("✏️ Edit Metadata Text", callback_data="edit_metadata_text")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ]
    ])
    
    metadata_code = await pp_bots.get_metadata_code(user_id)
    
    await query.message.edit_text(
        f"**📋 Metadata Settings**\n\n"
        f"**Status:** {status}\n"
        f"**Current Text:** `{metadata_code}`\n\n"
        f"Click button to toggle or edit text.",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex("word_replace_menu"))
async def word_replace_menu_callback(client, query: CallbackQuery):
    """Show word replacement menu"""
    user_id = query.from_user.id
    replace_words = await pp_bots.get_replace_words(user_id)
    
    if replace_words:
        replace_list = "\n".join([f"• `{old}` → `{new}`" for old, new in replace_words.items()])
    else:
        replace_list = "None"
    
    await query.message.edit_text(
        f"**🔄 Word Replacement**\n\n"
        f"**Current Replacements:**\n{replace_list}\n\n"
        f"Use: <code>/replace old:new,old2:new2</code>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Clear All", callback_data="clear_replace_words")],
            [
                InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
    )


@Client.on_callback_query(filters.regex("clear_replace_words"))
async def clear_replace_callback(client, query: CallbackQuery):
    """Clear replacement words"""
    user_id = query.from_user.id
    await pp_bots.set_replace_words(user_id, {})
    await query.answer("✅ Replacements cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ All Replacements Cleared!**\n\n"
        "Use /replace to add new ones.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )


@Client.on_callback_query(filters.regex("remove_words_menu"))
async def remove_words_menu_callback(client, query: CallbackQuery):
    """Show word removal menu"""
    user_id = query.from_user.id
    remove_words = await pp_bots.get_remove_words(user_id)
    
    if remove_words:
        remove_list = "\n".join([f"• `{word}`" for word in remove_words])
    else:
        remove_list = "None"
    
    await query.message.edit_text(
        f"**🗑️ Word Removal**\n\n"
        f"**Words to Remove:**\n{remove_list}\n\n"
        f"Use: <code>/remove word1,word2,word3</code>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Clear All", callback_data="clear_remove_words")],
            [
                InlineKeyboardButton("🔙 Back", callback_data="refresh_settings"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
    )


@Client.on_callback_query(filters.regex("clear_remove_words"))
async def clear_remove_callback(client, query: CallbackQuery):
    """Clear removal words"""
    user_id = query.from_user.id
    await pp_bots.set_remove_words(user_id, [])
    await query.answer("✅ Remove words cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ All Remove Words Cleared!**\n\n"
        "Use /remove to add new ones.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="refresh_settings")]
        ])
    )
