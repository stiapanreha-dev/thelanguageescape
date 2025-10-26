"""
Reminder service - handles automated reminders for inactive users
Uses APScheduler to check for inactive users and send motivational messages
"""
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
import pytz

from bot.database.models import User, Reminder
from bot.config import COURSE_DAYS, TIMEZONE

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing user reminders"""

    # Reminder messages for different attempts
    REMINDER_MESSAGES = [
        # First reminder (after 24h)
        """
🔔 **Hey there, Subject X!**

You've been inactive for 24 hours. The simulation is waiting... Don't let your progress slip away!

🎯 **Your mission:** Continue your escape journey
🔑 **Your progress:** Every day brings you closer to freedom

Ready to continue? /day
""",
        # Second reminder (after 48h)
        """
⚠️ **Subject X, are you still there?**

The simulation has noticed your absence. 48 hours have passed...

⏰ **Time is running out!**
Your secret code is incomplete: `{liberation_code}`

Don't give up now! Every day counts.

Continue your mission: /day
""",
        # Third reminder (after 72h)
        """
🚨 **FINAL NOTICE, Subject X!**

72 hours of inactivity. The system is about to lock you out permanently...

🔴 **This is your last chance!**
💪 **You've come this far** - {completed_days} days completed
🔑 **Don't lose your progress**: `{liberation_code}`

The escape route is still open... but not for long.

**ACT NOW:** /day

_Remember: Only 3 reminders per user. This is your last one._
"""
    ]

    MAX_REMINDERS = 3
    INACTIVITY_THRESHOLD_HOURS = 24

    def __init__(self, bot: Bot):
        """
        Initialize reminder service

        Args:
            bot: Bot instance for sending messages
        """
        self.bot = bot

    async def get_inactive_users(self, session: AsyncSession) -> List[User]:
        """
        Get list of users who are inactive and need reminders

        Args:
            session: Database session

        Returns:
            List of inactive users
        """
        threshold = datetime.utcnow() - timedelta(hours=self.INACTIVITY_THRESHOLD_HOURS)

        # Get users who:
        # - Have paid access
        # - Haven't completed the course
        # - Last activity was more than 24h ago
        # - Haven't received max reminders yet
        result = await session.execute(
            select(User).where(
                and_(
                    User.has_access == True,
                    User.course_completed_at.is_(None),
                    User.last_activity < threshold,
                    User.current_day > 0,  # Started the course
                    User.current_day <= COURSE_DAYS  # Not finished
                )
            )
        )

        users = result.scalars().all()

        # Filter by reminder count
        inactive_users = []
        for user in users:
            reminder_count = await self.get_reminder_count(session, user.id)
            if reminder_count < self.MAX_REMINDERS:
                inactive_users.append(user)

        return inactive_users

    async def get_reminder_count(self, session: AsyncSession, user_id: int) -> int:
        """
        Get number of reminders sent to user

        Args:
            session: Database session
            user_id: User ID

        Returns:
            Number of reminders sent
        """
        result = await session.execute(
            select(Reminder).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.sent == True
                )
            )
        )
        reminders = result.scalars().all()
        return len(reminders)

    async def get_hours_since_last_activity(self, user: User) -> int:
        """
        Calculate hours since last user activity

        Args:
            user: User object

        Returns:
            Hours since last activity
        """
        if not user.last_activity:
            return 0

        delta = datetime.utcnow() - user.last_activity
        return int(delta.total_seconds() / 3600)

    def get_reminder_message(
        self,
        reminder_attempt: int,
        user: User
    ) -> str:
        """
        Get appropriate reminder message based on attempt number

        Args:
            reminder_attempt: Which reminder this is (1, 2, or 3)
            user: User object for personalization

        Returns:
            Formatted reminder message
        """
        if reminder_attempt < 1 or reminder_attempt > len(self.REMINDER_MESSAGES):
            reminder_attempt = 1

        message = self.REMINDER_MESSAGES[reminder_attempt - 1]

        # Format with user data
        message = message.format(
            liberation_code=user.liberation_code or '___________',
            completed_days=user.completed_days
        )

        return message

    async def send_reminder(
        self,
        session: AsyncSession,
        user: User
    ) -> bool:
        """
        Send reminder to user

        Args:
            session: Database session
            user: User to send reminder to

        Returns:
            True if reminder sent successfully
        """
        try:
            # Check if current time is within allowed hours (12:00-18:00)
            tz = pytz.timezone(TIMEZONE)
            now = datetime.now(tz)
            current_hour = now.hour

            if not (12 <= current_hour < 18):
                logger.info(f"⏰ Skipping reminder for user {user.telegram_id}: outside allowed hours (current: {current_hour}:00, allowed: 12:00-18:00)")
                return False

            # Get reminder count to determine which message to send
            reminder_count = await self.get_reminder_count(session, user.id)

            # Don't send if max reminders reached
            if reminder_count >= self.MAX_REMINDERS:
                logger.info(f"User {user.telegram_id} has reached max reminders")
                return False

            # Get appropriate message
            reminder_attempt = reminder_count + 1
            message = self.get_reminder_message(reminder_attempt, user)

            # Send message
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown"
            )

            # Save reminder to database
            reminder = Reminder(
                user_id=user.id,
                day_number=user.current_day,
                reminder_type='inactive',
                message_text=message[:500],  # Store first 500 chars
                sent=True,
                sent_at=datetime.utcnow()
            )
            session.add(reminder)
            await session.commit()

            logger.info(f"✅ Sent reminder #{reminder_attempt} to user {user.telegram_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending reminder to user {user.telegram_id}: {e}")
            return False

    async def check_and_send_reminders(self, session: AsyncSession):
        """
        Check for inactive users and send reminders

        This is the main scheduled job function

        Args:
            session: Database session
        """
        logger.info("🔍 Checking for inactive users...")

        inactive_users = await self.get_inactive_users(session)

        if not inactive_users:
            logger.info("No inactive users found")
            return

        logger.info(f"Found {len(inactive_users)} inactive users")

        # Send reminders
        sent_count = 0
        for user in inactive_users:
            hours_inactive = await self.get_hours_since_last_activity(user)
            logger.info(f"User {user.telegram_id}: inactive for {hours_inactive}h")

            success = await self.send_reminder(session, user)
            if success:
                sent_count += 1

        logger.info(f"✅ Sent {sent_count}/{len(inactive_users)} reminders")

    async def reset_reminders(self, session: AsyncSession, user_id: int):
        """
        Reset reminder count when user becomes active again

        Args:
            session: Database session
            user_id: User ID
        """
        # Mark all unsent reminders as canceled
        result = await session.execute(
            select(Reminder).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.sent == False
                )
            )
        )
        reminders = result.scalars().all()

        for reminder in reminders:
            session.delete(reminder)

        await session.commit()
        logger.info(f"Reset reminders for user {user_id}")


# Global reminder service instance will be initialized in main.py with bot
reminder_service = None


def initialize_reminder_service(bot: Bot):
    """
    Initialize global reminder service

    Args:
        bot: Bot instance
    """
    global reminder_service
    reminder_service = ReminderService(bot)
    logger.info("✅ Reminder service initialized")
