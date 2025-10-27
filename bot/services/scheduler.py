"""
Scheduler service - manages scheduled tasks
Uses APScheduler for running periodic jobs
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.database import async_session_maker

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks"""

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = AsyncIOScheduler(
            timezone='Europe/Moscow',  # UTC+3
            job_defaults={
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 600  # 10 minutes grace period
            }
        )

        self.is_running = False

    async def check_reminders_job(self):
        """
        Job to check and send reminders to inactive users
        Runs every hour
        """
        try:
            logger.info("🔔 Running reminder check job...")

            # Import reminder_service at runtime to get current value
            from bot.services.reminders import reminder_service

            async with async_session_maker() as session:
                if reminder_service:
                    await reminder_service.check_and_send_reminders(session)
                else:
                    logger.error("Reminder service not initialized")

        except Exception as e:
            logger.error(f"Error in reminder check job: {e}")

    async def unlock_next_days_job(self):
        """
        Unlock next day for users who completed previous day
        Runs every hour (checks each user's local timezone)
        Sends notification to users about new day availability (once per day, 12:00-18:00 user's local time)
        """
        try:
            logger.info("🔓 Running next day unlock job...")

            from bot.database.models import User, Progress
            from bot.services.reminders import reminder_service
            from sqlalchemy import select, and_
            from datetime import datetime, timedelta
            import pytz

            async with async_session_maker() as session:
                # Get users who:
                # - Have access
                # - Haven't completed course
                # - Completed their current day tasks
                result = await session.execute(
                    select(User).where(
                        and_(
                            User.has_access == True,
                            User.course_completed_at.is_(None),
                            User.current_day > 0,
                            User.current_day < 10  # COURSE_DAYS
                        )
                    )
                )
                users = result.scalars().all()

                unlocked_count = 0
                for user in users:
                    # Check user's local time based on their timezone
                    try:
                        user_tz = pytz.timezone(user.timezone)
                    except:
                        # Fallback to Moscow time if timezone is invalid
                        user_tz = pytz.timezone('Europe/Moscow')
                        logger.warning(f"Invalid timezone '{user.timezone}' for user {user.telegram_id}, using Europe/Moscow")

                    user_local_time = datetime.now(user_tz)
                    user_hour = user_local_time.hour

                    # Check if user's local time is within allowed hours (12:00-18:00)
                    if not (12 <= user_hour < 18):
                        logger.debug(f"⏰ Skipping user {user.telegram_id}: outside allowed hours (local time: {user_hour}:00)")
                        continue

                    # Check if notification was already sent today
                    if user.last_unlock_notification:
                        last_notification_date = user.last_unlock_notification.date()
                        today = datetime.utcnow().date()
                        if last_notification_date == today:
                            logger.info(f"⏭️  Skipping user {user.telegram_id}: notification already sent today")
                            continue

                    # Check if current day is completed
                    progress_result = await session.execute(
                        select(Progress).where(
                            and_(
                                Progress.user_id == user.id,
                                Progress.day_number == user.current_day,
                                Progress.tasks_completed == True
                            )
                        )
                    )
                    progress = progress_result.scalar_one_or_none()

                    if progress and user.current_day < 10:  # COURSE_DAYS
                        # Unlock next day
                        next_day = user.current_day + 1
                        user.current_day = next_day
                        user.last_unlock_notification = datetime.utcnow()
                        unlocked_count += 1

                        # Send notification to user
                        if reminder_service and reminder_service.bot:
                            try:
                                notification = f"""
🌅 **Good Morning, Subject X!**

**Day {next_day} is now unlocked!**

You've completed Day {next_day - 1} yesterday. The simulation continues...

🔓 **Your next mission awaits**
🔑 **Code Progress:** `{user.liberation_code}`

Ready to continue? /day
"""
                                await reminder_service.bot.send_message(
                                    chat_id=user.telegram_id,
                                    text=notification,
                                    parse_mode="Markdown"
                                )
                                logger.info(f"Sent unlock notification to user {user.telegram_id}")
                            except Exception as e:
                                logger.error(f"Error sending unlock notification to {user.telegram_id}: {e}")

                        logger.info(f"Unlocked day {next_day} for user {user.telegram_id}")

                await session.commit()
                logger.info(f"✅ Unlocked next day for {unlocked_count} users")

        except Exception as e:
            logger.error(f"Error in unlock next days job: {e}", exc_info=True)

    async def daily_cleanup_job(self):
        """
        Daily cleanup job
        Runs at 3:00 AM Moscow time
        """
        try:
            logger.info("🧹 Running daily cleanup job...")

            # Add cleanup tasks here if needed
            # For example: delete old sessions, clean temp files, etc.

            logger.info("✅ Daily cleanup completed")

        except Exception as e:
            logger.error(f"Error in daily cleanup job: {e}")

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Add jobs

        # 1. Check reminders every hour
        self.scheduler.add_job(
            self.check_reminders_job,
            trigger=IntervalTrigger(hours=1),
            id='check_reminders',
            name='Check and send reminders to inactive users',
            replace_existing=True
        )

        # 2. Unlock next day every hour (checks user's local timezone)
        self.scheduler.add_job(
            self.unlock_next_days_job,
            trigger=IntervalTrigger(hours=1),
            id='unlock_next_days',
            name='Unlock next day for users who completed previous day (every hour)',
            replace_existing=True
        )

        # 3. Daily cleanup at 3:00 AM
        self.scheduler.add_job(
            self.daily_cleanup_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='daily_cleanup',
            name='Daily cleanup tasks',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("✅ Scheduler started with jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"   - {job.name} (ID: {job.id})")

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("✅ Scheduler stopped")

    def get_jobs(self):
        """Get list of scheduled jobs"""
        if not self.is_running:
            return []

        return self.scheduler.get_jobs()


# Global scheduler service instance
scheduler_service = SchedulerService()
