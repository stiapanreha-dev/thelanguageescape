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
    user_name = user.first_name if user and user.first_name else "Субъект X"

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

    # Replace [Имя] placeholder with user's real name
    question = question.replace('[Имя]', user_name)

    if task_type == 'choice':
        # Multiple choice task
        options = task.get('options', [])

        # Replace [Имя] in options
        options = [opt.replace('[Имя]', user_name) for opt in options]

        task_text = f"**{question}**"

        keyboard = get_task_keyboard(day_number, task_number, options)

        # Send media if available
        if media and os.path.exists(media):
            from aiogram.types import FSInputFile

            # Determine media type by extension
            if media.lower().endswith(('.mp4', '.mov', '.avi')):
                # Send as animation (GIF) - plays once without controls
                video = FSInputFile(media)
                await message.answer_animation(
                    animation=video,
                    caption=task_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            elif media.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # Send photo with caption
                photo = FSInputFile(media)
                await message.answer_photo(
                    photo,
                    caption=task_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            else:
                # Unknown media type, send as document
                doc = FSInputFile(media)
                await message.answer_document(
                    doc,
                    caption=task_text,
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

    elif task_type == 'voice':
        # Voice task
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

        # Check if next task is voice - auto-transition
        next_task_number = task_number + 1
        if task_number < total_tasks:
            next_task = course_service.get_task(day_number, next_task_number)
            logger.info(f"Checking next task: day={day_number}, task={next_task_number}, type={next_task.get('type') if next_task else None}")
            if next_task and next_task.get('type') == 'voice':
                # Auto-transition to voice task
                logger.info(f"Auto-transitioning to voice task {next_task_number} for user {user_id}")
                await callback.message.delete()
                await show_task(callback.message, session, user_id, day_number, next_task_number)
                await callback.answer("✅ Отлично!")
                return

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

        # Get current number of attempts AFTER saving
        current_attempts = await task_service.get_task_attempts(
            session=session,
            telegram_id=user_id,
            day_number=day_number,
            task_number=task_number
        )

        # Calculate remaining attempts
        remaining_attempts = max(0, MAX_TASK_ATTEMPTS - current_attempts)

        fail_text = THEME_MESSAGES['task_incorrect'].format(
            hint=hint,
            attempts=remaining_attempts,
            name=user_name
        )

        await callback.message.edit_text(
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
    Uses Vosk speech recognition to check for "My name is [Name]" phrase
    """
    from bot.services.speech_recognition import speech_service
    import os
    import tempfile

    user_id = message.from_user.id
    user_name = "Субъект X"
    voice: Voice = message.voice

    logger.info(f"🎤 Voice message received from user {user_id}, duration: {voice.duration}s")

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

    # Find voice task for current day (usually task #2)
    voice_task = None
    voice_task_number = None
    tasks = course_service.get_day_tasks(day_number)
    logger.info(f"Found {len(tasks)} tasks for day {day_number}")

    for task in tasks:
        if task.get('type') == 'voice':
            voice_task = task
            voice_task_number = task.get('task_number')
            logger.info(f"Found voice task #{voice_task_number}")
            break

    if not voice_task:
        logger.warning(f"No voice task found for day {day_number}")
        await message.answer("🎤 Голосовое сообщение получено, но сейчас нет активного голосового задания")
        return

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

        # Process voice with speech recognition
        recognized_text, extracted_name, has_phrase = await speech_service.process_voice_message(temp_path)

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

        # Check if required phrase was detected
        if not has_phrase:
            await message.answer(
                f"❌ **Фраза 'My name is' не обнаружена**\n\n"
                f"Я услышал: _{recognized_text}_\n\n"
                f"Пожалуйста, произнеси фразу **'My name is [твоё имя]'**",
                parse_mode="Markdown"
            )
            logger.info(f"Phrase not found. Recognized: {recognized_text}")
            return

        # Check if name was extracted
        if not extracted_name:
            await message.answer(
                f"❌ **Не удалось извлечь имя**\n\n"
                f"Я услышал: _{recognized_text}_\n\n"
                f"Убедись, что после 'My name is' произносишь свое имя",
                parse_mode="Markdown"
            )
            logger.info(f"Name not extracted. Recognized: {recognized_text}")
            return

        # Success! Save name to user profile
        user.first_name = extracted_name
        await session.commit()

        logger.info(f"Successfully extracted name '{extracted_name}' from voice message (user {user_id})")

        # Mark task as correct
        is_correct = True

    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await message.answer(
            "❌ **Ошибка обработки голосового сообщения**\n\n"
            "Попробуй отправить еще раз",
            parse_mode="Markdown"
        )
        return

    # Save result
    await task_service.save_task_result(
        session=session,
        telegram_id=user_id,
        day_number=day_number,
        task_number=voice_task_number,
        task_type=TaskType.VOICE,
        is_correct=is_correct,
        voice_file_id=voice.file_id,
        voice_duration=voice.duration,
        recognized_text=recognized_text
    )

    # Success message with extracted name
    total_tasks = len(tasks)
    letter = course_service.get_code_letter(day_number) if voice_task_number == total_tasks else ""

    success_text = f"✅ **Отлично, {extracted_name}!**\n\nТы успешно прошёл голосовое задание."
    if letter:
        success_text += f"\n\n🔑 **Фрагмент кода:** `{letter}`"

    # Auto-transition to next task
    next_task_number = voice_task_number + 1
    if voice_task_number < total_tasks:
        await message.answer(success_text, parse_mode="Markdown")
        await show_task(message, session, user_id, day_number, next_task_number)
    else:
        # Last task - show completion
        keyboard = get_task_result_keyboard(day_number, voice_task_number, total_tasks, True)
        await message.answer(success_text, parse_mode="Markdown", reply_markup=keyboard)

    logger.info(f"Voice message from user {user_id}, duration: {voice.duration}s, name: {extracted_name}, accepted")


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
