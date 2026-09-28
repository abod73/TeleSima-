from typing import List, Dict, Any
import logging
from telegram import Bot

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Bot, public_channel_id: int = None):
        self.bot = bot
        self.public_channel_id = public_channel_id

    async def send_new_content_notification(self, content_type: str, content_data: Dict[str, Any]) -> None:
        """Sends a notification when new content (movie/series) is added."""
        if content_type == 'movie':
            message_text = f"🎬 New Movie Added: {content_data.get('title_arabic') or content_data.get('title_english')} ({content_data.get('year')})\nSynopsis: {content_data.get('story', '')[:150]}...\nWatch now: [Link to Mini App/Movie Page]"
        elif content_type == 'series':
            message_text = f"📺 New Series Added: {content_data.get('title_arabic') or content_data.get('title_english')} ({content_data.get('year')})\nSynopsis: {content_data.get('story', '')[:150]}...\nWatch now: [Link to Mini App/Series Page]"
        else:
            logger.warning(f"Unknown content type for notification: {content_type}")
            return

        # Send to a public channel if configured
        if self.public_channel_id:
            try:
                await self.bot.send_message(chat_id=self.public_channel_id, text=message_text, parse_mode='Markdown')
                logger.info(f"Sent new content notification to public channel {self.public_channel_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to public channel: {e}")

        # In a real system, also send to subscribed users (requires user subscription management)

    async def send_upcoming_release_notification(self, upcoming_data: Dict[str, Any], user_ids: List[int]) -> None:
        """Sends a notification to users about an upcoming release they are following."""
        message_text = f"🔔 Upcoming Release Alert: {upcoming_data.get('title_arabic') or upcoming_data.get('title_english')} is coming soon on {upcoming_data.get('release_date')}."

        for user_id in user_ids:
            try:
                await self.bot.send_message(chat_id=user_id, text=message_text)
                logger.info(f"Sent upcoming release notification to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send upcoming release notification to user {user_id}: {e}")

    async def send_health_alert(self, admin_ids: List[int], alert_message: str) -> None:
        """Sends an alert message to administrators about a system health issue."""
        full_message = f"🚨 Teli Cinema Health Alert 🚨\n\n{alert_message}"
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=full_message)
                logger.info(f"Sent health alert to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send health alert to admin {admin_id}: {e}")
