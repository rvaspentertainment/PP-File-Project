from pyrogram import Client, filters
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, UserNotParticipant
from helper.database import AshutoshGoswami24


@Client.on_message(filters.private & filters.command("setchannel"))
async def set_channel(client, message):
    user_id = message.from_user.id
    
    try:
        # Extract channel ID from command
        channel_id = message.text.split("/setchannel", 1)[1].strip()
        
        if not channel_id:
            return await message.reply_text(
                "**Please provide a channel ID!**\n\n"
                "Example: `/setchannel -100123456789`"
            )
        
        # Convert to integer
        try:
            channel_id = int(channel_id)
        except ValueError:
            return await message.reply_text(
                "**Invalid channel ID!**\n\n"
                "Please provide a valid numeric channel ID.\n"
                "Example: `/setchannel -100123456789`"
            )
        
        # Check if bot is admin in the channel
        try:
            chat = await client.get_chat(channel_id)
            member = await client.get_chat_member(channel_id, client.me.id)
            
            if member.status not in ["administrator", "creator"]:
                return await message.reply_text(
                    "**I'm not an admin in this channel!**\n\n"
                    "Please make me an admin with permission to post messages."
                )
            
            # Save channel to database
            await AshutoshGoswami24.set_upload_channel(user_id, channel_id)
            
            await message.reply_text(
                f"**Channel Upload Set Successfully! ✅**\n\n"
                f"**Channel:** {chat.title}\n"
                f"**Channel ID:** `{channel_id}`\n\n"
                f"All renamed files will now be uploaded to this channel."
            )
            
        except ChannelInvalid:
            await message.reply_text(
                "**Invalid channel ID!**\n\n"
                "Please check the channel ID and try again."
            )
        except ChatAdminRequired:
            await message.reply_text(
                "**I don't have permission to access this channel!**\n\n"
                "Please make me an admin in the channel first."
            )
        except Exception as e:
            await message.reply_text(f"**Error:** {str(e)}")
            
    except IndexError:
        await message.reply_text(
            "**Please provide a channel ID!**\n\n"
            "Example: `/setchannel -100123456789`\n\n"
            "To get channel ID:\n"
            "1. Forward any message from channel to @userinfobot\n"
            "2. Copy the channel ID\n"
            "3. Use it with this command"
        )


@Client.on_message(filters.private & filters.command("viewchannel"))
async def view_channel(client, message):
    user_id = message.from_user.id
    channel_id = await AshutoshGoswami24.get_upload_channel(user_id)
    
    if not channel_id:
        return await message.reply_text(
            "**No channel configured!**\n\n"
            "Use `/setchannel` to set up channel upload."
        )
    
    try:
        chat = await client.get_chat(channel_id)
        await message.reply_text(
            f"**Current Upload Channel:**\n\n"
            f"**Channel:** {chat.title}\n"
            f"**Channel ID:** `{channel_id}`\n"
            f"**Type:** {chat.type}\n\n"
            f"All files are being uploaded to this channel."
        )
    except Exception as e:
        await message.reply_text(
            f"**Channel ID:** `{channel_id}`\n\n"
            f"**Error accessing channel:** {str(e)}\n\n"
            "The channel might have been deleted or bot was removed."
        )


@Client.on_message(filters.private & filters.command("delchannel"))
async def delete_channel(client, message):
    user_id = message.from_user.id
    channel_id = await AshutoshGoswami24.get_upload_channel(user_id)
    
    if not channel_id:
        return await message.reply_text(
            "**No channel configured!**\n\n"
            "Nothing to delete."
        )
    
    await AshutoshGoswami24.delete_upload_channel(user_id)
    await message.reply_text(
        "**Channel Upload Removed Successfully! ✅**\n\n"
        "Files will now be sent to you directly."
    )
