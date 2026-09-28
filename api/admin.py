from flask import Blueprint, jsonify, request
from api.auth import telegram_web_app_auth, admin_required
from database.repositories import MovieRepository, SeriesRepository, UpcomingRepository
from services.health import run_health_checks
import asyncio
import logging

admin_api_bp = Blueprint('admin_api', __name__)
logger = logging.getLogger(__name__)

movie_repo = MovieRepository()
series_repo = SeriesRepository()
upcoming_repo = UpcomingRepository()

@admin_api_bp.route('/health-report', methods=['GET'])
@telegram_web_app_auth
@admin_required
async def get_health_report():
    """Run and return system health checks."""
    report = await run_health_checks() # This function needs to be implemented in services/health.py
    return jsonify(report)

@admin_api_bp.route('/movies/<string:movie_id>', methods=['PUT'])
@telegram_web_app_auth
@admin_required
async def update_movie_admin(movie_id):
    """Admin: Update movie details."""
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided for update.'}), 400
    
    modified_count = await movie_repo.update_movie(movie_id, data)
    if modified_count == 0:
        return jsonify({'message': 'Movie not found or no changes made.'}), 404
    return jsonify({'message': 'Movie updated successfully.'})

@admin_api_bp.route('/movies/<string:movie_id>', methods=['DELETE'])
@telegram_web_app_auth
@admin_required
async def delete_movie_admin(movie_id):
    """Admin: Delete a movie."""
    deleted_count = await movie_repo.delete({"_id": movie_id})
    if deleted_count == 0:
        return jsonify({'message': 'Movie not found.'}), 404
    # Also need to delete associated files, favorites, history entries etc.
    return jsonify({'message': 'Movie deleted successfully.'})

@admin_api_bp.route('/upcoming', methods=['POST'])
@telegram_web_app_auth
@admin_required
async def add_upcoming_admin():
    """Admin: Add new upcoming content."""
    data = request.json
    if not data or not data.get('title_arabic') or not data.get('release_date'):
        return jsonify({'message': 'Title and release date are required.'}), 400

    # Add validation for release_date format
    try:
        # Ensure release_date is stored as datetime object
        from datetime import datetime
        data['release_date'] = datetime.strptime(data['release_date'], '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid release_date format. Use YYYY-MM-DD.'}), 400

    upcoming = await upcoming_repo.add_upcoming(data)
    return jsonify(upcoming), 201

@admin_api_bp.route('/upcoming/<string:upcoming_id>', methods=['DELETE'])
@telegram_web_app_auth
@admin_required
async def delete_upcoming_admin(upcoming_id):
    """Admin: Delete upcoming content."""
    deleted_count = await upcoming_repo.delete_upcoming(upcoming_id)
    if deleted_count == 0:
        return jsonify({'message': 'Upcoming content not found.'}), 404
    return jsonify({'message': 'Upcoming content deleted successfully.'}), 200

@admin_api_bp.route('/upcoming/<string:upcoming_id>/release', methods=['POST'])
@telegram_web_app_auth
@admin_required
async def release_upcoming_admin(upcoming_id):
    """Admin: Mark upcoming content as released, potentially creating a movie entry."""
    upcoming = await upcoming_repo.get_upcoming_by_id(upcoming_id)
    if not upcoming:
        return jsonify({'message': 'Upcoming content not found.'}), 404
    
    # Logic to convert upcoming to a movie/series and add to main collection
    # This is a placeholder, actual implementation would involve detailed data transfer and cleanup
    # For example: new_movie = await movie_repo.create_movie({'title_arabic': upcoming['title_arabic'], ...})
    # Then delete from upcoming
    await upcoming_repo.delete_upcoming(upcoming_id)
    return jsonify({'message': f"Upcoming content '{upcoming_id}' released and processed (placeholder)."}), 200
