import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect, url_for
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ApplicationBuilder

# Load environment variables from .env file
load_dotenv()

# Import blueprints and other modules
from api.routes import api_bp
from api.admin import admin_api_bp
from bot.handlers import start, handle_message
from bot.admin import setup_admin_handlers
from database.mongodb import MongoManager
from utils.validation import validate_telegram_init_data

# --- Flask App Configuration ---
app = Flask(__name__)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(admin_api_bp, url_prefix='/api/admin')

# --- Telegram Bot Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
BOT_USERNAME = os.getenv("BOT_USERNAME", "TeliCinemaBot")
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(',') if admin_id]

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    MongoManager.initialize(MONGODB_URI)

# Initialize Telegram Bot Application
def setup_telegram_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN is not set. Telegram bot will not be initialized.")
        return None

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Admin Handlers
    setup_admin_handlers(application)

    # Set webhook (if WEBHOOK_URL is provided)
    if WEBHOOK_URL:
        application.bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
        print(f"Telegram Webhook set to: {WEBHOOK_URL}{WEBHOOK_PATH}")
    else:
        print("WEBHOOK_URL not set. Bot will run in polling mode (not recommended for production on some hosts).")

    return application

telegram_app = setup_telegram_bot()

# --- Flask Routes for Mini App and Webhook ---
@app.route('/')
def index():
    # Mini App entry point, redirect to app.html or serve it directly
    # In a real deployment, you might serve `app.html` directly from `static`
    return redirect(url_for('static_files', filename='app.html'))

@app.route(WEBHOOK_PATH, methods=['POST'])
async def telegram_webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
    return jsonify({'status': 'ok'})

@app.route('/health')
def health_check_flask():
    # Basic health check for the Flask app
    db_status = 'disconnected'
    if MongoManager.is_initialized():
        try:
            MongoManager.get_client().admin.command('ping')
            db_status = 'connected'
        except Exception:
            db_status = 'error'
    return jsonify({'status': 'ok', 'database': db_status})

# Serve static files for Mini App
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)


if __name__ == '__main__':
    # This block is for local development without webhook. Not for production deployment.
    # In production, use Gunicorn or similar WSGI server.
    print("\n--- Teli Cinema Application Started ---")
    print("Flask app is running.")
    if not WEBHOOK_URL and telegram_app:
        print("Running Telegram bot in polling mode (for local testing).")
        # In a real environment, you would run application.run_polling()
        # in a separate thread or process, or configure a webhook.
    print("Open your browser to http://127.0.0.1:5000 (or your configured port).")
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true", host='0.0.0.0', port=5000)
