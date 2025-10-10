from pyrogram import Client, filters
from helper.database import pp_bots
from config import Txt
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@Client.on_message(filters.private & filters.command("remove"))
async def remove_words_command(client, message):
    """Add words to removal list"""
    user_id = message.from_user.id
    
    try:
        # Extract words from command
        words_text = message.text.split("/remove", 1)[1].strip()
        
        if not words_text:
            return await message.reply_text(
                "**Please provide words to remove!**\n\n"
                "**Example:**\n"
                "<code>/remove [Hindi],WEB-DL,x264</code>\n\n"
                "Separate multiple words with commas."
            )
        
        # Split by comma and clean
        words = [word.strip() for word in words_text.split(',') if word.strip()]
        
        if not words:
            return await message.reply_text("**No valid words provided!**")
        
        # Get existing words
        existing = await pp_bots.get_remove_words(user_id)
        
        # Add new words (avoid duplicates)
        for word in words:
            if word not in existing:
                existing.append(word)
        
        # Save to database
        await pp_bots.set_remove_words(user_id, existing)
        
        words_list = "\n".join([f"• `{word}`" for word in existing])
        
        await message.reply_text(
            f"**✅ Words Added to Removal List!**\n\n"
            f"**Words to Remove:**\n{words_list}\n\n"
            f"Use /clearwords to clear all"
        )
        
    except IndexError:
        await message.reply_text(
            "**Please provide words to remove!**\n\n"
            "**Example:**\n"
            "<code>/remove [Hindi],WEB-DL,x264</code>"
        )


@Client.on_message(filters.private & filters.command("replace"))
async def replace_words_command(client, message):
    """Add word replacements"""
    user_id = message.from_user.id
    
    try:
        # Extract replacement text
        replace_text = message.text.split("/replace", 1)[1].strip()
        
        if not replace_text:
            return await message.reply_text(
                "**Please provide replacement pairs!**\n\n"
                "**Example:**\n"
                "<code>/replace S01:Season 1,EP:Episode,x264:H264</code>\n\n"
                "Format: <code>old:new,old2:new2</code>"
            )
        
        # Parse replacements
        pairs = [pair.strip() for pair in replace_text.split(',') if pair.strip()]
        
        if not pairs:
            return await message.reply_text("**No valid replacement pairs provided!**")
        
        # Get existing replacements
        existing = await pp_bots.get_replace_words(user_id)
        
        # Parse and add new replacements
        added = []
        for pair in pairs:
            if ':' in pair:
                old, new = pair.split(':', 1)
                old = old.strip()
                new = new.strip()
                if old and new:
                    existing[old] = new
                    added.append(f"`{old}` → `{new}`")
        
        if not added:
            return await message.reply_text(
                "**No valid replacement pairs!**\n\n"
                "Use format: <code>old:new,old2:new2</code>"
            )
        
        # Save to database
        await pp_bots.set_replace_words(user_id, existing)
        
        replacements_list = "\n".join([f"• {item}" for item in added])
        
        await message.reply_text(
            f"**✅ Replacements Added!**\n\n"
            f"**New Replacements:**\n{replacements_list}\n\n"
            f"Use /viewwords to see all replacements"
        )
        
    except IndexError:
        await message.reply_text(
            "**Please provide replacement pairs!**\n\n"
            "**Example:**\n"
            "<code>/replace S01:Season 1,EP:Episode</code>"
        )


@Client.on_message(filters.private & filters.command("clearwords"))
async def clear_words_command(client, message):
    """Clear all word removals and replacements"""
    user_id = message.from_user.id
    
    await pp_bots.set_remove_words(user_id, [])
    await pp_bots.set_replace_words(user_id, {})
    
    await message.reply_text(
        "**✅ All Word Removals & Replacements Cleared!**\n\n"
        "Use /remove and /replace to add new ones."
    )


@Client.on_message(filters.private & filters.command("viewwords"))
async def view_words_command(client, message):
    """View current word removals and replacements"""
    user_id = message.from_user.id
    
    remove_words = await pp_bots.get_remove_words(user_id)
    replace_words = await pp_bots.get_replace_words(user_id)
    
    # Format removal list
    if remove_words:
        remove_list = "\n".join([f"• `{word}`" for word in remove_words])
    else:
        remove_list = "None"
    
    # Format replacement list
    if replace_words:
        replace_list = "\n".join([f"• `{old}` → `{new}`" for old, new in replace_words.items()])
    else:
        replace_list = "None"
    
    text = Txt.WORD_REPLACEMENT_TXT.format(
        remove=remove_list,
        replace=replace_list
    )
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Clear All", callback_data="clear_all_words")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    )


@Client.on_callback_query(filters.regex("clear_all_words"))
async def clear_words_callback(client, query):
    """Clear all words via callback"""
    user_id = query.from_user.id
    
    await pp_bots.set_remove_words(user_id, [])
    await pp_bots.set_replace_words(user_id, {})
    
    await query.answer("✅ All words cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ All Word Removals & Replacements Cleared!**\n\n"
        "Use /remove and /replace to add new ones."
    )
