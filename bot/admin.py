from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import os

ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "").split(',') if admin_id]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user and is_admin(update.effective_user.id):
            return await func(update, context, *args, **kwargs)
        else:
            if update.effective_message:
                await update.effective_message.reply_text("You are not authorized to use this command.")
            return
    return wrapper

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends bot statistics (admin only)."""
    # Placeholder for actual stats logic
    await update.message.reply_text("Bot statistics: (placeholder for actual data)")

@admin_only
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a channel to the allowed indexing list (admin only)."""
    if not context.args:
        await update.message.reply_text("Usage: /addchannel <channel_id>")
        return
    channel_id = context.args[0]
    # Implement logic to add channel_id to database or config
    await update.message.reply_text(f"Channel {channel_id} added (placeholder).")

# Placeholder for other admin commands
@admin_only
async def del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Del channel (placeholder).")

@admin_only
async def channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Channels list (placeholder).")

@admin_only
async def autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Autodelete (placeholder).")

@admin_only
async def add_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Add upcoming (placeholder).")

@admin_only
async def del_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Del upcoming (placeholder).")

@admin_only
async def release(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Release (placeholder).")

@admin_only
async def del_movie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Del movie (placeholder).")

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("delchannel", del_channel))
    application.add_handler(CommandHandler("channels", channels))
    application.add_handler(CommandHandler("autodelete", autodelete))
    application.add_handler(CommandHandler("addupcoming", add_upcoming))
    application.add_handler(CommandHandler("delupcoming", del_upcoming))
    application.add_handler(CommandHandler("release", release))
    application.add_handler(CommandHandler("delmovie", del_movie))
