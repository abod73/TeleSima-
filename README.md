# Teli Cinema / تلي سيما

Teli Cinema is a movie and series streaming platform built using Python (Flask, python-telegram-bot) and MongoDB, with a Telegram Mini App frontend.

## Features

*   **Telegram Bot Integration**: Indexing from private channels, admin commands.
*   **REST API**: For managing movies, series, search, and user-specific data.
*   **Telegram Mini App**: Modern, mobile-first, responsive, RTL-supported frontend.
*   **Robust Content Management**: Handles movies and series with multiple qualities, stable `movie_id` and `episode_id`.
*   **Advanced Search**: Arabic/English, partial, aliases, typo tolerance, natural language queries.
*   **User Features**: Favorites, Watch History, Recommendations, Ratings, Comments.
*   **Admin Dashboard**: Comprehensive management of content, users, and system health.
*   **Health Checks**: Detects data inconsistencies and system issues.
*   **Security**: `initData` validation, authentication, authorization, rate limiting.

## Project Structure

```
Teli-Cinema/
│
├── main.py                # Main Flask application and Telegram bot entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── README.md              # Project overview and setup guide
├── .gitignore             # Files and directories to ignore in Git
│
├── static/                # Frontend files for Telegram Mini App
│   ├── app.html
│   ├── app.js
│   └── styles.css
│
├── bot/                   # Telegram Bot logic
│   ├── __init__.py
│   ├── handlers.py        # General message and command handlers
│   ├── admin.py           # Admin-specific bot commands
│   ├── indexer.py         # Logic for indexing Telegram channel posts
│   └── parser.py          # Caption parsing logic for movie/series data
│
├── database/              # Database interaction layer
│   ├── __init__.py
│   ├── mongodb.py         # MongoDB connection and client management
│   ├── indexes.py         # MongoDB index creation
│   └── repositories.py    # Data access layer for different collections
│
├── api/                   # REST API endpoints
│   ├── __init__.py
│   ├── routes.py          # General API routes (movies, series, search)
│   ├── auth.py            # API authentication and authorization utilities
│   └── admin.py           # Admin-specific API routes
│
├── services/              # Business logic and services
│   ├── __init__.py
│   ├── search.py          # Movie/series search logic
│   ├── recommendations.py # Recommendation engine
│   ├── notifications.py   # Notification handling
│   ├── health.py          # System health check logic
│   └── image_search.py    # Image search (e.g., for posters)
│
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── normalization.py   # Text normalization (e.g., Arabic text)
│   ├── validation.py      # Data validation utilities
│   └── helpers.py         # General helper functions
│
└── tests/                 # Unit and integration tests (placeholder)
    └── __init__.py
```

## Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/Teli-Cinema.git
    cd Teli-Cinema
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Copy `.env.example` to `.env` and fill in your details.
    ```bash
    cp .env.example .env
    ```
    *   `BOT_TOKEN`: Your Telegram Bot API token.
    *   `BOT_USERNAME`: Your bot's username.
    *   `MONGODB_URI`: Connection string for your MongoDB Atlas cluster or local MongoDB.
    *   `WEBHOOK_URL`: The public URL of your deployed application (e.g., `https://your-app-name.replit.app`). This is crucial for Telegram webhooks.
    *   `WEBHOOK_PATH`: The path Telegram will send updates to (e.g., `/webhook`).
    *   `PUBLIC_POST_CHANNEL`: The Telegram channel ID where movies/series are shared publicly (if applicable).
    *   `ALLOWED_CHANNEL_IDS`: Comma-separated IDs of private channels from which the bot should index content.
    *   `ADMIN_IDS`: Comma-separated Telegram user IDs of your administrators.
    *   `FLASK_DEBUG`: Set to `True` for development, `False` for production.
    *   `FLASK_SECRET_KEY`: A strong, random secret key for Flask sessions.

5.  **Initialize MongoDB Indexes**:
    Before running the application, you should run a script or command to ensure all MongoDB indexes are created. (This functionality is implemented in `database/indexes.py` and would be called on deployment).

## Running the Application (On your Hosting Provider)

This application is designed to be deployed using a WSGI server like Gunicorn or on platforms like Replit, Vercel, or a VPS.

**Example with Gunicorn (for VPS/Cloud Hosting)**:
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 main:app
```

**Important Notes for Deployment**:

*   Ensure your `WEBHOOK_URL` and `WEBHOOK_PATH` in `.env` are correctly configured and accessible from Telegram servers.
*   Use a process manager (like `systemd` or `Supervisor`) to keep Gunicorn running.
*   For `python-telegram-bot` webhook mode, the `main.py` handles setting the webhook. Ensure the Flask application is publicly accessible.

## Telegram Mini App

The frontend is located in the `static/` directory. The `app.html`, `app.js`, and `styles.css` files constitute the Mini App. The Mini App relies on the Telegram WebApp API and communicates with the backend REST API.

## Admin Commands (via Telegram Bot)

Admins (defined in `ADMIN_IDS` in `.env`) can use commands like:

*   `/start`
*   `/stats`
*   `/addchannel <channel_id>`
*   `/delchannel <channel_id>`
*   `/channels`
*   `/autodelete <on/off>`
*   `/addupcoming <movie_title> <release_date>`
*   `/delupcoming <upcoming_id>`
*   `/release <upcoming_id>`
*   `/delmovie <movie_id>`

## Health Checks

The `services/health.py` module contains logic to detect issues like:

*   Movies without posters or qualities.
*   Duplicate files.
*   Missing metadata.
*   Invalid Telegram messages.
*   MongoDB or Telegram API failures.

This can be triggered via an admin command or an API endpoint (`/api/admin/health-report`).

## Contributing

(Guidelines for contribution would go here)

## License

(License information would go here)
