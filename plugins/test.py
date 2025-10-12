from pyrogram import Client, filters
import logging

@Client.on_message(filters.command("test") & filters.private)
async def test_handler(client, message):
    """Simple test handler to verify bot is responding"""
    logging.info(f"Test command received from {message.from_user.id}")
    await message.reply_text(
        "✅ **Bot is working!**\n\n"
        "All handlers are loaded correctly.\n"
        "You can now use the bot normally."
    )

logging.info("Test handler loaded")
