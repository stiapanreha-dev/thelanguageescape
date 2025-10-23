"""
User action logging middleware
Logs all user actions for analytics and debugging
Can be enabled/disabled via LOG_USER_ACTIONS in .env
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from bot.config import LOG_USER_ACTIONS

logger = logging.getLogger(__name__)


class UserActionLogger(BaseMiddleware):
    """
    Middleware to log all user actions
    Controlled by LOG_USER_ACTIONS environment variable
    """

    def __init__(self):
        super().__init__()
        self.enabled = LOG_USER_ACTIONS
        if self.enabled:
            logger.info("✅ User action logging enabled")
        else:
            logger.info("⚠️  User action logging disabled")

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Log user action before processing

        Args:
            handler: Next handler in chain
            event: Update event
            data: Additional data

        Returns:
            Handler result
        """
        # Only log if enabled
        if not self.enabled:
            return await handler(event, data)

        # Extract user info
        user = None
        action_type = None
        action_data = {}

        # Determine event type
        if event.message:
            user = event.message.from_user
            action_type = "message"

            if event.message.text:
                action_data['text'] = event.message.text[:100]  # First 100 chars
            elif event.message.photo:
                action_data['type'] = 'photo'
            elif event.message.voice:
                action_data['type'] = 'voice'
                action_data['duration'] = event.message.voice.duration
            elif event.message.document:
                action_data['type'] = 'document'
            elif event.message.video:
                action_data['type'] = 'video'

        elif event.callback_query:
            user = event.callback_query.from_user
            action_type = "callback"
            action_data['data'] = event.callback_query.data

        # Log the action
        if user and action_type:
            log_message = self._format_log_message(user, action_type, action_data)
            logger.info(log_message)

        # Continue with handler
        return await handler(event, data)

    def _format_log_message(
        self,
        user,
        action_type: str,
        action_data: Dict[str, Any]
    ) -> str:
        """
        Format log message with user action details

        Args:
            user: Telegram user object
            action_type: Type of action (message/callback)
            action_data: Additional action data

        Returns:
            Formatted log message
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        user_info = f"User {user.id}"
        if user.username:
            user_info += f" (@{user.username})"
        if user.first_name:
            user_info += f" [{user.first_name}]"

        action_info = f"Action: {action_type}"

        # Add specific action details
        details = []
        if action_type == "message":
            if 'text' in action_data:
                details.append(f"text='{action_data['text']}'")
            elif 'type' in action_data:
                details.append(f"type={action_data['type']}")
                if 'duration' in action_data:
                    details.append(f"duration={action_data['duration']}s")

        elif action_type == "callback":
            if 'data' in action_data:
                details.append(f"data='{action_data['data']}'")

        details_str = ", ".join(details) if details else "no details"

        return f"[{timestamp}] {user_info} | {action_info} | {details_str}"


# Singleton instance
user_action_logger = UserActionLogger()
