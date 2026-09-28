from database.mongodb import MongoManager
import logging

logger = logging.getLogger(__name__)

async def create_all_indexes():
    """Ensures all necessary MongoDB indexes are created."""
    db = MongoManager.get_db()
    if not db:
        logger.error("Cannot create indexes: MongoDB not initialized.")
        return

    # Movies Collection
    movies_col = db.movies
    await movies_col.create_index("normalized_title", unique=True, name="normalized_title_idx")
    await movies_col.create_index("movie_id", unique=True, name="movie_id_idx") # For canonical lookup
    await movies_col.create_index("year", name="year_idx")
    await movies_col.create_index("genres", name="genres_idx")
    await movies_col.create_index([("title_arabic", "text"), ("title_english", "text")], name="movie_text_search_idx")
    await movies_col.create_index("added_at", name="added_at_idx")
    logger.info("Indexes created for 'movies' collection.")

    # Series Collection
    series_col = db.series
    await series_col.create_index("normalized_title", unique=True, name="normalized_series_title_idx")
    await series_col.create_index("year", name="series_year_idx")
    await series_col.create_index("genres", name="series_genres_idx")
    await series_col.create_index([("title_arabic", "text"), ("title_english", "text")], name="series_text_search_idx")
    await series_col.create_index("added_at", name="series_added_at_idx")
    # Index for episode lookup within series (nested)
    await series_col.create_index("seasons.episodes._id", unique=True, name="episode_id_idx", partialFilterExpression={'seasons.episodes._id': {'$exists': True}})
    await series_col.create_index("seasons.season_number", name="season_number_idx")
    await series_col.create_index("seasons.episodes.episode_number", name="episode_number_idx")
    logger.info("Indexes created for 'series' collection.")

    # Movie Files Collection (if separate)
    # Or, if files are embedded, then it might be movie_files.file_unique_id
    movie_files_col = db.movie_files # Assuming a separate collection for individual files
    await movie_files_col.create_index("file_unique_id", unique=True, name="file_unique_id_idx")
    await movie_files_col.create_index("message_id", name="message_id_idx")
    await movie_files_col.create_index("channel_id", name="channel_id_idx")
    await movie_files_col.create_index("content_id", name="content_id_idx") # Links to movie_id or episode_id
    await movie_files_col.create_index("indexed_at", name="file_indexed_at_idx")
    logger.info("Indexes created for 'movie_files' collection.")

    # Users Collection
    users_col = db.users
    await users_col.create_index("telegram_id", unique=True, name="telegram_id_idx")
    logger.info("Indexes created for 'users' collection.")

    # Favorites, Watch History, etc.
    await db.favorites.create_index([("user_id", 1), ("content_id", 1)], unique=True, name="user_content_favorite_idx")
    await db.watch_history.create_index([("user_id", 1), ("content_id", 1)], name="user_content_history_idx")
    await db.watch_history.create_index("last_watched_at", name="last_watched_at_idx")
    await db.user_ratings.create_index([("user_id", 1), ("content_id", 1)], unique=True, name="user_content_rating_idx")
    logger.info("Indexes created for user interaction collections.")

    # Upcoming content
    await db.upcoming.create_index("release_date", name="upcoming_release_date_idx")
    logger.info("Indexes created for 'upcoming' collection.")


if __name__ == '__main__':
    print("MongoDB index creation script defined. Not executing in Colab.")
    # In a deployment scenario, you might call this like:
    # import asyncio
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()
    # MongoManager.initialize(os.getenv("MONGODB_URI"))
    # asyncio.run(create_all_indexes())
