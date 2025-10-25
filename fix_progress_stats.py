"""
Fix Progress table statistics
This script recalculates completed_tasks, correct_answers, and total_tasks
for all existing progress records based on actual TaskResult data.
"""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.database import get_session
from bot.database.models import Progress, TaskResult, User
from bot.services.course import course_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_progress_stats():
    """
    Fix all progress statistics by recalculating from TaskResult data
    """
    async for session in get_session():
        try:
            # Get all progress records
            result = await session.execute(select(Progress))
            progress_records = result.scalars().all()

            logger.info(f"Found {len(progress_records)} progress records to fix")

            for progress in progress_records:
                logger.info(f"Processing progress: user_id={progress.user_id}, day={progress.day_number}")

                # Get actual task results for this user and day
                task_results = await session.execute(
                    select(TaskResult).where(
                        TaskResult.user_id == progress.user_id,
                        TaskResult.day_number == progress.day_number,
                        TaskResult.is_correct == True
                    ).distinct(TaskResult.task_number)  # Only count each task once
                )
                correct_tasks = task_results.scalars().all()

                # Get total tasks for this day from JSON
                day_tasks = course_service.get_day_tasks(progress.day_number)
                total_tasks = len(day_tasks) if day_tasks else 0

                # Count unique task numbers that were completed correctly
                completed_task_numbers = set(tr.task_number for tr in correct_tasks)
                completed_count = len(completed_task_numbers)

                logger.info(f"  Before: total_tasks={progress.total_tasks}, completed={progress.completed_tasks}, correct={progress.correct_answers}")
                logger.info(f"  After:  total_tasks={total_tasks}, completed={completed_count}, correct={completed_count}")

                # Update progress
                progress.total_tasks = total_tasks
                progress.completed_tasks = completed_count
                progress.correct_answers = completed_count

            await session.commit()
            logger.info("✅ All progress records fixed!")

        except Exception as e:
            logger.error(f"Error fixing progress stats: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(fix_progress_stats())
