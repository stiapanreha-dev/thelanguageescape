"""
Admin middleware and decorators
Check if user is admin before allowing access to admin functions
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_TELEGRAM_ID
from bot.database.models import User

logger = logging.getLogger(__name__)


class AdminMiddleware(BaseMiddleware):
    """
    Middleware to check admin status
    Injects is_admin into handler data
    """

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Check if user is admin"""

        user_id = event.from_user.id
        session: AsyncSession = data.get('session')

        # Check if user is configured admin (from .env)
        is_config_admin = ADMIN_TELEGRAM_ID and user_id == ADMIN_TELEGRAM_ID

        # Check if user is marked as admin in database
        is_db_admin = False
        if session:
            try:
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    is_db_admin = user.is_admin

                    # Auto-promote config admin in database
                    if is_config_admin and not user.is_admin:
                        user.is_admin = True
                        await session.commit()
                        logger.info(f"User {user_id} promoted to admin via config")

            except Exception as e:
                logger.error(f"Error checking admin status: {e}")

        # User is admin if either config or database says so
        data['is_admin'] = is_config_admin or is_db_admin

        return await handler(event, data)


def admin_required(func):
    """
    Decorator to require admin access
    Usage:
        @router.message(Command("admin"))
        @admin_required
        async def admin_panel(message: Message, is_admin: bool):
            ...
    """
    import inspect

    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        is_admin = kwargs.get('is_admin', False)

        if not is_admin:
            if isinstance(event, Message):
                await event.answer("❌ Access denied. Admin only.")
            else:  # CallbackQuery
                await event.answer("❌ Access denied. Admin only.", show_alert=True)

            logger.warning(f"Non-admin user {event.from_user.id} tried to access admin function")
            return

        # Filter kwargs to only pass parameters that the function expects
        sig = inspect.signature(func)
        filtered_kwargs = {
            k: v for k, v in kwargs.items()
            if k in sig.parameters
        }

        return await func(event, *args, **filtered_kwargs)

    return wrapper


async def check_is_admin(telegram_id: int, session: AsyncSession = None) -> bool:
    """
    Helper function to check if user is admin

    Args:
        telegram_id: Telegram user ID
        session: Database session (optional)

    Returns:
        True if user is admin
    """
    # Check config admin
    if ADMIN_TELEGRAM_ID and telegram_id == ADMIN_TELEGRAM_ID:
        return True

    # Check database
    if session:
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user and user.is_admin:
                return True
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")

    return False


async def promote_user_to_admin(telegram_id: int, session: AsyncSession) -> bool:
    """
    Promote user to admin

    Args:
        telegram_id: Telegram user ID to promote
        session: Database session

    Returns:
        True if successful
    """
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {telegram_id} not found for promotion")
            return False

        user.is_admin = True
        await session.commit()

        logger.info(f"✅ User {telegram_id} promoted to admin")
        return True

    except Exception as e:
        logger.error(f"Error promoting user to admin: {e}")
        await session.rollback()
        return False


async def demote_admin(telegram_id: int, session: AsyncSession) -> bool:
    """
    Remove admin status from user

    Args:
        telegram_id: Telegram user ID to demote
        session: Database session

    Returns:
        True if successful
    """
    # Don't allow demoting config admin
    if ADMIN_TELEGRAM_ID and telegram_id == ADMIN_TELEGRAM_ID:
        logger.warning(f"Attempted to demote config admin {telegram_id}")
        return False

    try:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {telegram_id} not found for demotion")
            return False

        user.is_admin = False
        await session.commit()

        logger.info(f"User {telegram_id} demoted from admin")
        return True

    except Exception as e:
        logger.error(f"Error demoting admin: {e}")
        await session.rollback()
        return False
