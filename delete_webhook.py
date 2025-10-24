#!/usr/bin/env python3
"""
Delete webhook from Telegram Bot API
Use this to switch from webhook to polling mode for local testing
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

from aiogram import Bot

async def delete_webhook():
    """Delete webhook and allow polling"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return False

    bot = Bot(token=token)

    try:
        # Delete webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted successfully!")
        print("📱 You can now use polling mode for local testing")

        # Get webhook info to confirm
        info = await bot.get_webhook_info()
        print(f"\n📊 Webhook info:")
        print(f"   URL: {info.url or '(not set)'}")
        print(f"   Pending updates: {info.pending_update_count}")

    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False
    finally:
        await bot.session.close()

    return True

if __name__ == "__main__":
    success = asyncio.run(delete_webhook())
    sys.exit(0 if success else 1)
