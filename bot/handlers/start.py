"""
Start and basic command handlers
Registration, welcome messages, help
"""
import logging
import datetime as dt_module
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import COURSE_NAME, COURSE_PRICE, COURSE_CURRENCY, COURSE_DAYS, THEME_MESSAGES
from bot.database.models import User, Payment, PaymentStatus, TaskResult
from bot.keyboards.inline import get_welcome_keyboard, get_main_menu_keyboard
from bot.utils.timezone_detector import detect_timezone_from_language

logger = logging.getLogger(__name__)

router = Router(name="start")


async def get_user_name_from_day1(session: AsyncSession, user_id: int) -> str:
    """
    Get user's name from Day 1 Task 2 voice recognition result

    Args:
        session: Database session
        user_id: User's database ID (not telegram_id!)

    Returns:
        User's name or "Субъект X" if not found
    """
    try:
        result = await session.execute(
            select(TaskResult).where(
                TaskResult.user_id == user_id,
                TaskResult.day_number == 1,
                TaskResult.task_number == 2,
                TaskResult.is_correct == True
            ).order_by(TaskResult.completed_at.desc())
        )
        name_task = result.scalar_one_or_none()
        if name_task and name_task.user_answer:
            return name_task.user_answer
    except Exception as e:
        logger.error(f"Error getting user name from Day 1: {e}")

    return "Субъект X"


async def check_pending_payments(message: Message, session: AsyncSession, user: User):
    """
    Check if user has pending payments and activate if paid

    Args:
        message: Telegram message
        session: Database session
        user: User object
    """
    from bot.handlers.payment import payment_service

    if not payment_service:
        return

    try:
        # Get pending payments for this user
        result = await session.execute(
            select(Payment)
            .where(Payment.user_id == user.id)
            .where(Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.desc())
        )
        pending_payments = result.scalars().all()

        if not pending_payments:
            return

        logger.info(f"Checking {len(pending_payments)} pending payments for user {user.telegram_id}")

        # Check each pending payment
        for payment in pending_payments:
            status, payment_info = await payment_service.check_payment_status(payment.payment_id)

            if status == "succeeded" and payment_info and payment_info.get("paid"):
                # Activate access
                user.has_access = True
                user.current_day = 1
                user.course_started_at = dt_module.datetime.utcnow()

                # Update payment status
                payment.status = PaymentStatus.SUCCEEDED
                payment.paid_at = dt_module.datetime.utcnow()

                await session.commit()

                logger.info(f"✅ Auto-activated access for user {user.telegram_id} via payment {payment.payment_id}")

                # Send success message
                user_name = "Субъект X"
                await payment_service.send_payment_success_message(
                    chat_id=message.chat.id,
                    user_name=user_name
                )

                return  # Found successful payment, stop checking

    except Exception as e:
        logger.error(f"Error checking pending payments for user {user.telegram_id}: {e}", exc_info=True)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """
    Handle /start command
    Register new user or welcome back existing user
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Subject X"
    last_name = message.from_user.last_name

    logger.info(f"User {user_id} ({first_name}) started the bot")

    # Check if user exists
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Existing user
        # Don't update last_activity here - ActivityMiddleware handles it
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        await session.commit()

        if user.has_access:
            # User has access - show main menu
            # Get user's name from Day 1 Task 2
            user_display_name = await get_user_name_from_day1(session, user.id)

            await message.answer(
                f"⚡ **С возвращением, {user_display_name}!**\n\n"
                f"Ты на **Дне {user.current_day}/{COURSE_DAYS}**\n"
                f"Код освобождения: `{user.liberation_code or '___________'}`\n\n"
                f"Готов продолжить побег?",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard(user.current_day, user.has_access)
            )
        else:
            # User exists but no access - check for pending payments
            await check_pending_payments(message, session, user)

            # If still no access after check, show purchase option
            await session.refresh(user)
            if not user.has_access:
                await send_welcome_message(message, "Субъект X", is_new=False)

    else:
        # New user - create record
        # Detect timezone from user's language
        language_code = message.from_user.language_code
        detected_timezone = detect_timezone_from_language(language_code)

        new_user = User(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            has_access=False,
            current_day=0,
            timezone=detected_timezone,
        )
        session.add(new_user)
        await session.commit()

        logger.info(f"✅ New user registered: {user_id} ({first_name}), language: {language_code}, timezone: {detected_timezone}")

        # Send welcome message
        await send_welcome_message(message, "Субъект X", is_new=True)


async def send_welcome_message(message: Message, user_name: str, is_new: bool = True):
    """Send welcome message with course info"""

    greeting = "🔓 **Welcome to NeoVoice, Subject X**" if is_new else "⚡ **Welcome back, Subject X**"

    welcome_text = THEME_MESSAGES['welcome'].format(
        days=COURSE_DAYS,
        price=COURSE_PRICE,
        currency=COURSE_CURRENCY
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_welcome_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession):
    """Show help message"""
    user_id = message.from_user.id

    # Check if user has access
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if user and user.has_access:
        help_text = """
📚 **How to use the bot**

**Navigation:**
🎬 /day - Access current day's materials
📊 /progress - View your progress
💬 /help - Show this help

**Course Structure:**
Each day includes:
• Video briefing (cyberpunk story)
• PDF brief (vocabulary, grammar, dialogues)
• 3-4 interactive tasks

**Tasks:**
✅ **Choice** - Select correct answer (A/B/C/D)
🎤 **Voice** - Record yourself speaking
💬 **Dialog** - Interactive conversation

**Progress:**
Complete all tasks to unlock the next day.
Collect letters to form the secret code

**Tips:**
• Take your time with each task
• Watch videos carefully for clues
• Read briefs thoroughly
• Practice speaking out loud

Need support? Contact @your_support
"""
    else:
        help_text = """
📚 **About The Language Escape**

**What is it?**
A 10-day interactive English course in cyberpunk quest format.

**Who is it for?**
Beginners (A1-A2 level), ages 18-45, who want to learn English through gaming and sci-fi.

**What's included:**
🎬 10 days of cinematic videos
📄 PDF briefs with lessons
✍️ Interactive tasks with feedback
🎤 Voice challenges
💬 Dialog simulations
🏆 Certificate upon completion

**How to start:**
1. Use /pay to purchase access
2. Complete payment
3. Start Day 1 immediately!

**Price:** {price} {currency}

Questions? Contact @your_support
""".format(price=COURSE_PRICE, currency=COURSE_CURRENCY)

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("about"))
async def cmd_about(message: Message):
    """Show course information"""
    about_text = f"""
🌃 **{COURSE_NAME}**

**The Story:**
You wake up in NeoVoice, a simulation created by the ShadowNet corporation to erase your identity. Hackers are stealing words, leaving you voiceless. But there's hope...

A mysterious hacker, Emma, appears with a message: *"Learn to speak, and you'll break free."*

**Your Mission:**
• Complete {COURSE_DAYS} days of challenges
• Collect secret code letters day by day
• Escape the simulation

**What You'll Learn:**
• Basic English vocabulary (200+ words)
• Essential grammar structures
• Real-life conversations
• Pronunciation practice
• Confidence in speaking

**Format:**
📱 Fully in Telegram bot
🎯 Self-paced learning
⏱️ 20-30 minutes per day
🌍 Available 24/7

**Level:** Beginner (A1-A2)
**Languages:** English (with Russian support)

Ready to escape? Use /pay to start!
"""

    await message.answer(about_text, parse_mode="Markdown")


@router.callback_query(F.data == "show_help")
async def callback_help(callback: CallbackQuery, session: AsyncSession):
    """Handle help button"""
    user_id = callback.from_user.id

    # Check if user has access
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if user and user.has_access:
        help_text = (
            "📚 Как пользоваться ботом\n\n"
            "Навигация:\n"
            "🎬 /day - Материалы текущего дня\n"
            "📊 /progress - Твой прогресс\n"
            "💬 /help - Эта справка\n\n"
            "Структура курса:\n"
            "Каждый день включает:\n"
            "• Видео-брифинг (киберпанк история)\n"
            "• PDF-брифинг (слова, грамматика, диалоги)\n"
            "• 3-4 интерактивных задания\n\n"
            "Задания:\n"
            "✅ Выбор - Выбери правильный ответ (A/B/C/D)\n"
            "🎤 Голос - Запиши себя на английском\n"
            "💬 Диалог - Интерактивный разговор\n\n"
            "Прогресс:\n"
            "Выполни все задания, чтобы открыть следующий день.\n"
            "Собирай буквы секретного кода для побега\n\n"
            "Советы:\n"
            "• Не торопись с каждым заданием\n"
            "• Смотри видео внимательно - там подсказки\n"
            "• Читай брифинги тщательно\n"
            "• Практикуй произношение вслух\n\n"
            "Нужна поддержка? Напиши в поддержку"
        )
    else:
        help_text = (
            "📚 О курсе The Language Escape\n\n"
            "Что это?\n"
            "10-дневный интерактивный курс английского в формате киберпанк-квеста.\n\n"
            "Для кого?\n"
            "Начинающие (A1-A2), 18-45 лет, кто хочет учить английский через геймификацию и sci-fi.\n\n"
            "Что включено:\n"
            "🎬 10 дней кинематографичных видео\n"
            "📄 PDF-брифинги с уроками\n"
            "✍️ Интерактивные задания с обратной связью\n"
            "🎤 Голосовые челленджи\n"
            "💬 Симуляции диалогов\n"
            "🏆 Сертификат по завершению\n\n"
            "Как начать:\n"
            "1. Используй /pay для покупки доступа\n"
            "2. Завершить оплату\n"
            "3. Начать День 1 сразу!\n\n"
            f"Цена: {COURSE_PRICE} {COURSE_CURRENCY}\n\n"
            "Вопросы? Напиши в поддержку"
        )

    # Create back button keyboard
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_welcome"
        )]
    ])

    # Send as plain text without parse_mode to avoid entity parsing
    try:
        await callback.message.edit_text(help_text, parse_mode=None, reply_markup=back_keyboard)
    except Exception as e:
        logger.error(f"Error editing help message: {e}")
        await callback.answer("Ошибка отображения справки", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "back_to_welcome")
async def callback_back_to_welcome(callback: CallbackQuery):
    """Return to welcome message for unauthorized users"""
    welcome_text = THEME_MESSAGES['welcome'].format(
        days=COURSE_DAYS,
        price=COURSE_PRICE,
        currency=COURSE_CURRENCY
    )

    await callback.message.edit_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_welcome_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, session: AsyncSession):
    """Return to main menu"""
    user_id = callback.from_user.id

    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден. Используйте /start", show_alert=True)
        return

    menu_text = f"""
🎮 **Главное меню**

Текущий прогресс: День {user.current_day}/{COURSE_DAYS}
Собрано кода: `{user.liberation_code or '___________'}`

Выберите действие:
"""

    await callback.message.edit_text(
        menu_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(user.current_day, user.has_access)
    )
    await callback.answer()


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession):
    """Show main menu"""
    user_id = message.from_user.id

    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Пожалуйста, используйте /start")
        return

    if not user.has_access:
        await send_welcome_message(message, "Субъект X", is_new=False)
        return

    menu_text = f"""
🎮 **Главное меню**

Текущий прогресс: День {user.current_day}/{COURSE_DAYS}
Собрано кода: `{user.liberation_code or '___________'}`

Выберите действие:
"""

    await message.answer(
        menu_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(user.current_day, user.has_access)
    )
