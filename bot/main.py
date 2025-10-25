"""
Main entry point for The Language Escape Bot
Initializes bot, registers handlers, and starts polling
"""
import asyncio
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    YOOKASSA_SHOP_ID,
    YOOKASSA_SECRET_KEY,
    LOG_LEVEL,
    LOG_FORMAT,
    LOGS_PATH,
    WEBHOOK_ENABLED,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    WEBHOOK_PORT,
    WEBAPP_HOST
)
from bot.database.database import init_db, check_db_connection, get_session

# Import handlers
from bot.handlers import start, payment, course, tasks, admin, inline
from bot.handlers.payment import init_payment_service
from bot.handlers.tasks import init_task_service

# Import middlewares
from bot.middlewares.admin import AdminMiddleware
from bot.middlewares.activity import ActivityMiddleware
from bot.middlewares.user_logger import user_action_logger

# Import services
from bot.services.reminders import initialize_reminder_service
from bot.services.scheduler import scheduler_service

# Configure logging with rotation
# Ensure logs directory exists
LOGS_PATH.mkdir(parents=True, exist_ok=True)

# Create rotating file handler (max 10MB per file, keep 5 backups)
file_handler = RotatingFileHandler(
    LOGS_PATH / 'bot.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(getattr(logging, LOG_LEVEL))
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    handlers=[console_handler, file_handler]
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

    # Initialize payment service (YooKassa API)
    if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
        init_payment_service(bot)
        logger.info("✅ Payment service initialized with YooKassa API")
    else:
        logger.warning("⚠️  YooKassa credentials not set - payments disabled")

    # Initialize task service
    init_task_service()

    # Initialize reminder service
    initialize_reminder_service(bot)
    logger.info("✅ Reminder service initialized")

    # Start scheduler for automated tasks
    scheduler_service.start()
    logger.info("✅ Scheduler started")

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

    # Stop scheduler
    scheduler_service.stop()
    logger.info("✅ Scheduler stopped")

    await bot.session.close()


def register_handlers(dp: Dispatcher):
    """
    Register all handlers with the dispatcher

    Args:
        dp: Aiogram Dispatcher
    """
    # Register middlewares (order matters!)
    # 1. User action logger (optional, controlled by LOG_USER_ACTIONS)
    dp.update.middleware(user_action_logger)

    # 2. Activity tracker
    dp.message.middleware(ActivityMiddleware())
    dp.callback_query.middleware(ActivityMiddleware())

    # 3. Admin checker
    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(AdminMiddleware())

    # Register routers in order of priority
    dp.include_router(admin.router)  # Admin first
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(course.router)
    dp.include_router(tasks.router)
    dp.include_router(inline.router)

    logger.info("✅ Handlers and middlewares registered")


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

    # Choose between webhook and polling
    if WEBHOOK_ENABLED and WEBHOOK_URL:
        # Webhook mode
        logger.info(f"🌐 Starting webhook mode: {WEBHOOK_URL}")

        # Set webhook
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types()
        )

        # Create aiohttp application
        app = web.Application()

        # Create webhook handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )

        # Register webhook handler
        webhook_handler.register(app, path=WEBHOOK_PATH)

        # Setup application
        setup_application(app, dp, bot=bot)

        # Run app
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBHOOK_PORT)

        try:
            await site.start()
            logger.info(f"✅ Webhook server started on {WEBAPP_HOST}:{WEBHOOK_PORT}")
            logger.info(f"📍 Webhook path: {WEBHOOK_PATH}")

            # Keep the server running
            await asyncio.Event().wait()
        except Exception as e:
            logger.error(f"❌ Error during webhook: {e}")
            raise
        finally:
            await runner.cleanup()
            await bot.session.close()
    else:
        # Polling mode
        try:
            logger.info("🔄 Starting polling mode...")
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
