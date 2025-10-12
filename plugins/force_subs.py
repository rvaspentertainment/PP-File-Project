import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import UserNotParticipant, UsernameNotOccupied, PeerIdInvalid, ChannelPrivate
from config import Config
import logging

FORCE_SUB_CHANNELS = Config.FORCE_SUB_CHANNELS

# Commands that should bypass force subscription
EXEMPT_COMMANDS = [
    'start', 'help', 'about', 'donate', 'ping', 'status',
    'autotrim', 'autotrimhelp', 'autotrimstatus', 'autotrimcancel'
]

async def not_subscribed(_, __, message):
    """Check if user is subscribed to all required channels"""
    
    # Skip force sub check if no channels configured or empty
    if not FORCE_SUB_CHANNELS or FORCE_SUB_CHANNELS == ['']:
        return False
    
    # Skip force sub for exempt commands
    if message.text:
        text_lower = message.text.lower()
        for cmd in EXEMPT_COMMANDS:
            if text_lower.startswith(f'/{cmd}'):
                return False
    
    # Skip force sub for callback queries
    if hasattr(message, 'data'):
        return False
    
    # Check each channel
    for channel in FORCE_SUB_CHANNELS:
        # Skip invalid/empty channels
        if not channel or channel.strip() == "" or channel == "None":
            continue
            
        try:
            user = await message._client.get_chat_member(channel, message.from_user.id)
            if user.status in {"kicked", "left"}:
                logging.info(f"User {message.from_user.id} not subscribed to {channel}")
                return True
        except UserNotParticipant:
            logging.info(f"User {message.from_user.id} not participant in {channel}")
            return True
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate) as e:
            logging.warning(f"Invalid force sub channel '{channel}': {e}")
            continue
        except Exception as e:
            logging.error(f"Error checking force sub for channel '{channel}': {e}")
            continue
    
    return False


@Client.on_message(filters.private & filters.create(not_subscribed), group=-1)
async def forces_sub(client, message):
    """Send force subscription message"""
    not_joined_channels = []
    
    for channel in FORCE_SUB_CHANNELS:
        # Skip invalid/empty channels
        if not channel or channel.strip() == "" or channel == "None":
            continue
            
        try:
            user = await client.get_chat_member(channel, message.from_user.id)
            if user.status in {"kicked", "left"}:
                not_joined_channels.append(channel)
        except UserNotParticipant:
            not_joined_channels.append(channel)
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate) as e:
            logging.warning(f"Invalid force sub channel '{channel}': {e}")
            continue
        except Exception as e:
            logging.error(f"Error checking force sub for channel '{channel}': {e}")
            continue
    
    # If no valid channels to join, skip force sub
    if not not_joined_channels:
        return
    
    # Create buttons for channels
    buttons = []
    for channel in not_joined_channels:
        # Create proper invite link
        if channel.startswith('-100'):
            try:
                chat = await client.get_chat(channel)
                if chat.username:
                    url = f"https://t.me/{chat.username}"
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"📢 Join {chat.title} 📢",
                            url=url
                        )
                    ])
            except:
                continue
        else:
            # It's a username
            url = f"https://t.me/{channel.replace('@', '')}"
            buttons.append([
                InlineKeyboardButton(
                    text=f"📢 Join {channel.replace('@', '').capitalize()} 📢",
                    url=url
                )
            ])
    
    # Add check button
    if buttons:
        buttons.append([
            InlineKeyboardButton(
                text="✅ I Joined, Check Again ✅",
                callback_data="check_subscription"
            )
        ])
        
        text = "**⚠️ You must join our channel(s) to use this bot**\n\n" \
               "Please join the channel(s) below and click 'Check Again':"
        
        try:
            await message.reply_text(
                text=text, 
                reply_markup=InlineKeyboardMarkup(buttons),
                quote=True
            )
        except Exception as e:
            logging.error(f"Error sending force sub message: {e}")


@Client.on_callback_query(filters.regex("check_subscription"))
async def check_subscription(client, callback_query: CallbackQuery):
    """Check if user has joined all channels"""
    user_id = callback_query.from_user.id
    not_joined_channels = []
    
    for channel in FORCE_SUB_CHANNELS:
        if not channel or channel.strip() == "" or channel == "None":
            continue
            
        try:
            user = await client.get_chat_member(channel, user_id)
            if user.status in {"kicked", "left"}:
                not_joined_channels.append(channel)
        except UserNotParticipant:
            not_joined_channels.append(channel)
        except (UsernameNotOccupied, PeerIdInvalid, ChannelPrivate):
            continue
        except Exception:
            continue
    
    if not not_joined_channels:
        await callback_query.message.delete()
        await callback_query.answer(
            "✅ Thank you! You can now use the bot. Send /start",
            show_alert=True
        )
    else:
        await callback_query.answer(
            "❌ Please join all channels first!",
            show_alert=True
        )


# Debug logging
if FORCE_SUB_CHANNELS and FORCE_SUB_CHANNELS != ['']:
    logging.info(f"[Force Sub] Enabled for channels: {FORCE_SUB_CHANNELS}")
else:
    logging.info("[Force Sub] Disabled - No channels configured")
