import uuid
from typing import Dict, Any, List, Optional
from database.mongodb import MongoManager
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection = MongoManager.get_collection(collection_name)
        if not self.collection:
            raise ValueError(f"MongoDB collection '{collection_name}' not available.")

    async def create(self, document: Dict[str, Any]) -> Dict[str, Any]:
        if '_id' not in document:
            document['_id'] = str(uuid.uuid4())
        await self.collection.insert_one(document)
        return document

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one(query)

    async def find(self, query: Dict[str, Any], sort: Optional[List[tuple]] = None, limit: int = 0, skip: int = 0) -> List[Dict[str, Any]]:
        cursor = self.collection.find(query)
        if sort: 
            cursor = cursor.sort(sort)
        if skip > 0: 
            cursor = cursor.skip(skip)
        if limit > 0: 
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=None)

    async def update(self, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        result = await self.collection.update_one(query, {'$set': update_data})
        return result.modified_count

    async def delete(self, query: Dict[str, Any]) -> int:
        result = await self.collection.delete_one(query)
        return result.deleted_count
    
    def generate_unique_id(self) -> str:
        """Generates a unique ID for documents."""
        return str(uuid.uuid4())

class MovieRepository(BaseRepository):
    def __init__(self):
        super().__init__("movies")

    async def create_movie(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.create(movie_data)

    async def get_movie_by_id(self, movie_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"_id": movie_id})

    async def find_one_by_normalized_title(self, normalized_title: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"normalized_title": normalized_title})

    async def update_movie(self, movie_id: str, update_data: Dict[str, Any]) -> int:
        return await self.update({"_id": movie_id}, update_data)

    async def add_file_to_movie(self, movie_id: str, file_record_id: str) -> None:
        await self.collection.update_one({"_id": movie_id}, {'$addToSet': {'files': file_record_id}})

    async def get_latest_movies(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self.find(query={}, sort=[("added_at", -1)], limit=limit)

class SeriesRepository(BaseRepository):
    def __init__(self):
        super().__init__("series")

    async def create_series(self, series_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.create(series_data)

    async def get_series_by_id(self, series_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"_id": series_id})

    async def find_one_by_normalized_title(self, normalized_title: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"normalized_title": normalized_title})

    async def update_series(self, series_id: str, update_data: Dict[str, Any]) -> int:
        return await self.update({"_id": series_id}, update_data)

    async def add_episode(self, series_id: str, season_number: int, episode_data: Dict[str, Any]) -> Dict[str, Any]:
        # First, ensure the season exists or create it
        season_path = f"seasons.{season_number - 1}" # Assuming 0-indexed array for seasons
        await self.collection.update_one(
            {"_id": series_id, f"seasons.season_number": {'$ne': season_number}},
            {'$push': {'seasons': {'season_number': season_number, 'episodes': []}}}
        )
        # Then add the episode to the correct season
        await self.collection.update_one(
            {"_id": series_id, "seasons.season_number": season_number},
            {'$push': {'seasons.$.episodes': episode_data}}
        )
        return episode_data # Return the newly added episode data

    async def find_episode(self, series_id: str, season_number: int, episode_number: int) -> Optional[Dict[str, Any]]:
        series = await self.collection.find_one(
            {"_id": series_id, "seasons.season_number": season_number},
            {"seasons.$": 1} # Project only the matching season
        )
        if series and 'seasons' in series and series['seasons']:
            for episode in series['seasons'][0].get('episodes', []):
                if episode.get('episode_number') == episode_number:
                    return episode
        return None

    async def update_episode(self, series_id: str, episode_id: str, update_data: Dict[str, Any]) -> int:
        # Update a specific episode within a season
        result = await self.collection.update_one(
            {"_id": series_id, "seasons.episodes._id": episode_id},
            {'$set': {"seasons.$.episodes.$[elem]": update_data}},
            array_filters=[{"elem._id": episode_id}]
        )
        return result.modified_count

    def generate_unique_episode_id(self, series_id: str, season_number: int, episode_number: int) -> str:
        """Generates a predictable but unique ID for an episode."""
        return f"{series_id}-S{season_number}E{episode_number}"


class FileRepository(BaseRepository):
    def __init__(self):
        super().__init__("movie_files") # Using 'movie_files' for both movie and episode files

    async def create_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.create(file_data)

    async def get_by_unique_id(self, file_unique_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"file_unique_id": file_unique_id})

    async def get_by_message_id(self, message_id: int, channel_id: int) -> Optional[Dict[str, Any]]:
        return await self.find_one({"message_id": message_id, "channel_id": channel_id})

    async def delete_by_message_id(self, message_id: int, channel_id: int) -> int:
        result = await self.collection.delete_many({"message_id": message_id, "channel_id": channel_id})
        return result.deleted_count
    
    async def get_files_for_content(self, content_id: str) -> List[Dict[str, Any]]:
        return await self.find({"content_id": content_id})

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.create(user_data)

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return await self.find_one({"telegram_id": telegram_id})

    async def update_user(self, telegram_id: int, update_data: Dict[str, Any]) -> int:
        return await self.update({"telegram_id": telegram_id}, update_data)

# Placeholder for other repositories as needed (Favorites, WatchHistory, etc.)

class FavoritesRepository(BaseRepository):
    def __init__(self):
        super().__init__("favorites")
    
    async def add_favorite(self, user_id: int, content_id: str, content_type: str) -> Dict[str, Any]:
        favorite_data = {"user_id": user_id, "content_id": content_id, "content_type": content_type}
        existing = await self.find_one(favorite_data)
        if not existing:
            return await self.create(favorite_data)
        return existing

    async def remove_favorite(self, user_id: int, content_id: str) -> int:
        return await self.delete({"user_id": user_id, "content_id": content_id})

    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        return await self.find({"user_id": user_id})

class WatchHistoryRepository(BaseRepository):
    def __init__(self):
        super().__init__("watch_history")

    async def add_watch_entry(self, user_id: int, content_id: str, content_type: str, progress: int = 0) -> Dict[str, Any]:
        from datetime import datetime
        entry_data = {"user_id": user_id, "content_id": content_id, "content_type": content_type, "progress": progress, "last_watched_at": datetime.utcnow()}
        existing = await self.find_one({"user_id": user_id, "content_id": content_id})
        if existing:
            await self.update({"_id": existing['_id']}, {'$set': entry_data}) # Update existing entry
            return {**existing, **entry_data}
        else:
            return await self.create(entry_data)

    async def get_user_watch_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.find({"user_id": user_id}, sort=[("last_watched_at", -1)], limit=limit)

class UpcomingRepository(BaseRepository):
    def __init__(self):
        super().__init__("upcoming")

    async def add_upcoming(self, upcoming_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.create(upcoming_data)

    async def get_upcoming_by_id(self, upcoming_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"_id": upcoming_id})

    async def delete_upcoming(self, upcoming_id: str) -> int:
        return await self.delete({"_id": upcoming_id})

    async def get_all_upcoming(self) -> List[Dict[str, Any]]:
        return await self.find(query={}, sort=[("release_date", 1)])
