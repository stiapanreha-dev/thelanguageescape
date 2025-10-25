"""
Inline query handler for sharing certificates
"""
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultCachedPhoto
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import User, Certificate

logger = logging.getLogger(__name__)

router = Router()


@router.inline_query(F.query == "certificate")
async def inline_share_certificate(inline_query: InlineQuery, session: AsyncSession):
    """
    Handle inline query for sharing certificate
    User clicks "Share Certificate" button -> chooses chat -> sends certificate
    """
    user_id = inline_query.from_user.id

    try:
        # Get user's certificate from database
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Return empty result if user not found
            await inline_query.answer([], cache_time=1)
            return

        # Get latest certificate
        result = await session.execute(
            select(Certificate).where(Certificate.user_id == user.id).order_by(Certificate.id.desc()).limit(1)
        )
        certificate = result.scalar_one_or_none()

        if not certificate or not certificate.file_id:
            # Return empty result if no certificate
            await inline_query.answer([], cache_time=1)
            return

        # Create share text (cap accuracy at 100%)
        accuracy_capped = min(100.0, certificate.accuracy)
        share_text = f"""🎉 Я завершил курс The Language Escape!

🔑 Код освобождения: {certificate.final_code}
✅ Точность: {accuracy_capped:.1f}%
📅 Завершено: {certificate.completion_date.strftime('%d.%m.%Y')}

💡 Присоединяйся к курсу английского языка в киберпанк стилистике!

🌟 Начни обучение: @thelanguageescape_bot"""

        # Create inline result with cached photo
        results = [
            InlineQueryResultCachedPhoto(
                id="certificate_share",
                title="🎓 Сертификат о прохождении курса",
                description="Поделиться сертификатом The Language Escape",
                photo_file_id=certificate.file_id,
                caption=share_text
            )
        ]

        await inline_query.answer(results, cache_time=300)
        logger.info(f"✅ Inline query answered for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling inline query for user {user_id}: {e}", exc_info=True)
        # Return empty result on error
        await inline_query.answer([], cache_time=1)
