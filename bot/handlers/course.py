"""
Course delivery handlers
Handles day navigation, material delivery, progress viewing
"""
import logging
from datetime import datetime
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import THEME_MESSAGES, COURSE_DAYS, MATERIALS_PATH
from bot.services.course import course_service
from bot.keyboards.inline import (
    get_day_keyboard,
    get_progress_keyboard,
    get_all_days_keyboard,
    get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

router = Router(name="course")


@router.message(Command("day"))
async def cmd_day(message: Message, session: AsyncSession):
    """
    Show current day materials
    """
    user_id = message.from_user.id

    # Check access and get current day
    has_access = await course_service.check_day_access(session, user_id, 1)

    if not has_access:
        await message.answer(
            "❌ У тебя пока нет доступа. Используй /pay для покупки курса.",
            parse_mode="Markdown"
        )
        return

    # Get user's current day
    progress = await course_service.get_user_progress(session, user_id)
    current_day = progress.get('current_day', 1)

    await show_day(message, session, user_id, current_day)


async def show_day(
    message: Message,
    session: AsyncSession,
    user_id: int,
    day_number: int
):
    """
    Display day materials

    Args:
        message: Telegram message
        session: DB session
        user_id: User telegram ID
        day_number: Day to show
    """
    # Check access
    has_access = await course_service.check_day_access(session, user_id, day_number)

    if not has_access:
        await message.answer(
            f"🔒 День {day_number} заблокирован. Сначала пройди День {day_number - 1}!",
            parse_mode="Markdown"
        )
        return

    # Start day if not started
    await course_service.start_day(session, user_id, day_number)

    # Get day data
    day_title = course_service.get_day_title(day_number)
    day_tasks = course_service.get_day_tasks(day_number)

    # Get user's name from Day 1 voice task (for personalization after completing it)
    user_name = "Субъект X"
    from bot.database.models import TaskResult, User
    from sqlalchemy import select

    # First, get internal user id from users table
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if user:
        # Now query task results using internal user id
        result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user.id,  # Use internal id, not telegram_id
                TaskResult.day_number == 1,
                TaskResult.task_number == 2,
                TaskResult.is_correct == True
            ).order_by(TaskResult.completed_at.desc())
        )
        task_result = result.scalar_one_or_none()

        if task_result and task_result.user_answer:
            user_name = task_result.user_answer

    # Format day message
    # Try to get description from JSON first
    day_description = course_service.get_day_description(day_number)

    if day_description:
        # Use description from JSON with name substitution
        description_text = day_description.replace('[Имя]', user_name).replace('[имя]', user_name)

        # Format full message with header, description, and footer
        day_text = f"""⚡️ **День {day_number}/{COURSE_DAYS}: {day_title}**

{description_text}

🎥 Посмотри брифинг
📄 Прочитай разведданные
✅ Выполни испытания

**Время взломать систему.**"""
    else:
        # Fallback to template from config.py
        day_text = THEME_MESSAGES['day_start'].format(
            day=day_number,
            total_days=COURSE_DAYS,
            title=day_title,
            name=user_name
        )

    # Check what materials are available
    has_video = course_service.get_day_video_path(day_number) is not None
    has_brief = course_service.get_day_brief_path(day_number) is not None

    await message.answer(
        day_text,
        parse_mode="Markdown",
        reply_markup=get_day_keyboard(day_number, has_video, has_brief)
    )


@router.callback_query(F.data.startswith("start_day_"))
async def callback_start_day(callback: CallbackQuery, session: AsyncSession):
    """
    Handle 'Start Day X' button
    """
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    bot = callback.bot

    await callback.message.delete()

    # For Day 2+, send intro audio first
    if day_number >= 2:
        from aiogram.types import FSInputFile
        from bot.database.models import User, TaskResult
        from sqlalchemy import select
        import os

        # Get user's name from Day 1 voice task
        # First, get internal user id
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = user_result.scalar_one_or_none()

        user_name = "Subject X"
        if user:
            result = await session.execute(
                select(TaskResult).where(
                    TaskResult.user_id == user.id,  # Use internal id, not telegram_id
                    TaskResult.day_number == 1,
                    TaskResult.task_number == 2,
                    TaskResult.is_correct == True
                ).order_by(TaskResult.completed_at.desc())
            )
            task_result = result.scalar_one_or_none()

            if task_result and task_result.user_answer:
                user_name = task_result.user_answer

        # Send intro voice message if exists
        intro_audio_path = f"docs/Материалы/По_дням/день{day_number:02d}/Готовое/day_{day_number:02d}_intro.mp3"
        if os.path.exists(intro_audio_path):
            voice_file = FSInputFile(intro_audio_path)
            await bot.send_voice(
                chat_id=callback.message.chat.id,
                voice=voice_file
            )

    await show_day(callback.message, session, user_id, day_number)
    await callback.answer()


@router.callback_query(F.data.startswith("view_day_"))
async def callback_view_day(callback: CallbackQuery, session: AsyncSession):
    """
    View a specific day from all days menu
    """
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    await callback.message.delete()
    await show_day(callback.message, session, user_id, day_number)
    await callback.answer()


@router.callback_query(F.data.startswith("locked_day_"))
async def callback_locked_day(callback: CallbackQuery):
    """
    Handle locked day click
    """
    day_number = int(callback.data.split("_")[-1])

    await callback.answer(
        f"🔒 День {day_number} заблокирован. Сначала пройди предыдущие дни!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("watch_video_"))
async def callback_watch_video(callback: CallbackQuery, session: AsyncSession):
    """
    Send day's video to user
    """
    bot = callback.bot  # Get bot from callback
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # Get video path
    video_path = course_service.get_day_video_path(day_number)

    if not video_path:
        await callback.answer("❌ Video not available for this day", show_alert=True)
        return

    # Send video
    try:
        # Resolve path relative to MATERIALS_PATH
        full_path = MATERIALS_PATH / video_path
        if not full_path.exists():
            await callback.answer("❌ Video file not found", show_alert=True)
            logger.error(f"Video file not found: {full_path}")
            return

        # Check file size (Telegram limit: 50MB for videos)
        file_size = full_path.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB in bytes
            await callback.answer("❌ Video file too large (>50MB)", show_alert=True)
            logger.error(f"Video file too large: {file_size} bytes")
            return

        await callback.message.answer(
            f"🎬 **Видео Дня {day_number}**\n\nСмотри внимательно, ищи подсказки...",
            parse_mode="Markdown"
        )

        # Create keyboard for video
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        video_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📄 Читать брифинг",
                callback_data=f"read_brief_{day_number}"
            )],
            [InlineKeyboardButton(
                text="✅ Начать задания",
                callback_data=f"start_tasks_{day_number}"
            )]
        ])

        video_file = FSInputFile(str(full_path))
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=f"Day {day_number}: {course_service.get_day_title(day_number)}",
            width=1920,
            height=1080,
            reply_markup=video_keyboard
        )

        # Mark as watched
        await course_service.mark_video_watched(session, user_id, day_number)

        await callback.answer("✅ Video sent!")
        logger.info(f"✅ Video sent to user {user_id} for day {day_number}")

    except FileNotFoundError as e:
        logger.error(f"Video file not found for day {day_number}: {e}")
        await callback.answer("❌ Video file not available", show_alert=True)
    except PermissionError as e:
        logger.error(f"Permission denied reading video file: {e}")
        await callback.answer("❌ Cannot access video file", show_alert=True)
    except Exception as e:
        logger.error(f"Error sending video to user {user_id}, day {day_number}: {e}", exc_info=True)
        await callback.answer("❌ Error sending video. Please try again later.", show_alert=True)


@router.callback_query(F.data.startswith("read_brief_"))
async def callback_read_brief(callback: CallbackQuery, session: AsyncSession):
    """
    Send day's PDF brief to user
    """
    bot = callback.bot  # Get bot from callback
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # Get brief path
    brief_path = course_service.get_day_brief_path(day_number)

    if not brief_path:
        await callback.answer("❌ Brief not available for this day", show_alert=True)
        return

    # Send PDF
    try:
        # Resolve path relative to MATERIALS_PATH
        full_path = MATERIALS_PATH / brief_path
        if not full_path.exists():
            await callback.answer("❌ Brief file not found", show_alert=True)
            logger.error(f"Brief file not found: {full_path}")
            return

        # Check file size (Telegram limit: 50MB for documents)
        file_size = full_path.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB in bytes
            await callback.answer("❌ Brief file too large (>50MB)", show_alert=True)
            logger.error(f"Brief file too large: {file_size} bytes")
            return

        await callback.message.answer(
            f"📄 **Брифинг Дня {day_number}**\n\nЧитай внимательно и учись!",
            parse_mode="Markdown"
        )

        # Create keyboard for brief
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        brief_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Начать задания",
                callback_data=f"start_tasks_{day_number}"
            )]
        ])

        brief_file = FSInputFile(str(full_path))
        await bot.send_document(
            chat_id=chat_id,
            document=brief_file,
            caption=f"Day {day_number}: {course_service.get_day_title(day_number)}",
            reply_markup=brief_keyboard
        )

        # Mark as read
        await course_service.mark_brief_read(session, user_id, day_number)

        await callback.answer("✅ Brief sent!")
        logger.info(f"✅ Brief sent to user {user_id} for day {day_number}")

    except FileNotFoundError as e:
        logger.error(f"Brief file not found for day {day_number}: {e}")
        await callback.answer("❌ Brief file not available", show_alert=True)
    except PermissionError as e:
        logger.error(f"Permission denied reading brief file: {e}")
        await callback.answer("❌ Cannot access brief file", show_alert=True)
    except Exception as e:
        logger.error(f"Error sending brief to user {user_id}, day {day_number}: {e}", exc_info=True)
        await callback.answer("❌ Error sending brief. Please try again later.", show_alert=True)


@router.message(Command("progress"))
async def cmd_progress(message: Message, session: AsyncSession):
    """
    Show user's progress
    """
    user_id = message.from_user.id

    progress_data = await course_service.get_user_progress(session, user_id)

    if not progress_data:
        await message.answer("Ты ещё не начал курс. Используй /start")
        return

    # Format progress message
    progress_text = await course_service.format_progress_message(session, progress_data)

    await message.answer(
        progress_text,
        parse_mode="Markdown",
        reply_markup=get_progress_keyboard(progress_data['current_day'])
    )


@router.callback_query(F.data == "show_progress")
async def callback_show_progress(callback: CallbackQuery, session: AsyncSession):
    """
    Show progress via callback
    """
    user_id = callback.from_user.id

    progress_data = await course_service.get_user_progress(session, user_id)

    if not progress_data:
        await callback.answer("Progress not found", show_alert=True)
        return

    progress_text = await course_service.format_progress_message(session, progress_data)

    await callback.message.edit_text(
        progress_text,
        parse_mode="Markdown",
        reply_markup=get_progress_keyboard(progress_data['current_day'])
    )

    await callback.answer()


@router.callback_query(F.data == "show_all_days")
async def callback_show_all_days(callback: CallbackQuery, session: AsyncSession):
    """
    Show all days overview
    """
    user_id = callback.from_user.id

    progress_data = await course_service.get_user_progress(session, user_id)
    current_day = progress_data.get('current_day', 1)

    all_days_text = f"""
📅 **Обзор всех дней**

Текущий: День {current_day}/{COURSE_DAYS}
Пройдено: {progress_data.get('completed_days', 0)} дней

✅ - Пройден
▶️ - Текущий
🔒 - Заблокирован

Выбери день для просмотра:
"""

    await callback.message.edit_text(
        all_days_text,
        parse_mode="Markdown",
        reply_markup=get_all_days_keyboard(current_day, COURSE_DAYS)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("finish_day_"))
async def callback_finish_day(callback: CallbackQuery, session: AsyncSession):
    """
    Complete a day
    """
    bot = callback.bot  # Get bot from callback
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    # Get user's name from Day 1 voice task
    user_name = "Субъект X"
    from bot.database.models import User, TaskResult
    from sqlalchemy import select

    # Get internal user id
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if user:
        # Get name from Day 1 Task 2 results
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
    logger.info(f"Outro message for day {day_number}: {outro_message[:50] if outro_message else 'None'}")
    if outro_message:
        # Replace [Имя] placeholder with actual name
        outro_text = outro_message.replace('[Имя]', user_name).replace('[имя]', user_name)
        completion_text += f"\n---\n\n{outro_text}\n\n---\n"
        logger.info(f"Added outro to completion_text")

    if day_number < COURSE_DAYS:
        completion_text += f"\n✨ **День {day_number + 1} теперь доступен!**\nГотов продолжить?"
    else:
        # Final day - generate certificate!
        liberation_code = progress_data['liberation_code']
        completion_text += f"\n🏆 **КОД ОСВОБОЖДЕНИЯ СОБРАН!**\n`{liberation_code}`\n\nТы сбежал из симуляции! 🎊\n\n⏳ Генерируем твой сертификат..."

    from bot.keyboards.inline import get_day_completion_keyboard
    keyboard = get_day_completion_keyboard(day_number, COURSE_DAYS)

    await callback.message.edit_text(
        completion_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # Generate certificate for final day
    if day_number == COURSE_DAYS:
        await generate_and_send_certificate(callback.message, session, user_id, user_name, bot)

    await callback.answer("🎉 Day completed!", show_alert=False)


async def generate_and_send_certificate(
    message: Message,
    session: AsyncSession,
    user_id: int,
    user_name: str,
    bot: Bot
):
    """
    Generate and send certificate to user

    Args:
        message: Message to reply to
        session: DB session
        user_id: User telegram ID
        user_name: User name
        bot: Bot instance
    """
    from bot.services.certificates import generate_user_certificate
    from bot.database.models import Certificate, User
    from sqlalchemy import select

    try:
        # Get user progress data
        progress_data = await course_service.get_user_progress(session, user_id)

        # Generate certificate
        cert_path = await generate_user_certificate(
            user_name=user_name,
            telegram_id=user_id,
            completion_date=progress_data.get('course_completed'),
            total_days=10,
            accuracy=progress_data.get('accuracy', 100.0),
            liberation_code=progress_data.get('liberation_code', 'LIBERATION')
        )

        if not cert_path or not cert_path.exists():
            logger.error(f"Certificate generation failed for user {user_id}")
            await message.answer(
                "❌ Error generating certificate. Please contact support."
            )
            return

        # Send certificate
        from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

        cert_file = FSInputFile(str(cert_path))

        # Check certificate file size
        cert_size = cert_path.stat().st_size
        if cert_size > 10 * 1024 * 1024:  # 10MB limit for safety
            logger.error(f"Certificate file too large: {cert_size} bytes")
            await message.answer(
                "❌ Certificate file too large. Please contact support."
            )
            return

        # Cap accuracy at 100% for display
        accuracy_display = min(100.0, progress_data.get('accuracy', 100))

        # Send photo and capture the message to get file_id
        sent_message = await bot.send_photo(
            chat_id=message.chat.id,
            photo=cert_file,
            caption=f"""
📜 **Сертификат о прохождении**

Поздравляем, **{user_name}**!

Ты успешно завершил курс **The Language Escape**!

🔑 Код освобождения: `{progress_data.get('liberation_code', 'LIBERATION')}`
✅ Точность: {accuracy_display:.1f}%
📅 Завершено: {progress_data.get('course_completed').strftime('%d.%m.%Y') if progress_data.get('course_completed') else 'Сегодня'}

**Что дальше?**
📢 Присоединяйся к нашему каналу для новых курсов!
🌟 Поделись своим достижением!
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Присоединиться к каналу", url="https://t.me/language_escape")],
            ])
        )

        # Extract file_id from sent photo (get largest size)
        file_id = sent_message.photo[-1].file_id if sent_message.photo else None

        # Save certificate info to database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Cap accuracy at 100% before saving to database
            accuracy_to_save = min(100.0, progress_data.get('accuracy', 0.0))

            certificate = Certificate(
                user_id=user.id,
                certificate_code=progress_data.get('liberation_code', 'LIBERATION'),
                file_path=str(cert_path),
                file_id=file_id,  # Save Telegram file_id for inline sharing
                completion_date=progress_data.get('course_completed') or datetime.utcnow(),
                total_days=10,
                final_code=progress_data.get('liberation_code', 'LIBERATION'),
                total_tasks=progress_data.get('total_tasks', 0),
                correct_answers=progress_data.get('correct_answers', 0),
                accuracy=accuracy_to_save
            )
            session.add(certificate)
            await session.commit()
            logger.info(f"✅ Certificate saved with file_id: {file_id}")

        logger.info(f"✅ Certificate sent to user {user_id}")

    except FileNotFoundError as e:
        logger.error(f"Certificate file not found for user {user_id}: {e}")
        await message.answer(
            "❌ Certificate not found. Please contact support."
        )
    except PermissionError as e:
        logger.error(f"Permission denied accessing certificate: {e}")
        await message.answer(
            "❌ Cannot access certificate. Please contact support."
        )
    except Exception as e:
        logger.error(f"Error sending certificate to user {user_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Error sending certificate. Please try again later or contact support."
        )
