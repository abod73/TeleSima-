from flask import Blueprint, jsonify, request
from database.repositories import MovieRepository, SeriesRepository, FavoritesRepository, WatchHistoryRepository
from services.search import search_content
from api.auth import telegram_web_app_auth
import asyncio
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Initialize repositories
movie_repo = MovieRepository()
series_repo = SeriesRepository()
favorites_repo = FavoritesRepository()
watch_history_repo = WatchHistoryRepository()

@api_bp.route('/movies', methods=['GET'])
@telegram_web_app_auth
async def get_movies():
    """Get a list of movies, with optional filters and sorting."""
    # Example: /api/movies?limit=10&offset=0&sort_by=added_at&order=desc
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    sort_by = request.args.get('sort_by', 'added_at')
    order = -1 if request.args.get('order', 'desc') == 'desc' else 1

    # Implement more complex filtering later based on query parameters
    query = {}
    if sort_by == 'added_at':
        movies = await movie_repo.find(query, sort=[(sort_by, order)], limit=limit, skip=offset)
    else:
        # Default sorting if not by added_at (or implement other sort logic)
        movies = await movie_repo.find(query, limit=limit, skip=offset)

    return jsonify(movies)

@api_bp.route('/movies/<string:movie_id>', methods=['GET'])
@telegram_web_app_auth
async def get_movie_details(movie_id):
    """Get details for a specific movie by movie_id."""
    movie = await movie_repo.get_movie_by_id(movie_id)
    if not movie:
        return jsonify({'message': 'Movie not found'}), 404
    
    # Potentially enrich movie data with file details
    # movie_files = await file_repo.get_files_for_content(movie_id)
    # movie['files'] = movie_files

    return jsonify(movie)

@api_bp.route('/series', methods=['GET'])
@telegram_web_app_auth
async def get_series_list():
    """Get a list of series."""
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    series = await series_repo.find(query={}, sort=[('added_at', -1)], limit=limit, skip=offset)
    return jsonify(series)

@api_bp.route('/series/<string:series_id>', methods=['GET'])
@telegram_web_app_auth
async def get_series_details(series_id):
    """Get details for a specific series by series_id."""
    series = await series_repo.get_series_by_id(series_id)
    if not series:
        return jsonify({'message': 'Series not found'}), 404
    return jsonify(series)

@api_bp.route('/series/<string:series_id>/season/<int:season_number>/episode/<int:episode_number>', methods=['GET'])
@telegram_web_app_auth
async def get_episode_details(series_id, season_number, episode_number):
    """Get details for a specific episode."""
    episode = await series_repo.find_episode(series_id, season_number, episode_number)
    if not episode:
        return jsonify({'message': 'Episode not found'}), 404
    return jsonify(episode)

@api_bp.route('/search', methods=['GET'])
@telegram_web_app_auth
async def search():
    """Search for movies and series."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'message': 'Query parameter "q" is required.'}), 400
    
    # Add filters for year, genre, etc. from request.args
    search_results = await search_content(query)
    return jsonify(search_results)

@api_bp.route('/favorites', methods=['GET'])
@telegram_web_app_auth
async def get_favorites():
    user_id = request.telegram_user['id']
    favorites = await favorites_repo.get_user_favorites(user_id)
    # You might want to enrich this with movie/series details
    return jsonify(favorites)

@api_bp.route('/favorites', methods=['POST'])
@telegram_web_app_auth
async def add_favorite():
    user_id = request.telegram_user['id']
    data = request.json
    content_id = data.get('content_id')
    content_type = data.get('content_type') # 'movie' or 'series'

    if not content_id or not content_type:
        return jsonify({'message': 'content_id and content_type are required.'}), 400
    
    favorite = await favorites_repo.add_favorite(user_id, content_id, content_type)
    return jsonify(favorite), 201

@api_bp.route('/favorites/<string:content_id>', methods=['DELETE'])
@telegram_web_app_auth
async def remove_favorite(content_id):
    user_id = request.telegram_user['id']
    deleted_count = await favorites_repo.remove_favorite(user_id, content_id)
    if deleted_count == 0:
        return jsonify({'message': 'Favorite not found for user.'}), 404
    return jsonify({'message': 'Favorite removed.'}), 200

@api_bp.route('/history', methods=['GET'])
@telegram_web_app_auth
async def get_watch_history():
    user_id = request.telegram_user['id']
    history = await watch_history_repo.get_user_watch_history(user_id)
    return jsonify(history)

@api_bp.route('/history', methods=['POST'])
@telegram_web_app_auth
async def add_to_watch_history():
    user_id = request.telegram_user['id']
    data = request.json
    content_id = data.get('content_id')
    content_type = data.get('content_type')
    progress = data.get('progress', 0)

    if not content_id or not content_type:
        return jsonify({'message': 'content_id and content_type are required.'}), 400

    entry = await watch_history_repo.add_watch_entry(user_id, content_id, content_type, progress)
    return jsonify(entry), 201
