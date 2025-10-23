"""
YooKassa webhook handler
Receives payment notifications and activates access automatically
"""
import logging
import hmac
import hashlib
from aiohttp import web
from sqlalchemy import select
from yookassa import Payment as YooPayment

from bot.config import YOOKASSA_SECRET_KEY
from bot.database.database import async_session_maker
from bot.database.models import User, Payment, PaymentStatus
from bot.services.payment import PaymentService

logger = logging.getLogger(__name__)

# Global payment service reference
payment_service: PaymentService = None


def set_payment_service(service: PaymentService):
    """Set global payment service reference"""
    global payment_service
    payment_service = service


async def yookassa_webhook(request: web.Request) -> web.Response:
    """
    Handle YooKassa payment notification webhook

    YooKassa sends POST request to this endpoint when payment status changes
    """
    try:
        # Get request body
        body = await request.read()

        # Parse JSON
        import json
        data = json.loads(body.decode('utf-8'))

        logger.info(f"📥 Received YooKassa webhook: {data.get('event')}")

        # Extract payment info
        event = data.get('event')
        payment_obj = data.get('object')

        if not payment_obj:
            logger.error("No payment object in webhook")
            return web.json_response({'error': 'No payment object'}, status=400)

        payment_id = payment_obj.get('id')
        payment_status = payment_obj.get('status')

        logger.info(f"Payment {payment_id} status: {payment_status}")

        # Handle successful payment
        if event == 'payment.succeeded' and payment_status == 'succeeded':
            await handle_successful_payment(payment_id, payment_obj)

        # Handle canceled payment
        elif event == 'payment.canceled' and payment_status == 'canceled':
            await handle_canceled_payment(payment_id)

        return web.json_response({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return web.json_response({'error': str(e)}, status=500)


async def handle_successful_payment(payment_id: str, payment_obj: dict):
    """
    Handle successful payment notification
    Grant access to user
    """
    try:
        # Get telegram_id from metadata
        metadata = payment_obj.get('metadata', {})
        telegram_id = metadata.get('telegram_id')

        if not telegram_id:
            logger.error(f"No telegram_id in payment {payment_id} metadata")
            return

        telegram_id = int(telegram_id)

        logger.info(f"💰 Processing successful payment {payment_id} for user {telegram_id}")

        # Create DB session
        async with async_session_maker() as session:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {telegram_id} not found for payment {payment_id}")
                return

            # Check if user already has access
            if user.has_access:
                logger.info(f"User {telegram_id} already has access")
                return

            # Grant access
            from datetime import datetime
            user.has_access = True
            user.current_day = 1
            user.course_started_at = datetime.utcnow()

            # Update payment status in DB
            result = await session.execute(
                select(Payment).where(Payment.payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.SUCCEEDED
                payment.paid_at = datetime.utcnow()

            await session.commit()

            logger.info(f"✅ Access granted to user {telegram_id} via webhook")

            # Send success message to user
            if payment_service:
                user_name = "Субъект X"
                await payment_service.send_payment_success_message(
                    chat_id=telegram_id,
                    user_name=user_name
                )
                logger.info(f"📧 Success message sent to user {telegram_id}")

    except Exception as e:
        logger.error(f"Error handling successful payment {payment_id}: {e}", exc_info=True)


async def handle_canceled_payment(payment_id: str):
    """
    Handle canceled payment notification
    Update payment status in DB
    """
    try:
        logger.info(f"❌ Payment {payment_id} canceled")

        async with async_session_maker() as session:
            result = await session.execute(
                select(Payment).where(Payment.payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.CANCELED
                await session.commit()
                logger.info(f"💾 Payment {payment_id} marked as canceled in DB")

    except Exception as e:
        logger.error(f"Error handling canceled payment {payment_id}: {e}", exc_info=True)


def setup_webhook_routes(app: web.Application):
    """
    Setup webhook routes in aiohttp app

    Args:
        app: aiohttp Application instance
    """
    app.router.add_post('/webhook/yookassa', yookassa_webhook)
    logger.info("✅ YooKassa webhook route configured: POST /webhook/yookassa")
