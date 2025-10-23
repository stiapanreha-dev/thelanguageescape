"""
Activity tracking middleware
Updates user's last_activity timestamp on every interaction
"""
import logging
import datetime as dt_module
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User

logger = logging.getLogger(__name__)


class ActivityMiddleware(BaseMiddleware):
    """
    Middleware to track user activity
    Updates last_activity timestamp for every user interaction
    """

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process update and track activity

        Args:
            handler: Next handler in chain
            event: Update event (Message or CallbackQuery)
            data: Additional data

        Returns:
            Handler result
        """
        # Get user_id
        user_id = event.from_user.id

        # Get session from data
        session: AsyncSession = data.get('session')

        if session:
            try:
                # Update last_activity
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    # Use naive datetime (without timezone) to match DB column type
                    user.last_activity = dt_module.datetime.utcnow()
                    await session.commit()
                    logger.debug(f"Updated activity for user {user_id}")

            except Exception as e:
                logger.error(f"Error updating activity for user {user_id}: {e}")
                # Don't block the handler if activity update fails
                pass

        # Continue with handler
        return await handler(event, data)
