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
from bot.services.reminders import reminder_service

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

            async with async_session_maker() as session:
                if reminder_service:
                    await reminder_service.check_and_send_reminders(session)
                else:
                    logger.error("Reminder service not initialized")

        except Exception as e:
            logger.error(f"Error in reminder check job: {e}")

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

        # 2. Daily cleanup at 3:00 AM
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
