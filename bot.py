import logging
import warnings
from pyrogram import Client, idle
from pyrogram import __version__
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
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)

# Global variables
premium_client = None
app = None

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
        global app, premium_client
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        try:
            web_app = web.AppRunner(await web_server())
            await web_app.setup()
            bind_address = "0.0.0.0"
            await web.TCPSite(web_app, bind_address, Config.PORT).start()
            logging.info(f"✅ Web server started on port {Config.PORT}")
        except Exception as e:
            logging.error(f"⚠️ Failed to start web server: {e}")
        
        logging.info(f"✅✅ {me.first_name} BOT started successfully ✅✅")

        # Notify admins (optional)
        if Config.ADMIN:
            for admin_id in Config.ADMIN:
                try:
                    await self.send_message(
                        admin_id, 
                        f"**__{me.first_name} Is Started.....✨️__**"
                    )
                    logging.info(f"✅ Notified admin: {admin_id}")
                except Exception as e:
                    logging.warning(f"⚠️ Could not notify admin {admin_id}: {e}")

        # Log to channel (optional)
        if Config.LOG_CHANNEL and Config.LOG_CHANNEL != 0:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime("%d %B, %Y")
                time = curr.strftime("%I:%M:%S %p")
                
                # Check if premium client is running
                premium_status = "⚠️ Standard Session (2GB)"
                if Config.STRING_SESSION and app:
                    try:
                        premium_me = await app.get_me()
                        if premium_me.is_premium:
                            premium_status = f"✅ Premium Session Active (4GB) - @{premium_me.username or premium_me.first_name}"
                        else:
                            premium_status = f"⚠️ Non-Premium Session (2GB) - @{premium_me.username or premium_me.first_name}"
                    except Exception as e:
                        premium_status = f"⚠️ Premium Session Failed"
                        logging.warning(f"Premium client check failed: {e}")
                
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
                logging.info("✅ Log channel message sent successfully")
            except Exception as e:
                logging.warning(f"⚠️ Could not send to log channel: {e}")
                logging.warning(f"   Log Channel ID: {Config.LOG_CHANNEL}")
                logging.info("   Bot will continue working without log channel")
        else:
            logging.info("ℹ️ No log channel configured")

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot Stopped 🙄")


bot_instance = Bot()


def main():
    global premium_client, app
    
    # Initialize premium user client
    if Config.STRING_SESSION:
        try:
            premium_client = Client(
                name="PremiumUser",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=Config.STRING_SESSION,
                workers=200,
                sleep_threshold=15,
            )
            app = premium_client
            logging.info("✅ Premium User Client Initialized")
        except Exception as e:
            logging.warning(f"⚠️ Premium client initialization error: {e}")
            logging.info("   Bot will work with 2GB limit")
            premium_client = None
            app = None
    else:
        logging.info("ℹ️ No STRING_SESSION configured - 2GB upload limit")
    
    async def start_services():
        global premium_client, app
        try:
            # Start premium client if available
            if Config.STRING_SESSION and premium_client:
                logging.info("Starting Premium User Client...")
                try:
                    await premium_client.start()
                    premium_me = await premium_client.get_me()
                    logging.info(f"✅ Premium Client Connected: {premium_me.first_name} (@{premium_me.username or 'no username'})")
                    logging.info(f"✅ Premium Client ID: {premium_me.id}")
                    logging.info(f"✅ Premium Status: {'Premium ⭐' if premium_me.is_premium else 'Regular'}")
                except Exception as e:
                    logging.warning(f"⚠️ Premium client start failed: {e}")
                    logging.info("   Bot will work with 2GB limit")
                    premium_client = None
                    app = None
            
            # Start bot
            logging.info("Starting Bot Client...")
            await bot_instance.start()
            
            # Success message
            logging.info("=" * 60)
            if Config.STRING_SESSION and premium_client:
                logging.info("🎉 Bot and Premium User Client Started Successfully! 🚀")
                logging.info("📤 4GB Upload Support: ENABLED ✅")
            else:
                logging.info("🎉 Bot Started Successfully! 🚀")
                logging.info("📤 Upload Limit: 2GB")
            logging.info("=" * 60)
            
            # Keep running
            await idle()
            
        except Exception as e:
            logging.error(f"❌ Error starting services: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Cleanup
            try:
                if premium_client and hasattr(premium_client, 'is_connected') and premium_client.is_connected:
                    await premium_client.stop()
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
