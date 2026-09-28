import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update, Message
from telegram.constants import MessageEntityType

# Assuming these would be defined elsewhere or passed in
from database.repositories import MovieRepository, SeriesRepository, FileRepository
from bot.parser import parse_caption

logger = logging.getLogger(__name__)

class TelegramIndexer:
    def __init__(self, movie_repo: MovieRepository, series_repo: SeriesRepository, file_repo: FileRepository):
        self.movie_repo = movie_repo
        self.series_repo = series_repo
        self.file_repo = file_repo
        self.allowed_channel_ids = [] # This should be loaded from config/DB

    async def process_new_post(self, message: Message) -> Optional[Dict[str, Any]]:
        """Processes a new Telegram message (post) for indexing."""
        if not self._is_message_indexable(message):
            return None

        logger.info(f"Processing new message from chat {message.chat.id}, message_id {message.message_id}")

        parsed_data = parse_caption(message.caption or message.text)
        if not parsed_data: # If no caption or text, or parsing failed to extract meaningful data
            logger.warning(f"Skipping message {message.message_id}: No meaningful data in caption/text.")
            return None

        movie_info = parsed_data.get('movie_info', {})
        series_info = parsed_data.get('series_info', {})

        file_data = self._extract_file_data(message)
        if not file_data:
            logger.warning(f"Skipping message {message.message_id}: No file found for indexing.")
            return None

        file_unique_id = file_data['file_unique_id']

        # Check for duplicate file_unique_id first
        existing_file = await self.file_repo.get_by_unique_id(file_unique_id)
        if existing_file:
            logger.info(f"Duplicate file_unique_id {file_unique_id} detected for message {message.message_id}. Updating existing record.")
            # Optionally update existing file metadata if new info is available
            await self.file_repo.update_file(existing_file['_id'], {'updated_at': datetime.utcnow()})
            return None # Or return updated movie/series info if it's considered an update to content

        # Determine if it's a movie or an episode
        if series_info.get('season') and series_info.get('episode'):
            # This is an episode
            series_doc = await self._get_or_create_series(series_info, message)
            if series_doc:
                episode_doc = await self._get_or_create_episode(series_doc['_id'], series_info, message, file_data)
                if episode_doc:
                    await self._create_file_record(file_data, episode_doc['_id'], 'episode', message)
                    return {'type': 'episode', 'series_id': series_doc['_id'], 'episode_id': episode_doc['_id']}
        else:
            # This is a movie
            movie_doc = await self._get_or_create_movie(movie_info, message)
            if movie_doc:
                await self._create_file_record(file_data, movie_doc['_id'], 'movie', message)
                return {'type': 'movie', 'movie_id': movie_doc['_id']}

        logger.error(f"Failed to index message {message.message_id}. No movie, series, or episode data could be processed.")
        return None

    async def process_edited_post(self, message: Message) -> Optional[Dict[str, Any]]:
        """Processes an edited Telegram message."""
        logger.info(f"Processing edited message from chat {message.chat.id}, message_id {message.message_id}")
        # For edited posts, we should re-parse the caption and update the corresponding movie/episode/file entry
        # This requires linking the message_id to an existing indexed item.
        # This is a complex operation as it might change movie_id if title changes significantly etc.
        # For simplicity, we'll assume we only update the metadata linked to the message_id.

        existing_file_record = await self.file_repo.get_by_message_id(message.message_id, message.chat.id)
        if not existing_file_record:
            logger.warning(f"Edited message {message.message_id} not found in index. Attempting to process as new.")
            return await self.process_new_post(message)

        parsed_data = parse_caption(message.caption or message.text)
        if not parsed_data: # If no caption or text, or parsing failed to extract meaningful data
            logger.warning(f"No meaningful data in edited caption/text for message {message.message_id}. Skipping metadata update.")
            return None

        # Update movie/series/episode metadata based on parsed_data and existing_file_record
        update_fields = {'updated_at': datetime.utcnow()}
        if parsed_data.get('movie_info'):
            update_fields.update(parsed_data['movie_info'])
        elif parsed_data.get('series_info'):
            # This is more complex, might need to update series/episode docs
            pass

        # Example: update movie directly if it's a movie file
        if existing_file_record.get('content_type') == 'movie':
            await self.movie_repo.update_movie(existing_file_record['content_id'], update_fields)
            logger.info(f"Updated movie {existing_file_record['content_id']} from edited message {message.message_id}")
        # Similar logic for series/episode

        return {'type': 'update', 'message_id': message.message_id, 'content_id': existing_file_record.get('content_id')}

    async def process_deleted_post(self, chat_id: int, message_id: int) -> None:
        """Processes a deleted Telegram message."""
        logger.info(f"Processing deleted message from chat {chat_id}, message_id {message_id}")
        # Find and remove the corresponding file record(s)
        deleted_count = await self.file_repo.delete_by_message_id(message_id, chat_id)
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} file record(s) associated with message {message_id}.")
        else:
            logger.warning(f"No file records found for deleted message {message_id}.")

    def _is_message_indexable(self, message: Message) -> bool:
        """Checks if a message is from an allowed channel and contains media or text relevant for indexing."""
        if message.chat.id not in self.allowed_channel_ids:
            return False
        if not (message.photo or message.video or message.document or message.text or message.caption):
            return False # No content to index
        return True

    def _extract_file_data(self, message: Message) -> Optional[Dict[str, Any]]:
        """Extracts common file data from a message."""
        file_object = None
        if message.video:
            file_object = message.video
        elif message.document:
            file_object = message.document
        elif message.photo: # Use the largest photo as poster
            file_object = message.photo[-1] if message.photo else None

        if file_object:
            return {
                'file_id': file_object.file_id,
                'file_unique_id': file_object.file_unique_id,
                'file_size': file_object.file_size,
                'mime_type': file_object.mime_type if hasattr(file_object, 'mime_type') else None,
                'width': file_object.width if hasattr(file_object, 'width') else None,
                'height': file_object.height if hasattr(file_object, 'height') else None,
                'duration': file_object.duration if hasattr(file_object, 'duration') else None,
                'channel_id': message.chat.id,
                'message_id': message.message_id,
                'indexed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'caption': message.caption, # Store original caption for re-parsing if needed
            }
        return None

    async def _get_or_create_movie(self, movie_info: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Gets an existing movie or creates a new one."""
        normalized_title = movie_info.get('normalized_title')
        movie = None
        if normalized_title:
            movie = await self.movie_repo.find_one_by_normalized_title(normalized_title)

        if not movie:
            # Generate a new movie_id if not found, ensure it's unique
            new_movie_id = self.movie_repo.generate_unique_id()
            movie_data = {
                '_id': new_movie_id, # Using _id as movie_id
                'title_arabic': movie_info.get('title_arabic'),
                'title_english': movie_info.get('title_english'),
                'normalized_title': normalized_title,
                'year': movie_info.get('year'),
                'genres': movie_info.get('genres'),
                'rating': movie_info.get('rating'),
                'country': movie_info.get('country'),
                'duration': movie_info.get('duration'),
                'story': movie_info.get('story'),
                'poster_file_id': None, # To be updated if a poster is found later
                'added_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'files': [] # List of file_ids
            }
            movie = await self.movie_repo.create_movie(movie_data)
            logger.info(f"Created new movie: {movie['title_arabic']} ({movie['_id']})")
        else:
            # Update existing movie metadata if needed
            await self.movie_repo.update_movie(movie['_id'], {'updated_at': datetime.utcnow()})
            logger.info(f"Found existing movie: {movie['title_arabic']} ({movie['_id']})")

        return movie

    async def _get_or_create_series(self, series_info: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Gets an existing series or creates a new one."""
        normalized_title = series_info.get('normalized_title')
        series = None
        if normalized_title:
            series = await self.series_repo.find_one_by_normalized_title(normalized_title)

        if not series:
            new_series_id = self.series_repo.generate_unique_id()
            series_data = {
                '_id': new_series_id,
                'title_arabic': series_info.get('title_arabic'),
                'title_english': series_info.get('title_english'),
                'normalized_title': normalized_title,
                'year': series_info.get('year'),
                'genres': series_info.get('genres'),
                'story': series_info.get('story'),
                'poster_file_id': None,
                'added_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'seasons': [] # Stores season objects
            }
            series = await self.series_repo.create_series(series_data)
            logger.info(f"Created new series: {series['title_arabic']} ({series['_id']})")
        else:
            await self.series_repo.update_series(series['_id'], {'updated_at': datetime.utcnow()})
            logger.info(f"Found existing series: {series['title_arabic']} ({series['_id']})")
        return series

    async def _get_or_create_episode(self, series_id: str, series_info: Dict[str, Any], message: Message, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gets an existing episode or creates a new one."""
        season_number = series_info['season']
        episode_number = series_info['episode']

        episode = await self.series_repo.find_episode(series_id, season_number, episode_number)

        if not episode:
            new_episode_id = self.series_repo.generate_unique_episode_id(series_id, season_number, episode_number)
            episode_data = {
                '_id': new_episode_id,
                'season_number': season_number,
                'episode_number': episode_number,
                'title_arabic': series_info.get('episode_title_arabic'),
                'title_english': series_info.get('episode_title_english'),
                'duration': series_info.get('episode_duration'),
                'plot': series_info.get('episode_plot'),
                'poster_file_id': None,
                'added_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'files': []
            }
            episode = await self.series_repo.add_episode(series_id, season_number, episode_data)
            logger.info(f"Created new episode: S{season_number}E{episode_number} for series {series_id}")
        else:
            await self.series_repo.update_episode(series_id, episode['_id'], {'updated_at': datetime.utcnow()})
            logger.info(f"Found existing episode: S{season_number}E{episode_number} for series {series_id}")
        return episode

    async def _create_file_record(self, file_data: Dict[str, Any], content_id: str, content_type: str, message: Message) -> Dict[str, Any]:
        """Creates a file record and links it to a movie or episode."""
        # Generate file_id, similar to movie_id, or use Telegram's file_id
        file_record_id = self.file_repo.generate_unique_id() # Unique ID for our file record
        file_record = {
            '_id': file_record_id,
            'content_id': content_id, # Link to movie_id or episode_id
            'content_type': content_type, # 'movie' or 'episode'
            'quality': parse_caption(message.caption or message.text).get('quality'), # Extract quality again
            **file_data # Include all extracted Telegram file data
        }
        await self.file_repo.create_file(file_record)

        if content_type == 'movie':
            await self.movie_repo.add_file_to_movie(content_id, file_record_id)
        elif content_type == 'episode':
            await self.series_repo.add_file_to_episode(content_id, file_record_id)

        logger.info(f"Created file record {file_record_id} for {content_type} {content_id}")
        return file_record

    async def process_media_group(self, messages: list[Message]) -> None:
        """Processes a media group, linking files to a single movie/episode."""
        if not messages:
            return

        # All messages in a media group share the same caption (usually the first one)
        first_message = messages[0]
        parsed_data = parse_caption(first_message.caption or first_message.text)
        if not parsed_data:
            logger.warning(f"Skipping media group {first_message.media_group_id}: No meaningful data in caption.")
            return

        movie_info = parsed_data.get('movie_info', {})
        series_info = parsed_data.get('series_info', {})

        if series_info.get('season') and series_info.get('episode'):
            # This is a series episode with multiple qualities/files
            series_doc = await self._get_or_create_series(series_info, first_message)
            if not series_doc:
                return
            episode_doc = await self._get_or_create_episode(series_doc['_id'], series_info, first_message, {})
            if not episode_doc:
                return

            for msg in messages:
                file_data = self._extract_file_data(msg)
                if file_data:
                    await self._create_file_record(file_data, episode_doc['_id'], 'episode', msg)
                else:
                    logger.warning(f"Could not extract file data from message {msg.message_id} in media group {msg.media_group_id}")

        else:
            # This is a movie with multiple qualities/files
            movie_doc = await self._get_or_create_movie(movie_info, first_message)
            if not movie_doc:
                return

            for msg in messages:
                file_data = self._extract_file_data(msg)
                if file_data:
                    await self._create_file_record(file_data, movie_doc['_id'], 'movie', msg)
                else:
                    logger.warning(f"Could not extract file data from message {msg.message_id} in media group {msg.media_group_id}")

        logger.info(f"Processed media group {first_message.media_group_id}")

# Placeholder for imports needed for handlers.py to avoid circular dependency in initial writes
from telegram import InlineKeyboardButton
from telegram.web_app import WebAppInfo
