"""
Tasks handlers - interactive tasks system
Handles choice, voice, and dialog tasks
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Voice
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import THEME_MESSAGES, MAX_TASK_ATTEMPTS
from bot.database.models import User, Progress, TaskResult, TaskType
from bot.services.course import course_service
from bot.services.tasks import TaskService
from bot.keyboards.inline import (
    get_task_keyboard,
    get_task_result_keyboard,
    get_voice_task_keyboard
)

logger = logging.getLogger(__name__)

router = Router(name="tasks")

# Task service instance (will be initialized in main.py)
task_service: TaskService = None


class TaskStates(StatesGroup):
    """States for task processing"""
    waiting_for_voice = State()
    waiting_for_dialog = State()


def init_task_service():
    """Initialize task service"""
    global task_service
    task_service = TaskService()
    logger.info("Task service initialized")


@router.callback_query(F.data.startswith("start_tasks_"))
async def callback_start_tasks(callback: CallbackQuery, session: AsyncSession):
    """
    Start tasks for a day
    """
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    # Get first task
    tasks = course_service.get_day_tasks(day_number)

    if not tasks:
        await callback.answer("❌ Задания для этого дня недоступны", show_alert=True)
        return

    # Show first task
    await show_task(callback.message, session, user_id, day_number, 1)
    await callback.answer()


async def show_task(
    message: Message,
    session: AsyncSession,
    user_id: int,
    day_number: int,
    task_number: int
):
    """
    Display a specific task

    Args:
        message: Telegram message
        session: DB session
        user_id: User telegram ID
        day_number: Day number
        task_number: Task number
    """
    # Get task data
    task = course_service.get_task(day_number, task_number)

    if not task:
        await message.answer(
            f"❌ Задание {task_number} не найдено для Дня {day_number}"
        )
        return

    task_type = task.get('type', 'choice')
    title = task.get('title', f'Задание {task_number}')
    question = task.get('question', '')

    if task_type == 'choice':
        # Multiple choice task
        options = task.get('options', [])

        task_text = f"""
📝 **Задание {task_number}/{len(course_service.get_day_tasks(day_number))}**

**{title}**

{question}

Выбери правильный ответ:
"""

        keyboard = get_task_keyboard(day_number, task_number, options)

        await message.answer(
            task_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif task_type == 'voice':
        # Voice task
        task_text = f"""
🎤 **Голосовое задание {task_number}/{len(course_service.get_day_tasks(day_number))}**

**{title}**

{question}

**Инструкция:**
1. Запиши себя, произнося фразу
2. Отправь голосовое сообщение
3. Мы проверим твоё произношение

Готов? Отправь голосовое сообщение!
"""

        await message.answer(
            task_text,
            parse_mode="Markdown",
            reply_markup=get_voice_task_keyboard(day_number, task_number)
        )

    elif task_type == 'dialog':
        # Dialog task
        task_text = f"""
💬 **Диалог {task_number}/{len(course_service.get_day_tasks(day_number))}**

**{title}**

{question}

Давай поговорим. Выбери свой ответ:
"""

        # Get dialog options (first step)
        options = task.get('options', [])[:4]  # Take first 4 options

        keyboard = get_task_keyboard(day_number, task_number, options)

        await message.answer(
            task_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("answer_"))
async def callback_answer_task(callback: CallbackQuery, session: AsyncSession):
    """
    Handle task answer (choice or dialog)
    Format: answer_{day}_{task_number}_{letter}
    """
    parts = callback.data.split("_")
    day_number = int(parts[1])
    task_number = int(parts[2])
    answer_letter = parts[3]

    user_id = callback.from_user.id
    user_name = "Субъект X"

    # Get task
    task = course_service.get_task(day_number, task_number)

    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return

    # Get user's answer
    options = task.get('options', [])
    user_answer = None
    for opt in options:
        if opt.startswith(answer_letter + ")"):
            user_answer = opt
            break

    # Get correct answer
    correct_answer = task.get('correct_answer', '')

    # Check if correct
    is_correct = user_answer == correct_answer

    # Save result to database
    await task_service.save_task_result(
        session=session,
        telegram_id=user_id,
        day_number=day_number,
        task_number=task_number,
        task_type=TaskType.CHOICE if task.get('type') == 'choice' else TaskType.DIALOG,
        is_correct=is_correct,
        user_answer=user_answer,
        correct_answer=correct_answer
    )

    # Get total tasks for this day
    all_tasks = course_service.get_day_tasks(day_number)
    total_tasks = len(all_tasks)

    if is_correct:
        # Correct answer
        letter = course_service.get_code_letter(day_number) if task_number == total_tasks else ""

        success_text = THEME_MESSAGES['task_correct'].format(
            name=user_name,
            letter=letter if letter else "progress",
            day=day_number,
            total_days=10,
            code_fragment=letter
        )

        await callback.message.edit_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, True)
        )

    else:
        # Incorrect answer
        hint = task.get('hints', ['Try again!'])[0] if task.get('hints') else 'Try again!'

        fail_text = THEME_MESSAGES['task_incorrect'].format(
            hint=hint,
            attempts=MAX_TASK_ATTEMPTS,
            name=user_name
        )

        await callback.message.edit_text(
            fail_text,
            parse_mode="Markdown",
            reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, False)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("next_task_"))
async def callback_next_task(callback: CallbackQuery, session: AsyncSession):
    """
    Move to next task
    """
    parts = callback.data.split("_")
    day_number = int(parts[2])
    next_task_number = int(parts[3])

    user_id = callback.from_user.id

    await callback.message.delete()
    await show_task(callback.message, session, user_id, day_number, next_task_number)
    await callback.answer()


@router.callback_query(F.data.startswith("retry_task_"))
async def callback_retry_task(callback: CallbackQuery, session: AsyncSession):
    """
    Retry a task
    """
    parts = callback.data.split("_")
    day_number = int(parts[2])
    task_number = int(parts[3])

    user_id = callback.from_user.id

    await callback.message.delete()
    await show_task(callback.message, session, user_id, day_number, task_number)
    await callback.answer()


@router.callback_query(F.data.startswith("skip_task_"))
async def callback_skip_task(callback: CallbackQuery, session: AsyncSession):
    """
    Skip a task (voice tasks only)
    """
    parts = callback.data.split("_")
    day_number = int(parts[2])
    task_number = int(parts[3])

    user_id = callback.from_user.id

    # Get total tasks
    all_tasks = course_service.get_day_tasks(day_number)
    total_tasks = len(all_tasks)

    # Move to next task or finish
    if task_number < total_tasks:
        await callback.message.delete()
        await show_task(callback.message, session, user_id, day_number, task_number + 1)
    else:
        # Last task - finish day
        from bot.handlers.course import callback_finish_day
        # Update callback data to finish_day
        callback.data = f"finish_day_{day_number}"
        await callback_finish_day(callback, session)

    await callback.answer("⏭️ Задание пропущено")


@router.message(F.voice)
async def handle_voice_message(message: Message, session: AsyncSession):
    """
    Handle voice message for voice tasks
    """
    user_id = message.from_user.id
    user_name = "Субъект X"
    voice: Voice = message.voice

    # For now, accept any voice message
    # TODO: Implement Vosk speech recognition

    await message.answer(
        f"🎉 **Отлично, {user_name}!**\n\n"
        f"Голосовое сообщение получено! ✅\n"
        f"Длительность: {voice.duration}с\n\n"
        f"Распознавание речи скоро будет добавлено.\n"
        f"Пока все голосовые сообщения принимаются! 🎤"
    )

    logger.info(f"Voice message from user {user_id}, duration: {voice.duration}s")


@router.callback_query(F.data.startswith("voice_instructions_"))
async def callback_voice_instructions(callback: CallbackQuery):
    """
    Show voice task instructions
    """
    await callback.answer(
        "🎤 Запиши голос:\n"
        "1. Нажми кнопку микрофона\n"
        "2. Произнеси фразу чётко\n"
        "3. Отправь запись\n\n"
        "Совет: Говори медленно и чётко!",
        show_alert=True
    )
