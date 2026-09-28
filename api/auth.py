import os
import hashlib
import hmac
import json
import time
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Any, Optional

# NOTE: In a production Flask app, it's safer to get BOT_TOKEN directly from config/env
# instead of relying on os.getenv() within the request context repeatedly.
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(',') if admin_id]

def validate_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """Validates Telegram Mini App initData.

    The validation logic is based on Telegram's official documentation:
    https://core.telegram.org/bots/webapps#checking-authorization
    """
    if not BOT_TOKEN:
        print("BOT_TOKEN is not set, cannot validate Telegram initData.")
        return None

    data_check_string = []
    parsed_data = {} # To store parsed key-value pairs

    # Parse init_data string into a dictionary and prepare data_check_string
    pairs = init_data.split('&')
    for pair in pairs:
        if '=' not in pair:
            continue
        key, value = pair.split('=', 1)
        # Decode URL-encoded components
        decoded_key = bytes(key, 'utf-8').decode('unicode_escape').replace('%2D', '-') # handle %2D
        decoded_value = bytes(value, 'utf-8').decode('unicode_escape').replace('%2D', '-') # handle %2D
        
        parsed_data[decoded_key] = decoded_value
        if decoded_key != 'hash':
            data_check_string.append(f"{decoded_key}={decoded_value}")

    data_check_string.sort()
    data_check_string_joined = '\n'.join(data_check_string)

    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string_joined.encode(), hashlib.sha256).hexdigest()

    if calculated_hash == parsed_data.get('hash'):
        # Check exp date if 'auth_date' is present
        if 'auth_date' in parsed_data:
            auth_date = int(parsed_data['auth_date'])
            # Consider initData valid for, e.g., 24 hours (86400 seconds)
            if time.time() - auth_date > 86400:
                print("Telegram initData expired.")
                return None
        
        # If 'user' field is present, parse it from JSON
        if 'user' in parsed_data:
            try:
                parsed_data['user'] = json.loads(parsed_data['user'])
            except json.JSONDecodeError:
                print("Could not decode user data from initData.")
                return None
        return parsed_data
    else:
        print("Telegram initData hash validation failed.")
        return None

def telegram_web_app_auth(f):
    """Decorator for authenticating requests from Telegram Web Apps."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data')
        if not init_data:
            return jsonify({'error': 'Unauthorized', 'message': 'X-Telegram-Init-Data header missing.'}), 401
        
        auth_data = validate_telegram_init_data(init_data)
        if not auth_data:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid or expired Telegram InitData.'}), 401
        
        # Add authenticated user info to request context if needed
        request.telegram_user = auth_data.get('user')
        request.auth_data = auth_data
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for checking if the authenticated Telegram user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'telegram_user') or not request.telegram_user:
            # This should ideally be caught by telegram_web_app_auth first
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
        
        user_id = request.telegram_user.get('id')
        if user_id not in ADMIN_IDS:
            return jsonify({'error': 'Forbidden', 'message': 'Admin access required.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function
