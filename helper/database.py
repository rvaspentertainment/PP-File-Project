import motor.motor_asyncio
from config import Config
import logging

class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e
        self.pp_bots = self._client[database_name]
        self.col = self.pp_bots.user

    def new_user(self, id):
        return dict(
            _id=int(id),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @pp_bots",
            format_template=None,
            upload_channel=None,
            media_mode="rename",  # rename, trim, extract, merge, compress, autotrim
            remove_words=[],  # List of words to remove
            replace_words={},  # Dict of old:new replacements
            merge_queue=[],  # Queue for merge operations
            merge_type=None,  # video, audio, subtitle
            compression_qualities=[],  # List of qualities to compress
            media_preference=None,  # document, video, audio
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            try:
                await self.col.insert_one(user)
                from helper.utils import send_log
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    # Thumbnail
    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    # Caption
    async def set_caption(self, id, caption):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    # Format template
    async def set_format_template(self, id, format_template):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    # Media preference
    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    # Metadata
    async def set_metadata(self, id, bool_meta):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"metadata": bool_meta}}
            )
        except Exception as e:
            logging.error(f"Error setting metadata for user {id}: {e}")

    async def get_metadata(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("metadata", True) if user else True
        except Exception as e:
            logging.error(f"Error getting metadata for user {id}: {e}")
            return True

    async def set_metadata_code(self, id, metadata_code):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"metadata_code": metadata_code}}
            )
        except Exception as e:
            logging.error(f"Error setting metadata code for user {id}: {e}")

    async def get_metadata_code(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("metadata_code", "Telegram : @pp_bots") if user else "Telegram : @pp_bots"
        except Exception as e:
            logging.error(f"Error getting metadata code for user {id}: {e}")
            return "Telegram : @pp_bots"

    # Channel upload
    async def set_upload_channel(self, id, channel_id):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"upload_channel": channel_id}}
            )
        except Exception as e:
            logging.error(f"Error setting upload channel for user {id}: {e}")

    async def get_upload_channel(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("upload_channel", None) if user else None
        except Exception as e:
            logging.error(f"Error getting upload channel for user {id}: {e}")
            return None

    async def delete_upload_channel(self, id):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"upload_channel": None}}
            )
        except Exception as e:
            logging.error(f"Error deleting upload channel for user {id}: {e}")

    # Media mode
    async def set_media_mode(self, id, mode):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_mode": mode}}
            )
        except Exception as e:
            logging.error(f"Error setting media mode for user {id}: {e}")

    async def get_media_mode(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_mode", "rename") if user else "rename"
        except Exception as e:
            logging.error(f"Error getting media mode for user {id}: {e}")
            return "rename"

    # Word removal
    async def set_remove_words(self, id, words):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"remove_words": words}}
            )
        except Exception as e:
            logging.error(f"Error setting remove words for user {id}: {e}")

    async def get_remove_words(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("remove_words", []) if user else []
        except Exception as e:
            logging.error(f"Error getting remove words for user {id}: {e}")
            return []

    # Word replacement
    async def set_replace_words(self, id, words_dict):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"replace_words": words_dict}}
            )
        except Exception as e:
            logging.error(f"Error setting replace words for user {id}: {e}")

    async def get_replace_words(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("replace_words", {}) if user else {}
        except Exception as e:
            logging.error(f"Error getting replace words for user {id}: {e}")
            return {}

    # Merge queue
    async def add_to_merge_queue(self, id, file_info):
        try:
            user = await self.col.find_one({"_id": int(id)})
            queue = user.get("merge_queue", []) if user else []
            queue.append(file_info)
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"merge_queue": queue}}
            )
        except Exception as e:
            logging.error(f"Error adding to merge queue for user {id}: {e}")

    async def get_merge_queue(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("merge_queue", []) if user else []
        except Exception as e:
            logging.error(f"Error getting merge queue for user {id}: {e}")
            return []

    async def clear_merge_queue(self, id):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"merge_queue": []}}
            )
        except Exception as e:
            logging.error(f"Error clearing merge queue for user {id}: {e}")

    # Merge type
    async def set_merge_type(self, id, merge_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"merge_type": merge_type}}
            )
        except Exception as e:
            logging.error(f"Error setting merge type for user {id}: {e}")

    async def get_merge_type(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("merge_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting merge type for user {id}: {e}")
            return None

    # Compression qualities
    async def set_compression_qualities(self, id, qualities):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"compression_qualities": qualities}}
            )
        except Exception as e:
            logging.error(f"Error setting compression qualities for user {id}: {e}")

    async def get_compression_qualities(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("compression_qualities", []) if user else []
        except Exception as e:
            logging.error(f"Error getting compression qualities for user {id}: {e}")
            return []


pp_bots = Database(Config.DB_URL, Config.DB_NAME)
AshutoshGoswami24 = Database(Config.DB_URL, Config.DB_NAME)
