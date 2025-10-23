"""
Course delivery handlers
Handles day navigation, material delivery, progress viewing
"""
import logging
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import THEME_MESSAGES, COURSE_DAYS
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
            "❌ You don't have access yet. Use /pay to purchase the course.",
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
            f"🔒 Day {day_number} is locked. Complete Day {day_number - 1} first!",
            parse_mode="Markdown"
        )
        return

    # Start day if not started
    await course_service.start_day(session, user_id, day_number)

    # Get day data
    day_title = course_service.get_day_title(day_number)
    day_tasks = course_service.get_day_tasks(day_number)

    # Format day message
    day_text = THEME_MESSAGES['day_start'].format(
        day=day_number,
        total_days=COURSE_DAYS,
        title=day_title,
        name=message.from_user.first_name or "Subject X"
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

    await callback.message.delete()
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
        f"🔒 Day {day_number} is locked. Complete previous days first!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("watch_video_"))
async def callback_watch_video(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """
    Send day's video to user
    """
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
        full_path = Path(video_path)
        if not full_path.exists():
            await callback.answer("❌ Video file not found", show_alert=True)
            logger.error(f"Video file not found: {full_path}")
            return

        await callback.message.answer(
            f"🎬 **Day {day_number} Video**\n\nWatch carefully for clues...",
            parse_mode="Markdown"
        )

        video_file = FSInputFile(str(full_path))
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=f"Day {day_number}: {course_service.get_day_title(day_number)}"
        )

        # Mark as watched
        await course_service.mark_video_watched(session, user_id, day_number)

        await callback.answer("✅ Video sent!")
        logger.info(f"Video sent to user {user_id} for day {day_number}")

    except Exception as e:
        logger.error(f"Error sending video: {e}")
        await callback.answer("❌ Error sending video", show_alert=True)


@router.callback_query(F.data.startswith("read_brief_"))
async def callback_read_brief(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """
    Send day's PDF brief to user
    """
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
        full_path = Path(brief_path)
        if not full_path.exists():
            await callback.answer("❌ Brief file not found", show_alert=True)
            logger.error(f"Brief file not found: {full_path}")
            return

        await callback.message.answer(
            f"📄 **Day {day_number} Brief**\n\nRead carefully and learn!",
            parse_mode="Markdown"
        )

        brief_file = FSInputFile(str(full_path))
        await bot.send_document(
            chat_id=chat_id,
            document=brief_file,
            caption=f"Day {day_number}: {course_service.get_day_title(day_number)}"
        )

        # Mark as read
        await course_service.mark_brief_read(session, user_id, day_number)

        await callback.answer("✅ Brief sent!")
        logger.info(f"Brief sent to user {user_id} for day {day_number}")

    except Exception as e:
        logger.error(f"Error sending brief: {e}")
        await callback.answer("❌ Error sending brief", show_alert=True)


@router.message(Command("progress"))
async def cmd_progress(message: Message, session: AsyncSession):
    """
    Show user's progress
    """
    user_id = message.from_user.id

    progress_data = await course_service.get_user_progress(session, user_id)

    if not progress_data:
        await message.answer("You haven't started the course yet. Use /start")
        return

    # Format progress message
    progress_text = course_service.format_progress_message(progress_data)

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

    progress_text = course_service.format_progress_message(progress_data)

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
📅 **All Days Overview**

Current: Day {current_day}/{COURSE_DAYS}
Completed: {progress_data.get('completed_days', 0)} days

✅ - Completed
▶️ - Current
🔒 - Locked

Select a day to view:
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
    day_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "Subject X"

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
🎉 **Day {day_number} Complete!**

Excellent work, {user_name}!

🔑 **Code Fragment Unlocked:** `{letter}`
📊 **Progress:** {progress_data['liberation_code']}
⏭️ **Level:** {day_number}/{COURSE_DAYS}

"""

    if day_number < COURSE_DAYS:
        completion_text += f"\n✨ **Day {day_number + 1} is now unlocked!**\nReady to continue?"
    else:
        completion_text += f"\n🏆 **LIBERATION CODE COMPLETE!**\n`{progress_data['liberation_code']}`\n\nYou've escaped the simulation! 🎊"

    from bot.keyboards.inline import get_day_completion_keyboard
    keyboard = get_day_completion_keyboard(day_number, COURSE_DAYS)

    await callback.message.edit_text(
        completion_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await callback.answer("🎉 Day completed!", show_alert=False)
