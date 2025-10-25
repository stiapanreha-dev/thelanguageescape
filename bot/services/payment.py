"""
Payment service for YooKassa API integration
Handles payment creation, confirmation, and webhooks
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration, Payment as YooPayment

from bot.config import (
    COURSE_NAME,
    COURSE_PRICE,
    COURSE_CURRENCY,
    COURSE_DAYS,
    YOOKASSA_SHOP_ID,
    YOOKASSA_SECRET_KEY,
)
from bot.database.models import User, Payment, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling YooKassa payments"""

    def __init__(self, bot: Bot):
        self.bot = bot

        # Configure YooKassa
        Configuration.account_id = YOOKASSA_SHOP_ID
        Configuration.secret_key = YOOKASSA_SECRET_KEY

        logger.info(f"✅ YooKassa configured: Shop ID {YOOKASSA_SHOP_ID}")

    async def create_payment(
        self,
        user_id: int,
        telegram_id: int,
        amount: float = None,
        description: str = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Create payment via YooKassa API

        Args:
            user_id: Internal user ID
            telegram_id: Telegram user ID
            amount: Payment amount (default: COURSE_PRICE)
            description: Payment description

        Returns:
            Tuple of (payment_id, confirmation_url) or (None, None) on error
        """
        if amount is None:
            amount = COURSE_PRICE

        if description is None:
            description = f"{COURSE_NAME} - {COURSE_DAYS} дней"

        try:
            # Create unique idempotence key
            idempotence_key = str(uuid.uuid4())

            # Create payment
            # Get bot info for return URL
            bot_info = await self.bot.get_me()
            bot_username = bot_info.username

            payment = YooPayment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": COURSE_CURRENCY
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{bot_username}?start=payment_check"  # Auto-trigger payment check
                },
                "capture": True,  # Auto-capture payment
                "description": description,
                "metadata": {
                    "telegram_id": str(telegram_id),
                    "user_id": str(user_id),
                }
            }, idempotence_key)

            payment_id = payment.id
            confirmation_url = payment.confirmation.confirmation_url

            logger.info(f"✅ Payment created: {payment_id} for user {telegram_id}")

            return payment_id, confirmation_url

        except Exception as e:
            logger.error(f"Error creating payment for user {telegram_id}: {e}", exc_info=True)
            return None, None

    async def check_payment_status(
        self,
        payment_id: str
    ) -> tuple[str, Optional[Dict]]:
        """
        Check payment status via YooKassa API

        Args:
            payment_id: YooKassa payment ID

        Returns:
            Tuple of (status, payment_info)
        """
        try:
            payment = YooPayment.find_one(payment_id)

            return payment.status, {
                "id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency,
                "created_at": payment.created_at,
                "metadata": payment.metadata,
            }

        except Exception as e:
            logger.error(f"Error checking payment {payment_id}: {e}", exc_info=True)
            return "error", None

    async def save_payment_to_db(
        self,
        session: AsyncSession,
        user_id: int,
        payment_id: str,
        amount: float,
        currency: str,
        status: PaymentStatus,
        description: str = None,
        metadata: Dict = None
    ) -> Payment:
        """
        Save payment record to database

        Args:
            session: Database session
            user_id: Internal user ID
            payment_id: YooKassa payment ID
            amount: Payment amount
            currency: Currency code
            status: Payment status
            description: Optional description
            metadata: Optional metadata

        Returns:
            Payment object
        """
        payment = Payment(
            user_id=user_id,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=status,
            description=description or f"Course purchase: {COURSE_NAME}",
            payment_method="yookassa",
            payment_metadata=metadata,
            paid_at=datetime.utcnow() if status == PaymentStatus.SUCCEEDED else None
        )

        session.add(payment)
        await session.commit()

        logger.info(f"💾 Payment saved to DB: {payment_id} - {status.value}")

        return payment

    async def grant_access_after_payment(
        self,
        session: AsyncSession,
        telegram_id: int,
        payment_id: str
    ) -> bool:
        """
        Grant course access to user after successful payment

        Args:
            session: Database session
            telegram_id: Telegram user ID
            payment_id: YooKassa payment ID

        Returns:
            True if access granted successfully
        """
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {telegram_id} not found for payment {payment_id}")
                return False

            # Check payment status
            status, payment_info = await self.check_payment_status(payment_id)

            if status != "succeeded" or not payment_info or not payment_info.get("paid"):
                logger.warning(f"Payment {payment_id} not succeeded: {status}")
                return False

            # Grant access
            user.has_access = True
            user.current_day = 1
            user.course_started_at = datetime.utcnow()

            # Save payment to DB
            await self.save_payment_to_db(
                session=session,
                user_id=user.id,
                payment_id=payment_id,
                amount=payment_info["amount"],
                currency=payment_info["currency"],
                status=PaymentStatus.SUCCEEDED,
                metadata=payment_info.get("metadata")
            )

            await session.commit()

            logger.info(f"✅ Access granted to user {telegram_id} after payment {payment_id}")

            return True

        except Exception as e:
            logger.error(f"Error granting access for payment {payment_id}: {e}", exc_info=True)
            await session.rollback()
            return False

    async def send_payment_link(
        self,
        chat_id: int,
        payment_url: str,
        amount: float = None
    ):
        """
        Send payment link to user

        Args:
            chat_id: Chat ID to send message
            payment_url: YooKassa payment URL
            amount: Payment amount
        """
        if amount is None:
            amount = COURSE_PRICE

        message_text = f"""
💳 **Оплата курса**

**Сумма:** {amount} {COURSE_CURRENCY}
**Курс:** {COURSE_NAME}
**Доступ:** {COURSE_DAYS} дней

Нажми кнопку ниже для оплаты.
После успешной оплаты доступ откроется автоматически!

🔒 Безопасная оплата через YooKassa
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Оплатить {amount} {COURSE_CURRENCY}",
                url=payment_url
            )],
            [InlineKeyboardButton(
                text="❓ Помощь",
                callback_data="show_help"
            )],
        ])

        await self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    async def send_payment_success_message(
        self,
        chat_id: int,
        user_name: str = "Субъект X"
    ):
        """
        Send success message after payment

        Args:
            chat_id: Chat ID to send message
            user_name: User's first name
        """
        success_text = f"""
🎉 **Оплата прошла успешно!**

Добро пожаловать в **{COURSE_NAME}**, {user_name}!

✅ Теперь у тебя есть полный доступ ко всем {COURSE_DAYS} дням
🔓 Твой путь к свободе начинается сейчас

**Что дальше?**
🎬 День 1 готов - нажми кнопку ниже
📚 Выполняй задания, собирай секретные буквы кода
🏆 Получи сертификат свободы

Симуляция ждёт... Готов сбежать?
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать День 1", callback_data="start_day_1")],
            [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="show_progress")],
        ])

        await self.bot.send_message(
            chat_id=chat_id,
            text=success_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    async def send_payment_failed_message(
        self,
        chat_id: int,
        error_message: str = None
    ):
        """
        Send failure message if payment failed

        Args:
            chat_id: Chat ID to send message
            error_message: Optional error description
        """
        failed_text = f"""
❌ **Оплата не прошла**

{error_message or "Что-то пошло не так с оплатой."}

**Что делать:**
1. Проверь данные карты
2. Убедись, что достаточно средств
3. Попробуй снова или свяжись с поддержкой

Нужна помощь? Напиши в поддержку
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="buy_course")],
            [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/your_support")],
        ])

        await self.bot.send_message(
            chat_id=chat_id,
            text=failed_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    @staticmethod
    async def get_user_payments(
        session: AsyncSession,
        user_id: int
    ) -> list[Payment]:
        """
        Get all payments for a user

        Args:
            session: Database session
            user_id: Internal user ID (not telegram_id)

        Returns:
            List of Payment objects
        """
        result = await session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def check_user_access(
        session: AsyncSession,
        telegram_id: int
    ) -> bool:
        """
        Check if user has paid access

        Args:
            session: Database session
            telegram_id: Telegram user ID

        Returns:
            True if user has access
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        return user.has_access if user else False


# Helper function to format payment info
def format_payment_info(payment: Payment) -> str:
    """Format payment information for display"""
    return f"""
💳 **Payment #{payment.id}**

**Amount:** {payment.amount} {payment.currency}
**Status:** {payment.status.value}
**Date:** {payment.paid_at.strftime('%Y-%m-%d %H:%M') if payment.paid_at else 'N/A'}
**Payment ID:** `{payment.payment_id}`
"""
