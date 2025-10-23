"""
Payment handlers for Telegram bot
Handles invoice sending, pre-checkout, and successful payment
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import COURSE_NAME, COURSE_PRICE, COURSE_CURRENCY, COURSE_DAYS
from bot.services.payment import PaymentService
from bot.database.database import get_session

logger = logging.getLogger(__name__)

# Create router for payment handlers
router = Router(name="payment")

# Global payment service (will be initialized in main.py)
payment_service: PaymentService = None


def init_payment_service(bot: Bot, provider_token: str):
    """Initialize payment service with bot and provider token"""
    global payment_service
    payment_service = PaymentService(bot, provider_token)
    logger.info("Payment service initialized")


@router.message(Command("pay"))
async def cmd_pay(message: Message):
    """
    Handle /pay command - send invoice to user
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name or "Subject X"

    logger.info(f"User {user_id} ({user_name}) requested payment")

    # Check if payment service is initialized
    if not payment_service:
        await message.answer(
            "⚠️ Payment system is currently unavailable. Please try again later."
        )
        logger.error("Payment service not initialized!")
        return

    # Send invoice
    try:
        await payment_service.create_invoice(
            user_id=user_id,
            chat_id=chat_id
        )

        # Send additional info message
        info_text = f"""
💰 **Payment Information**

**Course:** {COURSE_NAME}
**Price:** {COURSE_PRICE} {COURSE_CURRENCY}
**Duration:** {COURSE_DAYS} days

After payment you'll get:
✅ Instant access to all {COURSE_DAYS} days
🎬 Videos, PDFs, and interactive tasks
🏆 Certificate upon completion
📱 Progress tracking

**Secure payment** powered by Telegram Payments + YooKassa
"""

        await message.answer(
            info_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error sending invoice to user {user_id}: {e}")
        await message.answer(
            "❌ Error creating invoice. Please try again or contact support."
        )


@router.callback_query(F.data == "buy_course")
async def callback_buy_course(callback: CallbackQuery):
    """
    Handle 'Buy Course' button press
    """
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    logger.info(f"User {user_id} clicked 'Buy Course' button")

    # Check if payment service is initialized
    if not payment_service:
        await callback.answer(
            "⚠️ Payment system is currently unavailable.",
            show_alert=True
        )
        return

    # Send invoice
    try:
        await payment_service.create_invoice(
            user_id=user_id,
            chat_id=chat_id
        )

        await callback.answer("📧 Invoice sent! Check the message above.")

    except Exception as e:
        logger.error(f"Error sending invoice to user {user_id}: {e}")
        await callback.answer(
            "❌ Error creating invoice. Please try again.",
            show_alert=True
        )


@router.pre_checkout_query()
async def process_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
    session: AsyncSession
):
    """
    Handle pre-checkout query
    This is called when user presses "Pay" button in invoice
    """
    user_id = pre_checkout_query.from_user.id

    logger.info(f"Pre-checkout query from user {user_id}")

    # Check if payment service is initialized
    if not payment_service:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Payment system is temporarily unavailable."
        )
        logger.error("Payment service not initialized during pre-checkout!")
        return

    # Process pre-checkout validation
    await payment_service.process_pre_checkout(
        pre_checkout_query=pre_checkout_query,
        session=session
    )


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    session: AsyncSession
):
    """
    Handle successful payment
    This is called after payment is completed
    """
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Subject X"
    chat_id = message.chat.id

    logger.info(f"✅ Successful payment from user {user_id}")

    # Check if payment service is initialized
    if not payment_service:
        await message.answer(
            "⚠️ Payment received but system error occurred. Please contact support."
        )
        logger.error("Payment service not initialized during successful payment!")
        return

    # Process payment and grant access
    success = await payment_service.process_successful_payment(
        message=message,
        session=session
    )

    if success:
        # Send success message with cyberpunk style
        await payment_service.send_payment_success_message(
            chat_id=chat_id,
            user_name=user_name
        )

        logger.info(f"✅ Access granted to user {user_id}")

    else:
        # Send error message
        await message.answer(
            "❌ Payment processed but error granting access. Please contact support with this payment ID:\n"
            f"`{message.successful_payment.telegram_payment_charge_id}`",
            parse_mode="Markdown"
        )

        logger.error(f"Failed to grant access to user {user_id} after successful payment")


@router.message(Command("check_payment"))
async def cmd_check_payment(message: Message, session: AsyncSession):
    """
    Check user's payment status and access
    """
    user_id = message.from_user.id

    # Check access
    has_access = await payment_service.check_user_access(
        session=session,
        telegram_id=user_id
    )

    if has_access:
        await message.answer(
            "✅ You have **active access** to the course!",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ You don't have access yet. Use /pay to purchase the course.",
            parse_mode="Markdown"
        )


# Helper function to create payment keyboard
def get_payment_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with payment button"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Buy Course - {COURSE_PRICE} {COURSE_CURRENCY}",
            callback_data="buy_course"
        )],
        [InlineKeyboardButton(
            text="ℹ️ Course Info",
            callback_data="course_info"
        )],
    ])
    return keyboard


@router.callback_query(F.data == "course_info")
async def callback_course_info(callback: CallbackQuery):
    """Show course information"""
    info_text = f"""
📚 **{COURSE_NAME}**

**What you'll get:**
🎯 {COURSE_DAYS} days of interactive lessons
🎬 Video content in cyberpunk style
📄 PDF briefs with vocabulary and grammar
✍️ Interactive tasks with instant feedback
🎤 Voice challenges
💬 Dialog simulations
🏆 Certificate upon completion

**Price:** {COURSE_PRICE} {COURSE_CURRENCY}
**Level:** A1-A2 (Beginner)
**Format:** Self-paced through Telegram bot

Ready to escape the simulation?
"""

    keyboard = get_payment_keyboard()

    await callback.message.edit_text(
        info_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await callback.answer()
