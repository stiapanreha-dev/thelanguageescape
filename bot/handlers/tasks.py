"""
Tasks handlers - interactive tasks system
Handles choice, voice, and dialog tasks
"""
import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Voice
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import THEME_MESSAGES, MAX_TASK_ATTEMPTS, MATERIALS_PATH, COURSE_DAYS
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

# Track users currently processing voice messages (protection from race condition)
_processing_voice_users = set()


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

    # Reset all attempts for this day (fresh start)
    await task_service.reset_day_attempts(
        session=session,
        telegram_id=user_id,
        day_number=day_number
    )

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
    # Get user for name substitution
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    # Get user's name from Day 1 voice task (for personalization)
    user_name = "Субъект X"
    if user:
        from bot.database.models import TaskResult

        # Get name from Day 1 Task 2 (voice task where name was collected)
        name_result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == 1,
                TaskResult.task_number == 2,
                TaskResult.is_correct == True
            ).order_by(TaskResult.completed_at.desc())
        )
        task_result = name_result.scalar_one_or_none()

        if task_result and task_result.user_answer:
            user_name = task_result.user_answer

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
    media = task.get('media', None)  # Path to video/image for task

    # Replace [Имя] and Subject X placeholders with user's real name
    question = question.replace('[Имя]', user_name)
    question = question.replace('Subject X', user_name)

    if task_type == 'choice':
        # Multiple choice task
        options = task.get('options', [])

        # Replace [Имя] in options
        options = [opt.replace('[Имя]', user_name) for opt in options]

        task_text = f"**{question}**"

        keyboard = get_task_keyboard(day_number, task_number, options)

        # Send media if available
        if media:
            from aiogram.types import FSInputFile

            # Resolve path relative to MATERIALS_PATH
            full_path = MATERIALS_PATH / media

            if full_path.exists():
                # Determine media type by extension
                if media.lower().endswith(('.mp4', '.mov', '.avi')):
                    # Send as animation (GIF) - plays once without controls
                    video = FSInputFile(full_path)
                    await message.answer_animation(
                        animation=video,
                        caption=task_text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                elif media.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    # Send photo with caption
                    photo = FSInputFile(full_path)
                    await message.answer_photo(
                        photo,
                        caption=task_text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                else:
                    # Unknown media type, send as document
                    doc = FSInputFile(full_path)
                    await message.answer_document(
                        doc,
                        caption=task_text,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
            else:
                # Media file not found, send text only with warning
                logger.warning(f"Media file not found: {full_path}")
                await message.answer(
                    task_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        else:
            # No media, send text only
            await message.answer(
                task_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    elif task_type == 'audio':
        # Audio listening task
        options = task.get('options', [])

        # Replace [Имя] in options and question
        options = [opt.replace('[Имя]', user_name) for opt in options]
        question = question.replace('[Имя]', user_name)

        task_text = f"**{question}**"

        # If no options provided, create a single "Continue" button
        if not options:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Прослушал(а)", callback_data=f"answer_{day_number}_{task_number}_completed")]
            ])
        else:
            keyboard = get_task_keyboard(day_number, task_number, options)

        # Send audio if available
        if media:
            from aiogram.types import FSInputFile

            # Resolve path relative to MATERIALS_PATH
            full_path = MATERIALS_PATH / media

            if full_path.exists():
                audio = FSInputFile(full_path)
                await message.answer_audio(
                    audio=audio,
                    caption=task_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            else:
                # Audio file not found, send text only with warning
                logger.warning(f"Audio file not found: {full_path}")
                await message.answer(
                    task_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        else:
            # No audio file, send text only
            await message.answer(
                task_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    elif task_type == 'voice':
        # Voice task
        # Try to get full instruction from JSON first
        instruction = task.get('instruction')

        if instruction:
            # Use instruction from JSON with name substitution
            task_text = instruction.replace('[Имя]', user_name).replace('[имя]', user_name)
        else:
            # Fallback to hardcoded template (for backward compatibility)
            task_text = f"""
🎤 **Голосовое задание {task_number}/{len(course_service.get_day_tasks(day_number))}**

**{question}**

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
        task_text = f"**{question}**"

        # Get dialog options (first step)
        options = task.get('options', [])[:4]  # Take first 4 options

        # Replace [Имя] in options
        options = [opt.replace('[Имя]', user_name) for opt in options]

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

    # Get user's name from Day 1 Task 2 results
    from bot.database.models import User, TaskResult
    from sqlalchemy import select

    user_result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if user:
        name_result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == 1,
                TaskResult.task_number == 2,
                TaskResult.is_correct == True
            ).order_by(TaskResult.completed_at.desc())
        )
        name_task = name_result.scalar_one_or_none()
        if name_task and name_task.user_answer:
            user_name = name_task.user_answer

    # Get task
    task = course_service.get_task(day_number, task_number)

    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return

    # Special handling for audio task with "completed" button
    if answer_letter == "completed" and task.get('type') == 'audio':
        # Audio task completed - always mark as correct
        is_correct = True
        user_answer = "Прослушал(а)"
        correct_answer = "completed"

        # Save result to database
        await task_service.save_task_result(
            session=session,
            telegram_id=user_id,
            day_number=day_number,
            task_number=task_number,
            task_type=TaskType.CHOICE,  # Use CHOICE for audio tasks
            is_correct=is_correct,
            user_answer=user_answer,
            correct_answer=correct_answer
        )
    else:
        # Regular choice/dialog task
        # Get user's answer
        options = task.get('options', [])
        user_answer = None
        for opt in options:
            if opt.startswith(answer_letter + ")"):
                user_answer = opt
                break

        # Get correct answer
        correct_answer = task.get('correct_answer', '')

        # Check if correct - compare only the letter part
        # user_answer format: "A) Some text"
        # correct_answer format: "A" or "A) Some text"
        is_correct = False
        if user_answer:
            user_letter = user_answer.split(")")[0].strip()  # Extract "A" from "A) text"
            correct_letter = correct_answer.split(")")[0].strip()  # Extract "A" from "A" or "A) text"
            is_correct = user_letter == correct_letter

        # Save result to database (this will increment attempts)
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

        # Check if should auto-transition to next task
        next_task_number = task_number + 1
        if task_number < total_tasks:
            next_task = course_service.get_task(day_number, next_task_number)
            logger.info(f"Checking next task: day={day_number}, task={next_task_number}, type={next_task.get('type') if next_task else None}")

            # Auto-transition rules:
            # 1. If next task is voice/audio - always auto-transition
            # 2. For Day 2: auto-transition from task 1 to task 2, and task 2 to task 3
            # 3. For Day 3: auto-transition from task 1, 2, 3 (show success only after task 4)
            # 4. For Day 4: auto-transition from task 1-6 (show success only after task 7)
            # 5. For Day 5: auto-transition from task 1-8 (show success only after task 9)
            # 6. For Day 6: auto-transition from task 1-3 (show success only after task 4)
            # 7. For Day 7: auto-transition from task 1-3 (show success only after task 4)
            # 8. For Day 8: auto-transition from task 1-3 (show success only after task 4)
            should_auto_transition = False
            if next_task and next_task.get('type') in ['voice', 'audio']:
                should_auto_transition = True
            elif day_number == 2 and task_number in [1, 2]:
                should_auto_transition = True
            elif day_number == 3 and task_number in [1, 2, 3]:
                should_auto_transition = True
            elif day_number == 4 and task_number in [1, 2, 3, 4, 5, 6]:
                should_auto_transition = True
            elif day_number == 5 and task_number in [1, 2, 3, 4, 5, 6, 7, 8]:
                should_auto_transition = True
            elif day_number == 6 and task_number in [1, 2, 3]:
                should_auto_transition = True
            elif day_number == 7 and task_number in [1, 2, 3]:
                should_auto_transition = True
            elif day_number == 8 and task_number in [1, 2, 3]:
                should_auto_transition = True
            elif day_number == 9 and task_number in [1, 2]:
                should_auto_transition = True

            if should_auto_transition:
                # Auto-transition to next task
                logger.info(f"Auto-transitioning to task {next_task_number} for user {user_id}")
                await callback.message.delete()
                await show_task(callback.message, session, user_id, day_number, next_task_number)
                await callback.answer("✅ Отлично!")
                return

        # Use custom success message from task if available, otherwise use template
        custom_success = task.get('correct_message', '')
        if custom_success:
            # Replace placeholders in custom message
            success_text = custom_success.replace('[Имя]', user_name).replace('Subject X', user_name)
        else:
            success_text = THEME_MESSAGES['task_correct'].format(
                name=user_name,
                letter=letter if letter else "progress",
                day=day_number,
                total_days=10,
                code_fragment=letter
            )

        # Check if message has text (can be edited) or media (need new message)
        if callback.message.text:
            await callback.message.edit_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, True)
            )
        else:
            # Message has media (audio, video, etc.), send new message
            await callback.message.answer(
                success_text,
                parse_mode="Markdown",
                reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, True)
            )

    else:
        # Incorrect answer
        hint = task.get('hint', 'Try again!')

        # Get current number of attempts AFTER saving
        current_attempts = await task_service.get_task_attempts(
            session=session,
            telegram_id=user_id,
            day_number=day_number,
            task_number=task_number
        )

        # Calculate remaining attempts
        remaining_attempts = max(0, MAX_TASK_ATTEMPTS - current_attempts)

        # Use custom incorrect message from task if available, otherwise use template
        custom_incorrect = task.get('incorrect_message', '')
        if custom_incorrect:
            # Replace placeholders in custom message
            fail_text = custom_incorrect.replace('[Имя]', user_name).replace('Subject X', user_name)
            fail_text += f"\n\n💡 Подсказка: {hint}\n🔄 Осталось попыток: {remaining_attempts}"
        else:
            fail_text = THEME_MESSAGES['task_incorrect'].format(
                hint=hint,
                attempts=remaining_attempts,
                name=user_name
            )

        # Check if message has text (can be edited) or media (need new message)
        if callback.message.text:
            await callback.message.edit_text(
                fail_text,
                parse_mode="Markdown",
                reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, False, remaining_attempts)
            )
        else:
            # Message has media (audio, video, etc.), send new message
            await callback.message.answer(
                fail_text,
                parse_mode="Markdown",
                reply_markup=get_task_result_keyboard(day_number, task_number, total_tasks, False, remaining_attempts)
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

    # Get task type to save skip record
    task = course_service.get_task(day_number, task_number)

    if task:
        # Save skip record to database (so this task is marked as completed)
        task_type = TaskType.VOICE if task.get('type') == 'voice' else TaskType.CHOICE

        # For voice tasks with name extraction, use "Subject X" instead of "SKIPPED"
        user_answer = "SKIPPED"
        if task.get('type') == 'voice' and task.get('voice_extract_pattern') == 'name':
            user_answer = "Subject X"

        await task_service.save_task_result(
            session=session,
            telegram_id=user_id,
            day_number=day_number,
            task_number=task_number,
            task_type=task_type,
            is_correct=True,  # Mark as correct to count as completed
            user_answer=user_answer,
            correct_answer="SKIPPED"
        )
        logger.info(f"Task {day_number}.{task_number} skipped by user {user_id}")

    # Get total tasks
    all_tasks = course_service.get_day_tasks(day_number)
    total_tasks = len(all_tasks)

    # Move to next task or finish
    if task_number < total_tasks:
        # Try to delete message, but continue even if it fails
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete message in skip_task: {e}")

        await show_task(callback.message, session, user_id, day_number, task_number + 1)
    else:
        # Last task - finish day manually (can't use callback_finish_day due to frozen callback)
        from bot.database.models import User, TaskResult
        from bot.keyboards.inline import get_day_completion_keyboard

        # Get user's name
        user_name = "Субъект X"
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if user:
            name_result = await session.execute(
                select(TaskResult).where(
                    TaskResult.user_id == user.id,
                    TaskResult.day_number == 1,
                    TaskResult.task_number == 2,
                    TaskResult.is_correct == True
                ).order_by(TaskResult.completed_at.desc())
            )
            name_task = name_result.scalar_one_or_none()
            if name_task and name_task.user_answer and name_task.user_answer != "SKIPPED":
                user_name = name_task.user_answer

        # Complete the day
        success = await course_service.complete_day(session, user_id, day_number)

        if not success:
            await callback.answer("Error completing day", show_alert=True)
            return

        # Get the letter unlocked
        letter = course_service.get_code_letter(day_number)

        # Get updated progress
        progress_data = await course_service.get_user_progress(session, user_id)

        # Success message
        completion_text = f"""
🎉 **День {day_number} пройден!**

Отличная работа, {user_name}!

🔑 **Фрагмент кода разблокирован:** `{letter}`
📊 **Прогресс:** `{progress_data['liberation_code']}`
⏭️ **Уровень:** {day_number}/{COURSE_DAYS}

"""

        # Add outro message if exists (story continuation)
        outro_message = course_service.get_day_outro_message(day_number)
        if outro_message:
            # Replace [Имя] placeholder with actual name
            outro_text = outro_message.replace('[Имя]', user_name).replace('[имя]', user_name)
            completion_text += f"\n---\n\n{outro_text}\n\n---\n"

        if day_number < COURSE_DAYS:
            completion_text += f"\n✨ **День {day_number + 1} теперь доступен!**\nГотов продолжить?"
        else:
            # Final day
            liberation_code = progress_data['liberation_code']
            completion_text += f"\n🏆 **КОД ОСВОБОЖДЕНИЯ СОБРАН!**\n`{liberation_code}`\n\nТы сбежал из симуляции! 🎊\n\n⏳ Генерируем твой сертификат..."

        keyboard = get_day_completion_keyboard(day_number, COURSE_DAYS)

        # Delete old message and send new one
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            completion_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # Generate certificate for final day
        if day_number == COURSE_DAYS:
            from bot.handlers.course import generate_and_send_certificate
            await generate_and_send_certificate(
                callback.message,
                session,
                user_id,
                user_name,
                callback.bot
            )

    await callback.answer("⏭️ Задание пропущено")


@router.message(F.voice)
async def handle_voice_message(message: Message, session: AsyncSession):
    """
    Handle voice message for voice tasks
    Uses Vosk speech recognition to check for "My name is [Name]" phrase
    """
    from bot.services.speech_recognition import speech_service
    import os
    import tempfile

    user_id = message.from_user.id
    user_name = "Субъект X"
    voice: Voice = message.voice

    logger.info(f"🎤 Voice message received from user {user_id}, duration: {voice.duration}s")

    # Protection from race condition: check if user is already processing a voice message
    if user_id in _processing_voice_users:
        logger.warning(f"User {user_id} is already processing a voice message, ignoring new one")
        await message.answer("⏳ Подожди, я ещё обрабатываю предыдущее голосовое сообщение...")
        return

    # Mark user as processing
    _processing_voice_users.add(user_id)

    try:
        # Get user's current day and find active voice task
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.has_access:
            logger.warning(f"User {user_id} has no access to course")
            await message.answer("❌ У вас нет доступа к курсу")
            return

        # Determine the day user is ACTUALLY working on by checking latest task result
        # This handles the case where user is repeating an old day
        from bot.database.models import TaskResult
        from sqlalchemy import desc

        latest_result = await session.execute(
            select(TaskResult)
            .where(TaskResult.user_id == user.id)
            .order_by(desc(TaskResult.created_at))
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        if latest:
            day_number = latest.day_number
            logger.info(f"User {user_id} is working on day {day_number} (from latest task result)")
        else:
            day_number = user.current_day
            logger.info(f"User {user_id} current day: {day_number} (no task results yet)")

        # Find CURRENT voice task for this day
        # Check which task user is on by looking at completed tasks
        tasks = course_service.get_day_tasks(day_number)
        logger.info(f"Found {len(tasks)} tasks for day {day_number}")

        # Get completed tasks for this day (including skipped ones)
        completed_result = await session.execute(
            select(TaskResult)
            .where(
                TaskResult.user_id == user.id,
                TaskResult.day_number == day_number,
                TaskResult.is_correct == True
            )
        )
        completed_tasks = completed_result.scalars().all()
        completed_task_numbers = {t.task_number for t in completed_tasks}

        logger.info(f"Completed task numbers for day {day_number}: {completed_task_numbers}")

        # Find first incomplete voice task (skip SKIPPED tasks)
        voice_task = None
        voice_task_number = None
        for task in tasks:
            task_num = task.get('task_number')
            if task.get('type') == 'voice' and task_num not in completed_task_numbers:
                voice_task = task
                voice_task_number = task_num
                logger.info(f"Found active voice task #{voice_task_number}")
                break

        if not voice_task:
            logger.warning(f"No active voice task found for day {day_number}")
            await message.answer("🎤 Голосовое сообщение получено, но нет активного голосового задания")
            return

        # Get task configuration
        voice_keywords = voice_task.get('voice_keywords', [])
        extract_pattern = voice_task.get('voice_extract_pattern')  # name, country, profession, or None
        hints = voice_task.get('hints', [])

        # Initialize variables that will be used after try block
        extracted_data = None
        recognized_text = None
        is_correct = False

        # Download voice message
        try:
            # Show processing message
            processing_msg = await message.answer("🎧 Обрабатываю голосовое сообщение...")

            # Download file
            file = await message.bot.get_file(voice.file_id)

            # Create temp file for voice
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name
                await message.bot.download_file(file.file_path, temp_path)

            # Transcribe audio
            recognized_text = await speech_service.transcribe_audio(temp_path)

            # Cleanup temp file
            try:
                os.remove(temp_path)
            except:
                pass

            # Delete processing message
            await processing_msg.delete()

            # Check if recognition was successful
            if not recognized_text:
                await message.answer(
                    "❌ **Не удалось распознать речь**\n\n"
                    "Попробуй еще раз:\n"
                    "1. Говори четко и медленно\n"
                    "2. Убедись, что произносишь фразу полностью\n"
                    "3. Уменьши фоновый шум",
                    parse_mode="Markdown"
                )
                logger.warning(f"Voice recognition failed for user {user_id}")
                return

            # Check if required keywords found
            text_lower = recognized_text.lower()
            has_keyword = any(keyword in text_lower for keyword in voice_keywords) if voice_keywords else True

            if not has_keyword:
                hint_text = hints[0] if hints else "Try again!"
                await message.answer(
                    f"❌ **Требуемая фраза не обнаружена**\n\n"
                    f"Я услышал: _{recognized_text}_\n\n"
                    f"{hint_text}",
                    parse_mode="Markdown"
                )
                logger.info(f"Keywords not found. Recognized: {recognized_text}")
                return

            # Extract data based on pattern (if pattern is specified)
            extracted_value = None
            if extract_pattern:
                if extract_pattern == 'name':
                    extracted_value = speech_service.extract_name_from_text(recognized_text)
                elif extract_pattern == 'country':
                    extracted_value = speech_service.extract_country_from_text(recognized_text)
                elif extract_pattern == 'profession':
                    extracted_value = speech_service.extract_profession_from_text(recognized_text)

                # Check if extraction was successful
                if not extracted_value:
                    hint_text = hints[1] if len(hints) > 1 else "Try again!"
                    await message.answer(
                        f"❌ **Не удалось извлечь данные**\n\n"
                        f"Я услышал: _{recognized_text}_\n\n"
                        f"{hint_text}",
                        parse_mode="Markdown"
                    )
                    logger.info(f"{extract_pattern} not extracted. Recognized: {recognized_text}")
                    return

                # Success! Save to user profile
                if extract_pattern == 'name':
                    user.first_name = extracted_value
                elif extract_pattern == 'country':
                    user.country = extracted_value
                elif extract_pattern == 'profession':
                    user.profession = extracted_value

                await session.commit()

                logger.info(f"Successfully extracted {extract_pattern} '{extracted_value}' from voice (user {user_id})")

            # Mark task as correct
            is_correct = True
            extracted_data = extracted_value if extracted_value else recognized_text

        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            await message.answer(
                "❌ **Ошибка обработки голосового сообщения**\n\n"
                "Попробуй отправить еще раз",
                parse_mode="Markdown"
            )
            return

        # Save result with extracted data as user_answer
        await task_service.save_task_result(
            session=session,
            telegram_id=user_id,
            day_number=day_number,
            task_number=voice_task_number,
            task_type=TaskType.VOICE,
            is_correct=is_correct,
            user_answer=extracted_data if extracted_data else None,
            voice_file_id=voice.file_id,
            voice_duration=voice.duration,
            recognized_text=recognized_text
        )

        # Get user's name for personalization from Day 1 voice task
        user_display_name = "Субъект X"
        if extract_pattern == 'name':
            # If this is the name task, use extracted name
            user_display_name = extracted_data
        else:
            # Otherwise get name from Day 1 Task 2 results
            name_result = await session.execute(
                select(TaskResult).where(
                    TaskResult.user_id == user.id,
                    TaskResult.day_number == 1,
                    TaskResult.task_number == 2,
                    TaskResult.is_correct == True
                ).order_by(TaskResult.completed_at.desc())
            )
            name_task = name_result.scalar_one_or_none()
            if name_task and name_task.user_answer:
                user_display_name = name_task.user_answer

        # Success message
        total_tasks = len(tasks)
        letter = course_service.get_code_letter(day_number) if voice_task_number == total_tasks else ""

        # Use custom success message if available
        custom_success = voice_task.get('correct_message', '')
        if custom_success:
            # Replace [Имя] placeholder with user's actual name
            success_text = custom_success.replace('[Имя]', user_display_name)
        else:
            success_text = f"✅ **Отлично, {user_display_name}!**\n\nТы успешно прошёл голосовое задание."
            if letter:
                success_text += f"\n\n🔑 **Фрагмент кода:** `{letter}`"

        # Auto-transition to next task
        next_task_number = voice_task_number + 1
        if voice_task_number < total_tasks:
            # Not last task - transition directly without success message
            await show_task(message, session, user_id, day_number, next_task_number)
        else:
            # Last task - show completion with code letter
            keyboard = get_task_result_keyboard(day_number, voice_task_number, total_tasks, True)
            await message.answer(success_text, parse_mode="Markdown", reply_markup=keyboard)

        logger.info(f"Voice task completed by user {user_id}: {extract_pattern}='{extracted_data}'")
    finally:
        # Always remove user from processing set
        _processing_voice_users.discard(user_id)


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
