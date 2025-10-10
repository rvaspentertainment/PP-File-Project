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
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, Config.PORT).start()
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
                
                session_status = "✅ Premium Session Active (4GB)" if Config.STRING_SESSION else "⚠️ Standard Session (2GB)"
                
                await self.send_message(
                    Config.LOG_CHANNEL,
                    f"**__{me.mention} Is Restarted !!**\n\n"
                    f"📅 Date: `{date}`\n"
                    f"⏰ Time: `{time}`\n"
                    f"🌐 Timezone: `Asia/Kolkata`\n"
                    f"🤖 Version: `v{__version__} (Layer {layer})`\n"
                    f"📊 Upload Status: {session_status}\n"
                    f"🎬 Features: Rename, Trim, Merge, Extract, Compress\n\n"
                    f"@pp_bots",
                )
            except Exception as e:
                logging.error(f"Failed to send log channel message: {e}")
                print("Please Make This Bot Admin In Your Log Channel")

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot Stopped 🙄")


# Initialize premium user client if session exists
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
                await asyncio.gather(
                    app.start(),
                    bot_instance.start(),
                )
                logging.info("Bot and Premium User Client Started Successfully! 🚀")
            else:
                await bot_instance.start()
                logging.info("Bot Started (Without Premium Session - 2GB Upload Limit) ⚠️")
            
            # Keep running
            await idle()
        except Exception as e:
            logging.error(f"Error starting services: {e}")
            raise

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")


if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="There is no current event loop")
    main()
