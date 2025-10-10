from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from helper.database import pp_bots
from config import Config, Txt


@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user = message.from_user
    await pp_bots.add_user(client, message)
    
    button = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/pp_bots"),
            InlineKeyboardButton("💬 Support", url="https://t.me/pp_bots"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="open_settings"),
            InlineKeyboardButton("📚 Help", callback_data="help"),
        ],
        [
            InlineKeyboardButton("💙 About", callback_data="about"),
            InlineKeyboardButton("🎬 Features", callback_data="features"),
        ],
    ])
    
    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=button,
        )
    else:
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=button,
            disable_web_page_preview=True,
        )


@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📢 Updates", url="https://t.me/pp_bots"),
                    InlineKeyboardButton("💬 Support", url="https://t.me/pp_bots"),
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="open_settings"),
                    InlineKeyboardButton("📚 Help", callback_data="help"),
                ],
                [
                    InlineKeyboardButton("💙 About", callback_data="about"),
                    InlineKeyboardButton("🎬 Features", callback_data="features"),
                ],
            ])
        )
    
    elif data == "open_settings":
        # Redirect to settings command
        from plugins.settings import settings_command
        # Show settings panel
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
        channel_text = f"Set" if upload_channel else "Not Set"
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
                InlineKeyboardButton("🔙 Back", callback_data="home"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
        
        await query.message.edit_text(settings_text, reply_markup=keyboard)
    
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="help"),
                ]
            ])
        )
    
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")],
                [InlineKeyboardButton("🎬 Features", callback_data="features")],
                [
                    InlineKeyboardButton("🏠 Home", callback_data="home"),
                    InlineKeyboardButton("❌ Close", callback_data="close")
                ],
            ])
        )
    
    elif data == "features":
        features_text = """**🎬 BOT FEATURES**

**📝 Rename & Organize:**
├ Template-based renaming
├ Word removal system
├ Word replacement system
├ Episode & quality detection
└ Custom filename formats

**🎞️ Video Processing:**
├ Multi-quality compression
├ Video trimming (manual)
├ Auto-trim with detection
├ Merge multiple videos
└ Extract audio/subtitles

**📤 Upload Options:**
├ Channel auto-upload
├ Custom thumbnails
├ Custom captions
├ Metadata embedding
└ 4GB file support (Premium)

**🎯 Special Features:**
├ "Jai Bajarangabali" auto-handler
├ Batch processing
├ Multiple media modes
├ Real-time progress tracking
└ Smart file detection

**💡 Use /help for detailed guide**"""
        
        await query.message.edit_text(
            text=features_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Full Guide", callback_data="help")],
                [
                    InlineKeyboardButton("🏠 Home", callback_data="home"),
                    InlineKeyboardButton("❌ Close", callback_data="close")
                ]
            ])
        )
    
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="help"),
                ]
            ])
        )

    elif data == "file_names":
        format_template = await pp_bots.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template or "Not Set"),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="help"),
                ]
            ])
        )

    elif data == "thumbnail":
        await query.message.edit_text(
            text=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="help"),
                ]
            ])
        )

    elif data == "channel":
        channel_id = await pp_bots.get_upload_channel(user_id)
        channel_status = "✅ Enabled" if channel_id else "❌ Not Set"
        
        await query.message.edit_text(
            text=Txt.CHANNEL_TXT + f"\n\n**Status:** {channel_status}",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="help"),
                ]
            ])
        )

    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✖️ Close", callback_data="close"),
                    InlineKeyboardButton("🔙 Back", callback_data="home"),
                ]
            ])
        )

    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
        except:
            await query.message.delete()
