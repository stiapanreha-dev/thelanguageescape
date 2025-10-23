"""
Main entry point for The Language Escape Bot
Initializes bot, registers handlers, and starts polling
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    YOOKASSA_PROVIDER_TOKEN,
    LOG_LEVEL,
    LOG_FORMAT,
    LOGS_PATH
)
from bot.database.database import init_db, check_db_connection, get_session

# Import handlers
from bot.handlers import start, payment, course, tasks
from bot.handlers.payment import init_payment_service
from bot.handlers.tasks import init_task_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_PATH / 'bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """
    Actions to perform on bot startup
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting The Language Escape Bot")
    logger.info("=" * 60)

    # Check database connection
    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("❌ Database connection failed!")
        logger.error("Please check your DATABASE_URL in .env")
        sys.exit(1)

    # Initialize database tables
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    # Initialize payment service
    if YOOKASSA_PROVIDER_TOKEN:
        init_payment_service(bot, YOOKASSA_PROVIDER_TOKEN)
        logger.info("✅ Payment service initialized")
    else:
        logger.warning("⚠️  YooKassa Provider Token not set - payments disabled")

    # Initialize task service
    init_task_service()

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"✅ Bot started: @{bot_info.username} (ID: {bot_info.id})")
    logger.info(f"📱 Bot name: {bot_info.first_name}")
    logger.info("=" * 60)


async def on_shutdown(bot: Bot):
    """
    Actions to perform on bot shutdown
    """
    logger.info("=" * 60)
    logger.info("🛑 Shutting down The Language Escape Bot")
    logger.info("=" * 60)

    await bot.session.close()


def register_handlers(dp: Dispatcher):
    """
    Register all handlers with the dispatcher

    Args:
        dp: Aiogram Dispatcher
    """
    # Register routers in order of priority
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(course.router)
    dp.include_router(tasks.router)

    logger.info("✅ Handlers registered")


async def main():
    """
    Main function to run the bot
    """
    # Validate configuration
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env file!")
        sys.exit(1)

    # Create bot instance
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN
        )
    )

    # Create dispatcher
    dp = Dispatcher()

    # Register handlers
    register_handlers(dp)

    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Inject database session into handlers
    @dp.update.middleware()
    async def db_session_middleware(handler, event, data):
        """Middleware to inject database session"""
        async for session in get_session():
            data['session'] = session
            return await handler(event, data)

    # Start polling
    try:
        logger.info("🔄 Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"❌ Error during polling: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️  Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
