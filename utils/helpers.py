from datetime import datetime
import json
from typing import Any, Dict, List

def get_current_timestamp() -> datetime:
    """Returns the current UTC datetime."""
    return datetime.utcnow()

def json_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Helper to create a Flask-style JSON response."""
    # In a real Flask app, you'd use jsonify directly, but this is for generic helpers
    return {'data': data, 'status': status_code}

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely gets a value from a dictionary, handling missing keys gracefully."""
    return data.get(key, default)

def paginate_list(data_list: List[Any], page: int, per_page: int) -> Dict[str, Any]:
    """Paginates a list of data."""
    start = (page - 1) * per_page
    end = start + per_page
    paginated_data = data_list[start:end]
    return {
        'data': paginated_data,
        'page': page,
        'per_page': per_page,
        'total': len(data_list),
        'total_pages': (len(data_list) + per_page - 1) // per_page
    }

def format_duration(minutes: int) -> str:
    """Formats duration in minutes to 'Xh Ym' string."""
    if not isinstance(minutes, int) or minutes < 0:
        return "N/A"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if hours > 0 and remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    elif hours > 0:
        return f"{hours}h"
    elif remaining_minutes > 0:
        return f"{remaining_minutes}m"
    return "0m"
