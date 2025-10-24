"""
Course service - handles course materials delivery and progress tracking
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import MATERIALS_PATH, COURSE_DAYS, LIBERATION_CODE
from bot.database.models import User, Progress, TaskResult

logger = logging.getLogger(__name__)


class CourseService:
    """Service for course materials and progress management"""

    def __init__(self):
        self.materials_path = MATERIALS_PATH
        self.course_data = self._load_course_data()

    def _load_course_data(self) -> Dict[str, Any]:
        """Load course data from JSON"""
        try:
            course_file = self.materials_path / "course_data.json"
            if course_file.exists():
                with open(course_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.error(f"Course data file not found: {course_file}")
                return {"days": []}
        except Exception as e:
            logger.error(f"Error loading course data: {e}")
            return {"days": []}

    def get_day_data(self, day_number: int) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific day

        Args:
            day_number: Day number (1-10)

        Returns:
            Day data dict or None if not found
        """
        try:
            day_file = self.materials_path / f"day_{day_number:02d}.json"
            if day_file.exists():
                with open(day_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Day {day_number} file not found")
                return None
        except Exception as e:
            logger.error(f"Error loading day {day_number}: {e}")
            return None

    def get_day_title(self, day_number: int) -> str:
        """Get title for a day"""
        day_data = self.get_day_data(day_number)
        if day_data:
            return day_data.get('title', f'Day {day_number}')
        return f'Day {day_number}'

    def get_day_video_path(self, day_number: int) -> Optional[str]:
        """Get video file path for a day"""
        day_data = self.get_day_data(day_number)
        if day_data:
            return day_data.get('video')
        return None

    def get_day_brief_path(self, day_number: int) -> Optional[str]:
        """Get PDF brief file path for a day"""
        day_data = self.get_day_data(day_number)
        if day_data:
            return day_data.get('brief')
        return None

    def get_day_tasks(self, day_number: int) -> List[Dict[str, Any]]:
        """Get all tasks for a day"""
        day_data = self.get_day_data(day_number)
        if day_data:
            return day_data.get('tasks', [])
        return []

    def get_task(self, day_number: int, task_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific task"""
        tasks = self.get_day_tasks(day_number)
        for task in tasks:
            if task.get('task_number') == task_number:
                return task
        return None

    def get_code_letter(self, day_number: int) -> str:
        """
        Get the liberation code letter for a day

        Args:
            day_number: Day number (1-10)

        Returns:
            Single letter from LIBERATION
        """
        if 1 <= day_number <= len(LIBERATION_CODE):
            return LIBERATION_CODE[day_number - 1]
        return ""

    async def check_day_access(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ) -> bool:
        """
        Check if user has access to a specific day

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day to check

        Returns:
            True if user can access this day
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Must have paid access
        if not user.has_access:
            return False

        # Can access current day or previous days
        return day_number <= user.current_day

    async def start_day(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ) -> bool:
        """
        Start a new day for user

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day to start

        Returns:
            True if day started successfully
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.has_access:
            return False

        # Check if progress record exists
        progress_result = await session.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.day_number == day_number
            )
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            # Create new progress record
            day_tasks = self.get_day_tasks(day_number)
            progress = Progress(
                user_id=user.id,
                day_number=day_number,
                total_tasks=len(day_tasks),
                started_at=datetime.utcnow()
            )
            session.add(progress)

        # Update user's current day if needed
        if user.current_day < day_number:
            user.current_day = day_number

        await session.commit()
        logger.info(f"User {telegram_id} started day {day_number}")
        return True

    async def complete_day(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ) -> bool:
        """
        Mark day as completed

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day to complete

        Returns:
            True if day completed successfully
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Get progress
        progress_result = await session.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.day_number == day_number
            )
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            return False

        # Mark as completed
        progress.tasks_completed = True
        progress.completed_at = datetime.utcnow()

        # Add letter to liberation code at the correct position
        letter = self.get_code_letter(day_number)
        if letter:
            # Build the code with underscores for incomplete positions
            code_list = list('_' * len(LIBERATION_CODE))  # Start with all underscores

            # Fill in completed letters
            for day in range(1, day_number + 1):
                day_letter = self.get_code_letter(day)
                if day_letter:
                    code_list[day - 1] = day_letter

            user.liberation_code = ''.join(code_list)

        # Update user stats
        user.completed_days = day_number

        # Unlock next day
        if day_number < COURSE_DAYS:
            user.current_day = day_number + 1

        # Check if course is fully completed
        if day_number == COURSE_DAYS:
            user.course_completed_at = datetime.utcnow()

        await session.commit()
        logger.info(f"✅ User {telegram_id} completed day {day_number}")
        return True

    async def get_user_progress(
        self,
        session: AsyncSession,
        telegram_id: int
    ) -> Dict[str, Any]:
        """
        Get user's overall progress

        Args:
            session: Database session
            telegram_id: Telegram user ID

        Returns:
            Progress statistics
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return {}

        # Get all progress records
        progress_result = await session.execute(
            select(Progress)
            .where(Progress.user_id == user.id)
            .order_by(Progress.day_number)
        )
        progress_records = progress_result.scalars().all()

        # Calculate stats
        total_tasks = sum(p.total_tasks for p in progress_records)
        completed_tasks = sum(p.completed_tasks for p in progress_records)
        correct_answers = sum(p.correct_answers for p in progress_records)

        accuracy = (correct_answers / total_tasks * 100) if total_tasks > 0 else 0

        return {
            'user': user,
            'current_day': user.current_day,
            'completed_days': user.completed_days,
            'liberation_code': user.liberation_code,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'correct_answers': correct_answers,
            'accuracy': accuracy,
            'progress_records': progress_records,
            'course_started': user.course_started_at,
            'course_completed': user.course_completed_at,
        }

    async def mark_video_watched(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ):
        """Mark day's video as watched"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.day_number == day_number
            )
        )
        progress = progress_result.scalar_one_or_none()

        if progress:
            progress.video_watched = True
            await session.commit()

    async def mark_brief_read(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ):
        """Mark day's brief as read"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        progress_result = await session.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.day_number == day_number
            )
        )
        progress = progress_result.scalar_one_or_none()

        if progress:
            progress.brief_read = True
            await session.commit()

    def format_progress_message(self, progress_data: Dict[str, Any]) -> str:
        """Format progress data into readable message"""
        user = progress_data['user']

        message = f"""
📊 **Твой прогресс**

**Имя:** Субъект X
**Текущий день:** {progress_data['current_day']}/{COURSE_DAYS}
**Пройдено дней:** {progress_data['completed_days']}

**Код освобождения:** `{progress_data['liberation_code'] or '___________'}`

**Статистика:**
✅ Выполнено заданий: {progress_data['completed_tasks']}/{progress_data['total_tasks']}
🎯 Точность: {progress_data['accuracy']:.1f}%

"""

        # Add course completion info
        if progress_data['course_completed']:
            message += f"\n🎉 **Course Completed!**\nCompleted on: {progress_data['course_completed'].strftime('%Y-%m-%d')}"
        elif progress_data['current_day'] <= COURSE_DAYS:
            remaining = COURSE_DAYS - progress_data['completed_days']
            message += f"\n⏳ {remaining} days remaining to escape!"

        return message


# Global course service instance
course_service = CourseService()
