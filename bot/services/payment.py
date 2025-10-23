"""
Payment service for Telegram Payments + YooKassa integration
Handles invoice creation, payment processing, and access granting
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import (
    LabeledPrice,
    PreCheckoutQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import (
    COURSE_NAME,
    COURSE_PRICE,
    COURSE_CURRENCY,
    COURSE_DAYS,
)
from bot.database.models import User, Payment, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling payments"""

    def __init__(self, bot: Bot, provider_token: str):
        self.bot = bot
        self.provider_token = provider_token

    async def create_invoice(
        self,
        user_id: int,
        chat_id: int,
        title: str = None,
        description: str = None,
    ) -> Message:
        """
        Create and send payment invoice to user

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID to send invoice
            title: Invoice title (optional)
            description: Invoice description (optional)

        Returns:
            Sent message with invoice
        """
        # Default title and description
        if not title:
            title = f"{COURSE_NAME} - {COURSE_DAYS} Days"

        if not description:
            description = (
                f"🔓 Access to {COURSE_DAYS}-day cyberpunk English quest\n"
                f"🎯 Unlock {COURSE_DAYS} days of videos, tasks, and challenges\n"
                f"📜 Certificate upon completion\n"
                f"⚡ Instant access after payment"
            )

        # Price in smallest currency unit (kopecks for RUB)
        prices = [
            LabeledPrice(
                label=f"{COURSE_NAME}",
                amount=COURSE_PRICE * 100  # Convert rubles to kopecks
            )
        ]

        # Create payload with user_id for verification
        payload = f"course_payment_{user_id}_{datetime.utcnow().timestamp()}"

        # Send invoice
        message = await self.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=self.provider_token,
            currency=COURSE_CURRENCY,
            prices=prices,
            start_parameter=f"pay_{user_id}",
            photo_url="https://i.imgur.com/your_course_image.jpg",  # Optional course image
            photo_size=512,
            photo_width=512,
            photo_height=512,
            need_name=False,
            need_phone_number=False,
            need_email=True,  # Collect email for certificate
            need_shipping_address=False,
            is_flexible=False,
            send_phone_number_to_provider=False,
            send_email_to_provider=True,
        )

        logger.info(f"Invoice sent to user {user_id}, payload: {payload}")
        return message

    async def process_pre_checkout(
        self,
        pre_checkout_query: PreCheckoutQuery,
        session: AsyncSession
    ) -> bool:
        """
        Process pre-checkout query (before payment)
        Validate payment and user

        Args:
            pre_checkout_query: Telegram PreCheckoutQuery
            session: Database session

        Returns:
            True if validation passed, False otherwise
        """
        user_id = pre_checkout_query.from_user.id
        payload = pre_checkout_query.invoice_payload

        logger.info(f"Pre-checkout from user {user_id}, payload: {payload}")

        # Validate payload format
        if not payload.startswith("course_payment_"):
            logger.error(f"Invalid payload format: {payload}")
            await pre_checkout_query.answer(
                ok=False,
                error_message="Invalid payment request. Please try again."
            )
            return False

        # Extract user_id from payload
        try:
            payload_user_id = int(payload.split("_")[2])
        except (IndexError, ValueError):
            logger.error(f"Cannot extract user_id from payload: {payload}")
            await pre_checkout_query.answer(
                ok=False,
                error_message="Invalid payment request. Please contact support."
            )
            return False

        # Verify user_id matches
        if payload_user_id != user_id:
            logger.error(f"User ID mismatch: {user_id} != {payload_user_id}")
            await pre_checkout_query.answer(
                ok=False,
                error_message="Payment verification failed. Please try again."
            )
            return False

        # Check if user exists in database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {user_id} not found in database")
            await pre_checkout_query.answer(
                ok=False,
                error_message="User not found. Please use /start first."
            )
            return False

        # Check if user already has access
        if user.has_access:
            logger.warning(f"User {user_id} already has access")
            await pre_checkout_query.answer(
                ok=False,
                error_message="You already have access to the course!"
            )
            return False

        # All checks passed
        await pre_checkout_query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user_id}")
        return True

    async def process_successful_payment(
        self,
        message: Message,
        session: AsyncSession
    ) -> bool:
        """
        Process successful payment
        Grant access to course and save payment info

        Args:
            message: Message with successful_payment
            session: Database session

        Returns:
            True if processing succeeded
        """
        user_id = message.from_user.id
        payment_info = message.successful_payment

        logger.info(f"Processing successful payment from user {user_id}")
        logger.info(f"Payment info: {payment_info}")

        try:
            # Get user from database
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found during payment processing")
                return False

            # Update user email if provided
            if payment_info.order_info and payment_info.order_info.email:
                user.email = payment_info.order_info.email

            # Grant access
            user.has_access = True
            user.current_day = 1  # Start from day 1
            user.course_started_at = datetime.utcnow()

            # Save payment record
            payment = Payment(
                user_id=user.id,
                payment_id=payment_info.telegram_payment_charge_id,
                amount=payment_info.total_amount / 100,  # Convert kopecks to rubles
                currency=payment_info.currency,
                status=PaymentStatus.SUCCEEDED,
                description=f"Course purchase: {COURSE_NAME}",
                payment_method="telegram_payments",
                paid_at=datetime.utcnow(),
                payment_metadata={
                    "provider_payment_charge_id": str(payment_info.provider_payment_charge_id) if payment_info.provider_payment_charge_id else None,
                    "invoice_payload": str(payment_info.invoice_payload) if payment_info.invoice_payload else None,
                }
            )

            session.add(payment)
            await session.commit()

            logger.info(f"✅ Payment processed successfully for user {user_id}")
            logger.info(f"Payment ID: {payment_info.telegram_payment_charge_id}")

            return True

        except Exception as e:
            logger.error(f"Error processing payment for user {user_id}: {e}")
            await session.rollback()
            return False

    async def send_payment_success_message(
        self,
        chat_id: int,
        user_name: str = "Subject X"
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
📚 Выполняй задания, чтобы собрать код LIBERATION
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
