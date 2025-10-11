import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import UserNotParticipant, UsernameNotOccupied, PeerIdInvalid, ChannelPrivate
from config import Config

FORCE_SUB_CHANNELS = Config.FORCE_SUB_CHANNELS

# Commands that should bypass force subscription
EXEMPT_COMMANDS = [
    '/autotrim',
    '/autotrimhelp', 
    '/autotrimstatus',
    '/autotrimcancel',
    '/start',
    '/help'
]


async def not_subscribed(_, __, message):
    """Check if user is subscribed to all required channels"""
    
    # Skip force sub check if no channels configured
    if not FORCE_SUB_CHANNELS:
        return False
    
    # Skip force sub for exempt commands
    if message.text:
        for cmd in EXEMPT_COMMANDS:
            if message.text.startswith(cmd):
                return False
    
    # Check each channel
    for channel in FORCE_SUB_CHANNELS:
        # Skip invalid/empty channels
        if not channel or channel.strip() == "":
            continue
            
        try:
            user = await message._client.get_chat_member(channel, message.from_user.id)
            if user.status in {"kicked", "left"}:
                return True
        except UserNotParticipant:
            return True
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate) as e:
            # Invalid channel - log and skip
            print(f"⚠️ Invalid force sub channel '{channel}': {e}")
            continue
        except Exception as e:
            # Any other error - log and skip to avoid blocking users
            print(f"⚠️ Error checking force sub for channel '{channel}': {e}")
            continue
    
    return False


@Client.on_message(filters.private & filters.create(not_subscribed))
async def forces_sub(client, message):
    """Send force subscription message"""
    not_joined_channels = []
    
    for channel in FORCE_SUB_CHANNELS:
        # Skip invalid/empty channels
        if not channel or channel.strip() == "":
            continue
            
        try:
            user = await client.get_chat_member(channel, message.from_user.id)
            if user.status in {"kicked", "left"}:
                not_joined_channels.append(channel)
        except UserNotParticipant:
            not_joined_channels.append(channel)
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate) as e:
            # Invalid channel - log and skip
            print(f"⚠️ Invalid force sub channel '{channel}': {e}")
            continue
        except Exception as e:
            # Any other error - log and skip
            print(f"⚠️ Error checking force sub for channel '{channel}': {e}")
            continue
    
    # If no valid channels to join, skip force sub
    if not not_joined_channels:
        return
    
    # Create buttons for channels
    buttons = []
    for channel in not_joined_channels:
        # Create proper invite link
        if channel.startswith('-100'):
            # It's a channel ID, need to get username or create invite link
            try:
                chat = await client.get_chat(channel)
                if chat.username:
                    url = f"https://t.me/{chat.username}"
                else:
                    # Private channel - skip or use invite link if available
                    continue
            except:
                continue
        else:
            # It's a username
            url = f"https://t.me/{channel}"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"📢 Join {channel.replace('@', '').capitalize()} 📢",
                url=url
            )
        ])
    
    # Add check button
    buttons.append([
        InlineKeyboardButton(
            text="✅ I am joined ✅",
            callback_data="check_subscription"
        )
    ])
    
    text = "**Sorry, you're not joined to all required channels 😐. Please join the update channels to continue**"
    
    try:
        await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"Error sending force sub message: {e}")


@Client.on_callback_query(filters.regex("check_subscription"))
async def check_subscription(client, callback_query: CallbackQuery):
    """Check if user has joined all channels"""
    user_id = callback_query.from_user.id
    not_joined_channels = []
    
    for channel in FORCE_SUB_CHANNELS:
        # Skip invalid/empty channels
        if not channel or channel.strip() == "":
            continue
            
        try:
            user = await client.get_chat_member(channel, user_id)
            if user.status in {"kicked", "left"}:
                not_joined_channels.append(channel)
        except UserNotParticipant:
            not_joined_channels.append(channel)
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate) as e:
            # Invalid channel - log and skip
            print(f"⚠️ Invalid force sub channel '{channel}': {e}")
            continue
        except Exception as e:
            # Any other error - log and skip
            print(f"⚠️ Error checking force sub for channel '{channel}': {e}")
            continue
    
    if not not_joined_channels:
        await callback_query.message.edit_text(
            "**✅ You have joined all the required channels. Thank you! 😊**\n\n"
            "You can now use the bot. Send /start to continue."
        )
    else:
        # Create buttons for remaining channels
        buttons = []
        for channel in not_joined_channels:
            # Create proper invite link
            if channel.startswith('-100'):
                # It's a channel ID
                try:
                    chat = await client.get_chat(channel)
                    if chat.username:
                        url = f"https://t.me/{chat.username}"
                    else:
                        continue
                except:
                    continue
            else:
                # It's a username
                url = f"https://t.me/{channel}"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"📢 Join {channel.replace('@', '').capitalize()} 📢",
                    url=url
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="✅ I am joined",
                callback_data="check_subscription"
            )
        ])
        
        text = "**You haven't joined all the required channels. Please join them to continue.**"
        
        try:
            await callback_query.message.edit_text(
                text=text, reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            print(f"Error updating force sub message: {e}")
            await callback_query.answer("Please try again later.", show_alert=True)


# Debug: Print configured channels on module load
print(f"[Force Sub] Configured channels: {FORCE_SUB_CHANNELS}")
if FORCE_SUB_CHANNELS:
    for idx, channel in enumerate(FORCE_SUB_CHANNELS, 1):
        if channel and channel.strip():
            print(f"[Force Sub] Channel {idx}: {channel}")
        else:
            print(f"[Force Sub] Channel {idx}: INVALID (empty)")
else:
    print("[Force Sub] ⚠️ No channels configured - Force subscription disabled")
