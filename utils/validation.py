from typing import Any, Dict
import re

def validate_movie_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and cleans movie data, returning a dictionary of errors if any."""
    errors = {}
    if not data.get('title_arabic') and not data.get('title_english'):
        errors['title'] = 'At least one of Arabic or English title is required.'
    
    if data.get('year') and not isinstance(data['year'], int):
        try: 
            data['year'] = int(data['year'])
        except ValueError:
            errors['year'] = 'Year must be an integer.'

    if data.get('genres') and not isinstance(data['genres'], list):
        errors['genres'] = 'Genres must be a list of strings.'
    elif data.get('genres'):
        data['genres'] = [str(g).strip() for g in data['genres'] if str(g).strip()]

    if data.get('rating'):
        try:
            data['rating'] = float(data['rating'])
            if not (0 <= data['rating'] <= 10):
                errors['rating'] = 'Rating must be between 0 and 10.'
        except ValueError:
            errors['rating'] = 'Rating must be a number.'

    # Add more validations for other fields as needed
    return errors

def validate_telegram_init_data(init_data: str) -> bool:
    """Placeholder for Telegram InitData validation function.
    This should be implemented with proper HMAC-SHA256 signature checking.
    For now, it's a dummy.
    """
    # The actual validation logic for Telegram InitData is complex and involves HMAC-SHA256.
    # It's implemented in api/auth.py for server-side validation.
    # This dummy function is just to prevent errors in other modules that might call it.
    # DO NOT use this for real security validation.
    return True

def is_valid_telegram_id(telegram_id: Any) -> bool:
    """Checks if the given value is a valid Telegram ID (integer)."""
    return isinstance(telegram_id, int) and telegram_id > 0

def is_valid_mongo_id(mongo_id: Any) -> bool:
    """Checks if the given value is a valid MongoDB ObjectId string (or UUID string)."""
    if not isinstance(mongo_id, str): return False
    # Check for UUID format (our internal IDs are UUIDs)
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', mongo_id, re.IGNORECASE))

