from typing import List, Dict, Any
from database.repositories import MovieRepository, SeriesRepository, WatchHistoryRepository, FavoritesRepository
import logging
import random

logger = logging.getLogger(__name__)

movie_repo = MovieRepository()
series_repo = SeriesRepository()
watch_history_repo = WatchHistoryRepository()
favorites_repo = FavoritesRepository()

async def get_user_recommendations(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Generates content recommendations for a given user.

    This is a basic recommendation system that prioritizes:
    1. Content similar to recently watched items.
    2. Content similar to favorited items.
    3. Popular content or trending content.
    4. Random content as a fallback.
    """
    recommendations = []
    seen_content_ids = set()

    # 1. Content based on watch history (genre/actor similarity, or simply recent views)
    history = await watch_history_repo.get_user_watch_history(user_id, limit=5) # Look at last 5 watched
    for entry in history:
        if entry['content_type'] == 'movie':
            movie = await movie_repo.get_movie_by_id(entry['content_id'])
            if movie and movie.get('genres'):
                similar_movies = await movie_repo.find({'genres': {'$in': movie['genres']}, '_id': {'$ne': movie['_id']}}, limit=2)
                for m in similar_movies:
                    if m['_id'] not in seen_content_ids:
                        recommendations.append({**m, 'source': 'watch_history', 'score': 0.8})
                        seen_content_ids.add(m['_id'])
        # Add similar logic for series

    # 2. Content based on favorites
    favorites = await favorites_repo.get_user_favorites(user_id)
    for entry in favorites:
        if entry['content_type'] == 'movie':
            movie = await movie_repo.get_movie_by_id(entry['content_id'])
            if movie and movie.get('genres'):
                similar_movies = await movie_repo.find({'genres': {'$in': movie['genres']}, '_id': {'$ne': movie['_id']}}, limit=2)
                for m in similar_movies:
                    if m['_id'] not in seen_content_ids:
                        recommendations.append({**m, 'source': 'favorites', 'score': 0.9})
                        seen_content_ids.add(m['_id'])
        # Add similar logic for series

    # 3. Popular or highest-rated content (placeholder, requires watch counts/ratings)
    # For now, let's just get some latest movies/series as 'popular'
    latest_movies = await movie_repo.get_latest_movies(limit=5)
    for movie in latest_movies:
        if movie['_id'] not in seen_content_ids:
            recommendations.append({**movie, 'source': 'popular', 'score': 0.7})
            seen_content_ids.add(movie['_id'])
    
    # 4. Fallback: random content if not enough recommendations
    if len(recommendations) < limit:
        all_movies_cursor = movie_repo.collection.aggregate([{"$sample": {"size": limit - len(recommendations)}}])
        random_movies = await all_movies_cursor.to_list(length=None)
        for movie in random_movies:
            if movie['_id'] not in seen_content_ids:
                recommendations.append({**movie, 'source': 'random', 'score': 0.5})
                seen_content_ids.add(movie['_id'])

    # Sort recommendations by score and truncate to limit
    recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
    return recommendations[:limit]

async def get_what_to_watch(user_id: int) -> Optional[Dict[str, Any]]:
    """Suggests a single item for the user to watch, perhaps based on a mix of factors."""
    # This could be the top recommendation from the list, or a more curated pick.
    recommendations = await get_user_recommendations(user_id, limit=1)
    return recommendations[0] if recommendations else None

async def get_continue_watching(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves content the user was watching and hasn't finished."""
    continue_watching_entries = await watch_history_repo.find(
        {"user_id": user_id, "progress": {'$lt': 100}}, # Assuming progress < 100 means not finished
        sort=[("last_watched_at", -1)], limit=limit
    )
    # Enrich with actual movie/series data
    results = []
    for entry in continue_watching_entries:
        content = None
        if entry['content_type'] == 'movie':
            content = await movie_repo.get_movie_by_id(entry['content_id'])
        elif entry['content_type'] == 'episode': # Need to distinguish episode from series for now, assuming content_id is episode_id
            # This would require more complex lookup from series collection
            pass # Placeholder

        if content:
            results.append({**content, 'progress': entry['progress'], 'last_watched_at': entry['last_watched_at']})
    return results
