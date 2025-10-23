"""
Start and basic command handlers
Registration, welcome messages, help
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import COURSE_NAME, COURSE_PRICE, COURSE_CURRENCY, COURSE_DAYS, THEME_MESSAGES
from bot.database.models import User
from bot.keyboards.inline import get_welcome_keyboard, get_main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router(name="start")


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
        user.last_activity = message.date
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        await session.commit()

        if user.has_access:
            # User has access - show main menu
            await message.answer(
                f"⚡ **Welcome back, {first_name}!**\n\n"
                f"You're on **Day {user.current_day}/{COURSE_DAYS}**\n"
                f"Liberation code: `{user.liberation_code or '___________'}`\n\n"
                f"Ready to continue your escape?",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard(user.current_day, user.has_access)
            )
        else:
            # User exists but no access - show purchase option
            await send_welcome_message(message, first_name, is_new=False)

    else:
        # New user - create record
        new_user = User(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            has_access=False,
            current_day=0,
        )
        session.add(new_user)
        await session.commit()

        logger.info(f"✅ New user registered: {user_id} ({first_name})")

        # Send welcome message
        await send_welcome_message(message, first_name, is_new=True)


async def send_welcome_message(message: Message, user_name: str, is_new: bool = True):
    """Send welcome message with course info"""

    greeting = "🔓 **Welcome to NeoVoice, Subject X**" if is_new else "⚡ **Welcome back, Subject X**"

    welcome_text = THEME_MESSAGES['welcome'].format(
        days=COURSE_DAYS,
        price=COURSE_PRICE,
        currency=COURSE_CURRENCY,
        code="LIBERATION"
    )

    # Replace Subject X with actual name
    welcome_text = welcome_text.replace("Subject X", user_name)

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
Collect letters to form the code: **LIBERATION**

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
• Collect letters to form the code LIBERATION
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
async def callback_help(callback: CallbackQuery):
    """Handle help button"""
    await callback.message.delete()
    await cmd_help(callback.message, callback.message.chat.id)
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
        await callback.answer("User not found. Use /start", show_alert=True)
        return

    menu_text = f"""
🎮 **Main Menu**

Current progress: Day {user.current_day}/{COURSE_DAYS}
Code collected: `{user.liberation_code or '___________'}`

Choose an action:
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
        await message.answer("Please use /start first")
        return

    if not user.has_access:
        await send_welcome_message(message, user.first_name or "Subject X", is_new=False)
        return

    menu_text = f"""
🎮 **Main Menu**

Current progress: Day {user.current_day}/{COURSE_DAYS}
Code collected: `{user.liberation_code or '___________'}`

Choose an action below:
"""

    await message.answer(
        menu_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(user.current_day, user.has_access)
    )
