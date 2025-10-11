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
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            return await message.reply_text(
                "**📝 Remove Words**\n\n"
                "**Usage:**\n"
                "<code>/remove [Hindi],WEB-DL,x264</code>\n\n"
                "Separate multiple words with commas.",
                quote=True
            )
        
        words_text = command_parts[1].strip()
        
        # Split by comma and clean
        words = [word.strip() for word in words_text.split(',') if word.strip()]
        
        if not words:
            return await message.reply_text("**❌ No valid words provided!**", quote=True)
        
        # Get existing words
        existing = await pp_bots.get_remove_words(user_id)
        
        # Add new words (avoid duplicates)
        new_added = []
        for word in words:
            if word not in existing:
                existing.append(word)
                new_added.append(word)
        
        # Save to database
        await pp_bots.set_remove_words(user_id, existing)
        
        if new_added:
            words_list = "\n".join([f"• `{word}`" for word in new_added])
            await message.reply_text(
                f"**✅ Words Added to Removal List!**\n\n"
                f"**New Words:**\n{words_list}\n\n"
                f"**Total Words:** {len(existing)}\n\n"
                f"Use /viewwords to see all\n"
                f"Use /clearwords to clear all",
                quote=True
            )
        else:
            await message.reply_text(
                "**⚠️ All words already exist in removal list!**\n\n"
                "Use /viewwords to see current list",
                quote=True
            )
        
    except Exception as e:
        await message.reply_text(
            f"**❌ Error:** `{e}`\n\n"
            "**Example:**\n"
            "<code>/remove [Hindi],WEB-DL,x264</code>",
            quote=True
        )


@Client.on_message(filters.private & filters.command("replace"))
async def replace_words_command(client, message):
    """Add word replacements"""
    user_id = message.from_user.id
    
    try:
        # Extract replacement text
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            return await message.reply_text(
                "**🔄 Replace Words**\n\n"
                "**Usage:**\n"
                "<code>/replace S01:Season 1,EP:Episode</code>\n\n"
                "Format: <code>old:new,old2:new2</code>",
                quote=True
            )
        
        replace_text = command_parts[1].strip()
        
        # Parse replacements
        pairs = [pair.strip() for pair in replace_text.split(',') if pair.strip()]
        
        if not pairs:
            return await message.reply_text("**❌ No valid replacement pairs provided!**", quote=True)
        
        # Get existing replacements
        existing = await pp_bots.get_replace_words(user_id)
        
        # Parse and add new replacements
        added = []
        invalid = []
        for pair in pairs:
            if ':' in pair:
                parts = pair.split(':', 1)
                if len(parts) == 2:
                    old = parts[0].strip()
                    new = parts[1].strip()
                    if old:  # Allow empty 'new' value for deletion
                        existing[old] = new
                        added.append(f"`{old}` → `{new}`")
                    else:
                        invalid.append(pair)
                else:
                    invalid.append(pair)
            else:
                invalid.append(pair)
        
        if not added and not invalid:
            return await message.reply_text(
                "**❌ No valid replacement pairs!**\n\n"
                "Use format: <code>old:new,old2:new2</code>",
                quote=True
            )
        
        # Save to database
        await pp_bots.set_replace_words(user_id, existing)
        
        response = "**✅ Replacements Updated!**\n\n"
        
        if added:
            replacements_list = "\n".join([f"• {item}" for item in added])
            response += f"**New Replacements:**\n{replacements_list}\n\n"
        
        if invalid:
            invalid_list = "\n".join([f"• `{item}`" for item in invalid])
            response += f"**⚠️ Invalid Format:**\n{invalid_list}\n\n"
        
        response += f"**Total Replacements:** {len(existing)}\n\n"
        response += "Use /viewwords to see all"
        
        await message.reply_text(response, quote=True)
        
    except Exception as e:
        await message.reply_text(
            f"**❌ Error:** `{e}`\n\n"
            "**Example:**\n"
            "<code>/replace S01:Season 1,EP:Episode</code>",
            quote=True
        )


@Client.on_message(filters.private & filters.command("prefix"))
async def set_prefix_command(client, message):
    """Set prefix to add at start of filename"""
    user_id = message.from_user.id
    
    try:
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            current_prefix = await pp_bots.get_prefix(user_id)
            return await message.reply_text(
                "**📌 Set Prefix**\n\n"
                "**Usage:**\n"
                "<code>/prefix @MyChannel -</code>\n\n"
                f"**Current Prefix:** `{current_prefix or 'None'}`\n\n"
                "Use <code>/prefix none</code> to remove",
                quote=True
            )
        
        prefix = command_parts[1].strip()
        
        if prefix.lower() == "none":
            await pp_bots.set_prefix(user_id, None)
            await message.reply_text("**✅ Prefix Removed!**", quote=True)
        else:
            await pp_bots.set_prefix(user_id, prefix)
            await message.reply_text(
                f"**✅ Prefix Set!**\n\n"
                f"**Prefix:** `{prefix}`\n\n"
                f"**Example:**\n"
                f"`{prefix} Movie Name.mkv`",
                quote=True
            )
        
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{e}`", quote=True)


@Client.on_message(filters.private & filters.command("suffix"))
async def set_suffix_command(client, message):
    """Set suffix to add at end of filename (before extension)"""
    user_id = message.from_user.id
    
    try:
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            current_suffix = await pp_bots.get_suffix(user_id)
            return await message.reply_text(
                "**📌 Set Suffix**\n\n"
                "**Usage:**\n"
                "<code>/suffix @MyChannel</code>\n\n"
                f"**Current Suffix:** `{current_suffix or 'None'}`\n\n"
                "Use <code>/suffix none</code> to remove",
                quote=True
            )
        
        suffix = command_parts[1].strip()
        
        if suffix.lower() == "none":
            await pp_bots.set_suffix(user_id, None)
            await message.reply_text("**✅ Suffix Removed!**", quote=True)
        else:
            await pp_bots.set_suffix(user_id, suffix)
            await message.reply_text(
                f"**✅ Suffix Set!**\n\n"
                f"**Suffix:** `{suffix}`\n\n"
                f"**Example:**\n"
                f"`Movie Name {suffix}.mkv`",
                quote=True
            )
        
    except Exception as e:
        await message.reply_text(f"**❌ Error:** `{e}`", quote=True)


@Client.on_message(filters.private & filters.command("clearwords"))
async def clear_words_command(client, message):
    """Clear all word removals and replacements"""
    user_id = message.from_user.id
    
    await pp_bots.set_remove_words(user_id, [])
    await pp_bots.set_replace_words(user_id, {})
    
    await message.reply_text(
        "**✅ All Word Removals & Replacements Cleared!**\n\n"
        "Use /remove and /replace to add new ones.",
        quote=True
    )


@Client.on_message(filters.private & filters.command("viewwords"))
async def view_words_command(client, message):
    """View current word removals and replacements"""
    user_id = message.from_user.id
    
    remove_words = await pp_bots.get_remove_words(user_id)
    replace_words = await pp_bots.get_replace_words(user_id)
    prefix = await pp_bots.get_prefix(user_id)
    suffix = await pp_bots.get_suffix(user_id)
    
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
    
    text = (
        "**🔄 WORD REPLACEMENT SETTINGS**\n\n"
        f"**📌 Prefix:** `{prefix or 'None'}`\n"
        f"**📌 Suffix:** `{suffix or 'None'}`\n\n"
        f"**🗑️ Remove Words:**\n{remove_list}\n\n"
        f"**🔄 Replace Words:**\n{replace_list}\n\n"
        "**How It Works:**\n"
        "├ Apply prefix\n"
        "├ Remove words\n"
        "├ Replace words\n"
        "├ Clean underscores/dots\n"
        "└ Apply suffix"
    )
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Clear All", callback_data="clear_all_words"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ]),
        quote=True
    )


@Client.on_callback_query(filters.regex("clear_all_words"))
async def clear_words_callback(client, query):
    """Clear all words via callback"""
    user_id = query.from_user.id
    
    await pp_bots.set_remove_words(user_id, [])
    await pp_bots.set_replace_words(user_id, {})
    await pp_bots.set_prefix(user_id, None)
    await pp_bots.set_suffix(user_id, None)
    
    await query.answer("✅ All settings cleared!", show_alert=True)
    await query.message.edit_text(
        "**✅ All Settings Cleared!**\n\n"
        "• Prefix removed\n"
        "• Suffix removed\n"
        "• Remove words cleared\n"
        "• Replace words cleared\n\n"
        "Use commands to set new values:\n"
        "├ /prefix\n"
        "├ /suffix\n"
        "├ /remove\n"
        "└ /replace"
    )
