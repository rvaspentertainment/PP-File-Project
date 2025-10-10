from config import Config, Txt
from helper.database import pp_bots
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = Config.ADMIN

# Flag to indicate if the bot is restarting
is_restarting = False


@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    """Restart the bot"""
    global is_restarting
    if not is_restarting:
        is_restarting = True
        restart_msg = await m.reply_text(
            "**🔄 Restarting Bot...**\n\n"
            "Please wait a moment..."
        )
        
        try:
            # Stop bot gracefully
            await asyncio.sleep(2)
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            await restart_msg.edit(f"**❌ Restart Failed:**\n`{e}`")
            is_restarting = False


@Client.on_message(filters.private & filters.command(["tutorial", "guide"]))
async def tutorial(bot, message):
    """Show tutorial/guide"""
    try:
        user_id = message.from_user.id
        format_template = await pp_bots.get_format_template(user_id)
        
        await message.reply_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template or "Not Set"),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Full Guide", callback_data="help")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")]
            ]),
        )
    except Exception as e:
        logging.error(f"Error in /tutorial: {e}")


@Client.on_message(filters.private & filters.command(["ping", "p"]))
async def ping(_, message):
    """Check bot latency"""
    start_t = time.time()
    rm = await message.reply_text("🏓 Pinging...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"**🏓 Pong!**\n\n**Latency:** `{time_taken_s:.3f} ms`")


@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    """Get bot statistics (Admin only)"""
    total_users = await pp_bots.total_users_count()
    uptime = time.time() - Config.BOT_UPTIME
    uptime_str = f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s"
    
    start_t = time.time()
    st = await message.reply_text("**📊 Fetching statistics...**")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    
    # Get disk space
    try:
        import psutil
        disk = psutil.disk_usage('/')
        disk_free = disk.free / (1024**3)  # GB
        disk_total = disk.total / (1024**3)  # GB
        disk_used_percent = disk.percent
    except:
        disk_free = 0
        disk_total = 0
        disk_used_percent = 0
    
    premium_status = "✅ Active (4GB)" if Config.STRING_SESSION else "❌ Not Active (2GB)"
    
    await st.edit(
        f"**📊 BOT STATISTICS**\n\n"
        f"**👥 Users:** `{total_users}`\n"
        f"**⏰ Uptime:** `{uptime_str}`\n"
        f"**🏓 Ping:** `{time_taken_s:.3f} ms`\n"
        f"**💎 Premium:** {premium_status}\n\n"
        f"**💾 Disk Space:**\n"
        f"├ Free: `{disk_free:.2f} GB`\n"
        f"├ Total: `{disk_total:.2f} GB`\n"
        f"└ Used: `{disk_used_percent}%`\n\n"
        f"**🎬 Features Active:**\n"
        f"├ Rename ✅\n"
        f"├ Trim ✅\n"
        f"├ Extract ✅\n"
        f"├ Merge ✅\n"
        f"├ Compress ✅\n"
        f"└ Auto Trim ✅\n\n"
        f"**Powered by @pp_bots**"
    )


@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    """Broadcast message to all users (Admin only)"""
    all_users = await pp_bots.get_all_users()
    broadcast_msg = m.reply_to_message
    
    sts_msg = await m.reply_text(
        "**📢 Broadcast Started!**\n\n"
        "Preparing to send messages..."
    )
    
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await pp_bots.total_users_count()
    
    async for user in all_users:
        sts = await send_msg(user["_id"], broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        if sts == 400:
            await pp_bots.delete_user(user["_id"])
        
        done += 1
        
        # Update status every 20 users
        if done % 20 == 0:
            try:
                await sts_msg.edit(
                    f"**📢 Broadcast In Progress**\n\n"
                    f"**Total Users:** `{total_users}`\n"
                    f"**Completed:** `{done}/{total_users}`\n"
                    f"**Success:** `{success}` ✅\n"
                    f"**Failed:** `{failed}` ❌\n"
                    f"**Progress:** `{(done/total_users)*100:.1f}%`"
                )
            except:
                pass
    
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    
    await sts_msg.edit(
        f"**✅ Broadcast Completed!**\n\n"
        f"**Total Users:** `{total_users}`\n"
        f"**Completed:** `{done}/{total_users}`\n"
        f"**Success:** `{success}` ✅\n"
        f"**Failed:** `{failed}` ❌\n"
        f"**Time Taken:** `{completed_in}`\n\n"
        f"**Powered by @pp_bots**"
    )


async def send_msg(user_id, message):
    """Helper function to send broadcast messages"""
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id}: Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id}: Blocked")
        return 400
