#!/usr/bin/env python3
"""
Webhook registration script
Registers Telegram webhook after deployment
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot
from bot.config import (
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_ENABLED,
    WEBHOOK_URL,
    WEBHOOK_PATH
)


async def setup_webhook():
    """Register webhook with Telegram"""
    if not WEBHOOK_ENABLED or not WEBHOOK_URL:
        print("❌ Webhook not enabled or WEBHOOK_URL not set")
        print(f"WEBHOOK_ENABLED: {WEBHOOK_ENABLED}")
        print(f"WEBHOOK_URL: {WEBHOOK_URL}")
        return False

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        # Delete existing webhook first
        await bot.delete_webhook(drop_pending_updates=True)
        print("🗑️  Deleted existing webhook")

        # Set new webhook
        webhook_info = await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )

        print(f"✅ Webhook registered successfully!")
        print(f"📍 URL: {WEBHOOK_URL}")
        print(f"🔗 Path: {WEBHOOK_PATH}")

        # Get webhook info
        info = await bot.get_webhook_info()
        print(f"\n📊 Webhook Info:")
        print(f"   URL: {info.url}")
        print(f"   Pending updates: {info.pending_update_count}")
        print(f"   Last error: {info.last_error_message or 'None'}")

        return True

    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

    finally:
        await bot.session.close()


async def delete_webhook():
    """Delete webhook (switch to polling)"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted successfully (switched to polling mode)")
        return True

    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False

    finally:
        await bot.session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage Telegram webhook")
    parser.add_argument(
        "action",
        choices=["setup", "delete", "info"],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "setup":
        success = asyncio.run(setup_webhook())
        sys.exit(0 if success else 1)

    elif args.action == "delete":
        success = asyncio.run(delete_webhook())
        sys.exit(0 if success else 1)

    elif args.action == "info":
        async def get_info():
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            try:
                info = await bot.get_webhook_info()
                print(f"📊 Current Webhook Info:")
                print(f"   URL: {info.url or 'Not set (polling mode)'}")
                print(f"   Pending updates: {info.pending_update_count}")
                print(f"   Max connections: {info.max_connections}")
                print(f"   Last error: {info.last_error_message or 'None'}")
                if info.last_error_date:
                    print(f"   Last error date: {info.last_error_date}")
            finally:
                await bot.session.close()

        asyncio.run(get_info())
        sys.exit(0)
