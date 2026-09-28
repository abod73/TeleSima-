from typing import Dict, Any, List
import logging
from database.mongodb import MongoManager
from database.repositories import MovieRepository, SeriesRepository, FileRepository

logger = logging.getLogger(__name__)

movie_repo = MovieRepository()
series_repo = SeriesRepository()
file_repo = FileRepository()

async def run_health_checks() -> Dict[str, Any]:
    """Runs a series of health checks on the system components and data integrity."""
    report = {
        "status": "healthy",
        "timestamp": None,
        "checks": {
            "database_connection": {"status": "unknown"},
            "movie_data_integrity": {"status": "unknown", "issues": []},
            "series_data_integrity": {"status": "unknown", "issues": []},
            "duplicate_files": {"status": "unknown", "issues": []},
            "telegram_api_status": {"status": "unknown"}
        }
    }
    report['timestamp'] = datetime.utcnow().isoformat()

    # 1. Check MongoDB Connection
    await _check_database_connection(report['checks']['database_connection'])
    if report['checks']['database_connection']['status'] != 'healthy':
        report['status'] = 'unhealthy'
        return report # Critical failure, stop further checks

    # 2. Check Movie Data Integrity
    await _check_movie_data_integrity(report['checks']['movie_data_integrity'])
    if report['checks']['movie_data_integrity']['issues']:
        report['status'] = 'unhealthy'
    
    # 3. Check Series Data Integrity
    await _check_series_data_integrity(report['checks']['series_data_integrity'])
    if report['checks']['series_data_integrity']['issues']:
        report['status'] = 'unhealthy'

    # 4. Check for Duplicate Files
    await _check_duplicate_files(report['checks']['duplicate_files'])
    if report['checks']['duplicate_files']['issues']:
        report['status'] = 'unhealthy'

    # 5. Check Telegram API (placeholder - requires Bot object)
    # For a real check, you'd need to try making a simple API call (e.g., get_me())
    report['checks']['telegram_api_status'] = {"status": "healthy", "message": "Direct API check not implemented in mock."} # Placeholder

    return report

async def _check_database_connection(check_result: Dict[str, Any]) -> None:
    """Checks if MongoDB is reachable and responsive."""
    if not MongoManager.is_initialized():
        check_result['status'] = 'unhealthy'
        check_result['message'] = 'MongoDB Manager not initialized.'
        return
    try:
        # The ping command is a lightweight way to check if the server is up
        await MongoManager.get_client().admin.command('ping')
        check_result['status'] = 'healthy'
        check_result['message'] = 'MongoDB connection successful.'
    except Exception as e:
        check_result['status'] = 'unhealthy'
        check_result['message'] = f'MongoDB connection failed: {e}'
        logger.error(f"MongoDB health check failed: {e}")

async def _check_movie_data_integrity(check_result: Dict[str, Any]) -> None:
    """Checks for common movie data issues (e.g., missing poster, missing qualities)."""
    issues = []
    movies_cursor = movie_repo.collection.find({})
    async for movie in movies_cursor:
        if not movie.get('poster_file_id'):
            issues.append(f"Movie '{movie.get('title_arabic', movie.get('_id'))}' ({movie['_id']}) is missing a poster.")
        
        # Check if movie has any associated files/qualities
        movie_files = await file_repo.get_files_for_content(movie['_id'])
        if not movie_files:
            issues.append(f"Movie '{movie.get('title_arabic', movie.get('_id'))}' ({movie['_id']}) has no associated files/qualities.")
        
        if not movie.get('title_arabic') and not movie.get('title_english'):
            issues.append(f"Movie '{movie['_id']}' is missing both Arabic and English titles.")
        
        if not movie.get('genres') or len(movie['genres']) == 0:
            issues.append(f"Movie '{movie.get('title_arabic', movie.get('_id'))}' ({movie['_id']}) is missing genre information.")

    if issues:
        check_result['status'] = 'unhealthy'
        check_result['issues'] = issues
    else:
        check_result['status'] = 'healthy'
        check_result['message'] = 'Movie data integrity looks good.'

async def _check_series_data_integrity(check_result: Dict[str, Any]) -> None:
    """Checks for common series data issues."""
    issues = []
    series_cursor = series_repo.collection.find({})
    async for series in series_cursor:
        if not series.get('poster_file_id'):
            issues.append(f"Series '{series.get('title_arabic', series.get('_id'))}' ({series['_id']}) is missing a poster.")
        
        if not series.get('seasons') or len(series['seasons']) == 0:
            issues.append(f"Series '{series.get('title_arabic', series.get('_id'))}' ({series['_id']}) has no seasons.")
        else:
            for season in series['seasons']:
                if not season.get('episodes') or len(season['episodes']) == 0:
                    issues.append(f"Series '{series.get('title_arabic', series.get('_id'))}' ({series['_id']}) season {season.get('season_number')} has no episodes.")
                else:
                    for episode in season['episodes']:
                        episode_files = await file_repo.get_files_for_content(episode['_id'])
                        if not episode_files:
                            issues.append(f"Episode '{episode.get('title_arabic', episode.get('_id'))}' (S{season.get('season_number')}E{episode.get('episode_number')}) is missing associated files.")

    if issues:
        check_result['status'] = 'unhealthy'
        check_result['issues'] = issues
    else:
        check_result['status'] = 'healthy'
        check_result['message'] = 'Series data integrity looks good.'

async def _check_duplicate_files(check_result: Dict[str, Any]) -> None:
    """Checks for duplicate file_unique_id in the database."""
    issues = []
    # Aggregate to find duplicate file_unique_ids
    pipeline = [
        {"$group": {"_id": "$file_unique_id", "count": {"$sum": 1}, "file_ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicate_files = await file_repo.collection.aggregate(pipeline).to_list(length=None)

    for dup in duplicate_files:
        issues.append(f"Duplicate file_unique_id '{dup['_id']}' found in {dup['count']} records. Internal file_ids: {dup['file_ids']}")

    if issues:
        check_result['status'] = 'unhealthy'
        check_result['issues'] = issues
    else:
        check_result['status'] = 'healthy'
        check_result['message'] = 'No duplicate files (by unique_id) found.'


# Needed for timestamp
from datetime import datetime
