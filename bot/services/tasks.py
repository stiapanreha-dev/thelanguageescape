"""
Task service - handles task validation and result saving
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User, Progress, TaskResult, TaskType

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task processing"""

    async def save_task_result(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int,
        task_number: int,
        task_type: TaskType,
        is_correct: bool,
        user_answer: str = None,
        correct_answer: str = None,
        voice_file_id: str = None,
        voice_duration: float = None,
        recognized_text: str = None
    ) -> bool:
        """
        Save task result to database

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day number
            task_number: Task number
            task_type: Type of task
            is_correct: Whether answer was correct
            user_answer: User's answer
            correct_answer: Correct answer
            voice_file_id: Telegram file_id for voice
            voice_duration: Voice duration in seconds
            recognized_text: Recognized text from voice

        Returns:
            True if saved successfully
        """
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {telegram_id} not found")
                return False

            # Check if result already exists
            existing_result = await session.execute(
                select(TaskResult).where(
                    TaskResult.user_id == user.id,
                    TaskResult.day_number == day_number,
                    TaskResult.task_number == task_number
                )
            )
            task_result = existing_result.scalar_one_or_none()

            if task_result:
                # Update existing result
                task_result.is_correct = is_correct
                task_result.attempts += 1
                task_result.user_answer = user_answer
                task_result.completed_at = datetime.utcnow() if is_correct else None

                if voice_file_id:
                    task_result.voice_file_id = voice_file_id
                    task_result.voice_duration = voice_duration
                    task_result.recognized_text = recognized_text

            else:
                # Create new result
                task_result = TaskResult(
                    user_id=user.id,
                    day_number=day_number,
                    task_number=task_number,
                    task_type=task_type,
                    is_correct=is_correct,
                    attempts=1,
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    voice_file_id=voice_file_id,
                    voice_duration=voice_duration,
                    recognized_text=recognized_text,
                    completed_at=datetime.utcnow() if is_correct else None
                )
                session.add(task_result)

            # Update progress
            if is_correct:
                await self._update_progress(session, user.id, day_number, task_number)

            await session.commit()
            logger.info(f"Task result saved: user={telegram_id}, day={day_number}, task={task_number}, correct={is_correct}")
            return True

        except Exception as e:
            logger.error(f"Error saving task result: {e}")
            await session.rollback()
            return False

    async def _update_progress(
        self,
        session: AsyncSession,
        user_id: int,
        day_number: int,
        task_number: int
    ):
        """Update progress for completed task"""
        # Get progress record
        result = await session.execute(
            select(Progress).where(
                Progress.user_id == user_id,
                Progress.day_number == day_number
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            # Create progress if doesn't exist
            progress = Progress(
                user_id=user_id,
                day_number=day_number,
                started_at=datetime.utcnow()
            )
            session.add(progress)

        # Update stats
        progress.completed_tasks += 1
        progress.correct_answers += 1

        await session.commit()

    async def get_user_task_results(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ) -> list[TaskResult]:
        """
        Get all task results for a user and day

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day number

        Returns:
            List of TaskResult objects
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return []

        results = await session.execute(
            select(TaskResult)
            .where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == day_number
            )
            .order_by(TaskResult.task_number)
        )

        return results.scalars().all()

    async def check_task_completed(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int,
        task_number: int
    ) -> bool:
        """
        Check if a specific task is completed

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day number
            task_number: Task number

        Returns:
            True if task is completed
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        task_result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == day_number,
                TaskResult.task_number == task_number,
                TaskResult.is_correct == True
            )
        )

        return task_result.scalar_one_or_none() is not None

    async def get_task_attempts(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int,
        task_number: int
    ) -> int:
        """
        Get number of attempts for a specific task

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day number
            task_number: Task number

        Returns:
            Number of attempts (0 if no attempts yet)
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return 0

        task_result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == day_number,
                TaskResult.task_number == task_number
            )
        )
        task = task_result.scalar_one_or_none()

        return task.attempts if task else 0

    async def get_day_completion_stats(
        self,
        session: AsyncSession,
        telegram_id: int,
        day_number: int
    ) -> dict:
        """
        Get completion statistics for a day

        Args:
            session: Database session
            telegram_id: Telegram user ID
            day_number: Day number

        Returns:
            Dict with completion stats
        """
        results = await self.get_user_task_results(session, telegram_id, day_number)

        total = len(results)
        completed = sum(1 for r in results if r.is_correct)
        correct = sum(1 for r in results if r.is_correct)
        total_attempts = sum(r.attempts for r in results)

        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'correct_answers': correct,
            'total_attempts': total_attempts,
            'accuracy': (correct / total * 100) if total > 0 else 0
        }
