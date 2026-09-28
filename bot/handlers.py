from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and keyboard with Mini App button."""
    # Telegram Mini App URL (replace with your actual deployed URL)
    # The URL will be constructed based on your WEBHOOK_URL + '/'
    mini_app_url = context.bot_data.get('mini_app_url', 'https://your-webhook-url.com/')

    keyboard = [
        [InlineKeyboardButton("🚀 Open Teli Cinema", web_app=WebAppInfo(url=mini_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome to Teli Cinema! Explore movies and series directly within Telegram.",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles general text messages."""
    # For now, just echo or provide a generic response
    if update.message and update.message.text:
        response_text = f"You said: {update.message.text}. I'm a bot under development!"
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("I received something, but I can only process text for now.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    print(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text(
            'An error occurred while processing your request. Please try again later.'
        )
