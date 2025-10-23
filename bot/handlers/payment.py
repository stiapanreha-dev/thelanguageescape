"""
Payment handlers for YooKassa API integration
Handles payment creation and status checking
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import COURSE_NAME, COURSE_PRICE, COURSE_CURRENCY, COURSE_DAYS
from bot.services.payment import PaymentService
from bot.database.models import User

logger = logging.getLogger(__name__)

# Create router for payment handlers
router = Router(name="payment")

# Global payment service (will be initialized in main.py)
payment_service: PaymentService = None


def init_payment_service(bot: Bot):
    """
    Initialize payment service with bot instance

    Args:
        bot: Bot instance
    """
    global payment_service
    payment_service = PaymentService(bot)
    logger.info("✅ Payment service initialized with YooKassa API")


@router.message(Command("pay"))
async def cmd_pay(message: Message, session: AsyncSession):
    """
    Handle /pay command - create payment and send link
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name or "Субъект X"

    logger.info(f"User {user_id} ({user_name}) requested payment")

    # Check if payment service is initialized
    if not payment_service:
        await message.answer(
            "⚠️ Платёжная система временно недоступна. Попробуй позже."
        )
        logger.error("Payment service not initialized!")
        return

    # Get user from DB
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Используй /start сначала")
        return

    # Check if user already has access
    if user.has_access:
        await message.answer(
            "✅ У тебя уже есть доступ к курсу!\n"
            f"Текущий день: {user.current_day}/{COURSE_DAYS}\n\n"
            "Используй /day чтобы продолжить"
        )
        return

    # Create payment
    try:
        payment_id, payment_url = await payment_service.create_payment(
            user_id=user.id,
            telegram_id=user_id,
            amount=COURSE_PRICE
        )

        if not payment_id or not payment_url:
            await message.answer(
                "❌ Ошибка создания платежа. Попробуй ещё раз или напиши в поддержку."
            )
            return

        # Send payment link
        await payment_service.send_payment_link(
            chat_id=chat_id,
            payment_url=payment_url,
            amount=COURSE_PRICE
        )

        # Save pending payment to DB
        from bot.database.models import PaymentStatus
        await payment_service.save_payment_to_db(
            session=session,
            user_id=user.id,
            payment_id=payment_id,
            amount=COURSE_PRICE,
            currency=COURSE_CURRENCY,
            status=PaymentStatus.PENDING,
            description=f"{COURSE_NAME} - {COURSE_DAYS} дней",
            metadata={"telegram_id": str(user_id)}
        )

        logger.info(f"✅ Payment link sent to user {user_id}: {payment_id}")

    except Exception as e:
        logger.error(f"Error creating payment for user {user_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка создания платежа. Попробуй ещё раз или напиши в поддержку."
        )


@router.callback_query(F.data == "buy_course")
async def callback_buy_course(callback: CallbackQuery, session: AsyncSession):
    """
    Handle 'Buy Course' button press
    """
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    logger.info(f"User {user_id} clicked 'Buy Course' button")

    # Check if payment service is initialized
    if not payment_service:
        await callback.answer(
            "⚠️ Платёжная система временно недоступна.",
            show_alert=True
        )
        return

    # Get user from DB
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("Используй /start сначала", show_alert=True)
        return

    # Check if user already has access
    if user.has_access:
        await callback.answer(
            "✅ У тебя уже есть доступ к курсу!",
            show_alert=True
        )
        return

    # Create payment
    try:
        payment_id, payment_url = await payment_service.create_payment(
            user_id=user.id,
            telegram_id=user_id,
            amount=COURSE_PRICE
        )

        if not payment_id or not payment_url:
            await callback.answer(
                "❌ Ошибка создания платежа. Попробуй ещё раз.",
                show_alert=True
            )
            return

        # Send payment link
        await payment_service.send_payment_link(
            chat_id=chat_id,
            payment_url=payment_url,
            amount=COURSE_PRICE
        )

        # Save pending payment to DB
        from bot.database.models import PaymentStatus
        await payment_service.save_payment_to_db(
            session=session,
            user_id=user.id,
            payment_id=payment_id,
            amount=COURSE_PRICE,
            currency=COURSE_CURRENCY,
            status=PaymentStatus.PENDING,
            description=f"{COURSE_NAME} - {COURSE_DAYS} дней",
            metadata={"telegram_id": str(user_id)}
        )

        await callback.answer("💳 Ссылка на оплату отправлена!")
        logger.info(f"✅ Payment link sent to user {user_id}: {payment_id}")

    except Exception as e:
        logger.error(f"Error creating payment for user {user_id}: {e}", exc_info=True)
        await callback.answer(
            "❌ Ошибка создания платежа. Попробуй ещё раз.",
            show_alert=True
        )


@router.message(Command("check_payment"))
async def cmd_check_payment(message: Message, session: AsyncSession):
    """
    Manual payment status check (for testing and support)
    Usage: /check_payment <payment_id>
    """
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "Использование: /check_payment <payment_id>\n"
            "Пример: /check_payment 2d88ff3e-000f-5000-9000-1de86ca83bd5"
        )
        return

    payment_id = args[1].strip()

    logger.info(f"User {user_id} checking payment: {payment_id}")

    if not payment_service:
        await message.answer("⚠️ Платёжная система недоступна")
        return

    try:
        status, payment_info = await payment_service.check_payment_status(payment_id)

        if status == "succeeded" and payment_info and payment_info.get("paid"):
            # Grant access
            success = await payment_service.grant_access_after_payment(
                session=session,
                telegram_id=user_id,
                payment_id=payment_id
            )

            if success:
                user_name = message.from_user.first_name or "Субъект X"
                await payment_service.send_payment_success_message(
                    chat_id=message.chat.id,
                    user_name=user_name
                )
            else:
                await message.answer("❌ Ошибка предоставления доступа")

        elif status == "pending" or status == "waiting_for_capture":
            await message.answer(
                f"⏳ Платёж в обработке\n"
                f"Статус: {status}\n"
                f"ID: `{payment_id}`",
                parse_mode="Markdown"
            )
        elif status == "canceled":
            await message.answer(
                f"❌ Платёж отменён\n"
                f"ID: `{payment_id}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"ℹ️ Статус платежа: {status}\n"
                f"ID: `{payment_id}`",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error checking payment {payment_id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка проверки платежа")


# Helper function to create payment keyboard
def get_payment_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with payment button"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Купить курс - {COURSE_PRICE} {COURSE_CURRENCY}",
            callback_data="buy_course"
        )],
        [InlineKeyboardButton(
            text="ℹ️ О курсе",
            callback_data="course_info"
        )],
    ])
    return keyboard


@router.callback_query(F.data == "course_info")
async def callback_course_info(callback: CallbackQuery):
    """Show course information"""
    info_text = f"""
📚 **{COURSE_NAME}**

**Что ты получишь:**
🎯 {COURSE_DAYS} дней интерактивных уроков
🎬 Видео в киберпанк стиле
📄 PDF брифинги со словами и грамматикой
✍️ Интерактивные задания с мгновенной обратной связью
🎤 Голосовые челленджи
💬 Симуляции диалогов
🏆 Сертификат по завершению

**Цена:** {COURSE_PRICE} {COURSE_CURRENCY}
**Уровень:** A1-A2 (Начальный)
**Формат:** В своём темпе через Telegram бот

Готов сбежать из симуляции?
"""

    # Separate keyboard for course info screen (with Back button)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Купить курс - {COURSE_PRICE} {COURSE_CURRENCY}",
            callback_data="buy_course"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_welcome"
        )],
    ])

    try:
        await callback.message.edit_text(
            info_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception:
        # Ignore if message is the same (user clicked button again)
        pass

    await callback.answer()


@router.callback_query(F.data == "back_to_welcome")
async def callback_back_to_welcome(callback: CallbackQuery):
    """Go back to welcome screen"""
    from bot.config import THEME_MESSAGES

    user_name = callback.from_user.first_name or "Субъект X"

    welcome_text = THEME_MESSAGES['welcome'].format(
        days=COURSE_DAYS,
        price=COURSE_PRICE,
        currency=COURSE_CURRENCY,
        code="LIBERATION"
    )

    # Replace Subject X with actual name
    welcome_text = welcome_text.replace("Субъект X", user_name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Купить курс - {COURSE_PRICE} {COURSE_CURRENCY}",
            callback_data="buy_course"
        )],
        [InlineKeyboardButton(
            text="📚 О курсе",
            callback_data="course_info"
        )],
        [InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="show_help"
        )],
    ])

    try:
        await callback.message.edit_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception:
        pass

    await callback.answer()
