import logging
import warnings
from pyrogram import Client, idle
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from pytz import timezone
from datetime import datetime
import asyncio
from plugins.web_support import web_server
import pyromod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="pp_bots",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=15,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        web_app = web.AppRunner(await web_server())
        await web_app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(web_app, bind_address, Config.PORT).start()
        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")

        # Notify admins
        for id in Config.ADMIN:
            try:
                await self.send_message(
                    id, f"**__{me.first_name} Is Started.....✨️__**"
                )
            except:
                pass

        # Log to channel
        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime("%d %B, %Y")
                time = curr.strftime("%I:%M:%S %p")
                
                # ✅ Check if premium client is actually running
                premium_status = "⚠️ Standard Session (2GB)"
                if Config.STRING_SESSION and app:
                    try:
                        premium_me = await app.get_me()
                        premium_status = f"✅ Premium Session Active (4GB) - @{premium_me.username or premium_me.first_name}"
                    except:
                        premium_status = "⚠️ Premium Session Failed (Using 2GB)"
                
                await self.send_message(
                    Config.LOG_CHANNEL,
                    f"**__{me.mention} Is Restarted !!**\n\n"
                    f"📅 Date: `{date}`\n"
                    f"⏰ Time: `{time}`\n"
                    f"🌐 Timezone: `Asia/Kolkata`\n"
                    f"🤖 Version: `v{__version__} (Layer {layer})`\n"
                    f"📊 Upload Status: {premium_status}\n"
                    f"🎬 Features: Rename, Trim, Merge, Extract, Compress\n\n"
                    f"@pp_bots",
                )
            except Exception as e:
                logging.error(f"Failed to send log channel message: {e}")
                print("Please Make This Bot Admin In Your Log Channel")

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot Stopped 🙄")


# ✅ Initialize premium user client BEFORE bot instance
app = None
if Config.STRING_SESSION:
    try:
        app = Client(
            name="PremiumUser",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            session_string=Config.STRING_SESSION,
            workers=200,
            sleep_threshold=15,
        )
        logging.info("Premium User Client Initialized ✅")
    except Exception as e:
        logging.error(f"Premium client initialization error: {e}")
        app = None

bot_instance = Bot()


def main():
    async def start_services():
        try:
            if Config.STRING_SESSION and app:
                logging.info("Starting Premium User Client...")
                await app.start()
                
                try:
                    premium_me = await app.get_me()
                    logging.info(f"✅ Premium Client Connected: {premium_me.first_name} (@{premium_me.username or 'no username'})")
                    logging.info(f"✅ Premium Client ID: {premium_me.id}")
                    logging.info(f"✅ Premium Status: {'Premium ⭐' if premium_me.is_premium else 'Regular'}")
                except Exception as e:
                    logging.error(f"❌ Premium client verification failed: {e}")
                
                logging.info("Starting Bot Client...")
                await bot_instance.start()
                
                logging.info("=" * 60)
                logging.info("🎉 Bot and Premium User Client Started Successfully! 🚀")
                logging.info("📤 4GB Upload Support: ENABLED ✅")
                logging.info("=" * 60)
            else:
                await bot_instance.start()
                logging.info("=" * 60)
                logging.info("⚠️ Bot Started (Without Premium Session - 2GB Upload Limit)")
                logging.info("💡 Add STRING_SESSION env variable for 4GB support")
                logging.info("=" * 60)
            
            # Keep running
            await idle()
            
        except Exception as e:
            logging.error(f"❌ Error starting services: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # ✅ Proper cleanup
            try:
                if app and hasattr(app, 'is_connected') and app.is_connected:
                    await app.stop()
                    logging.info("Premium client stopped")
            except Exception as e:
                logging.error(f"Error stopping premium client: {e}")
            
            try:
                if bot_instance and hasattr(bot_instance, 'is_connected') and bot_instance.is_connected:
                    await bot_instance.stop()
                    logging.info("Bot stopped")
            except Exception as e:
                logging.error(f"Error stopping bot: {e}")

    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="There is no current event loop")
    main()
