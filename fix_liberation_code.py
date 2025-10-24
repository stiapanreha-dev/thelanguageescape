#!/usr/bin/env python3
"""
Fix liberation_code format for existing users
"""
import asyncio
import sys
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.database.database import get_session
from bot.database.models import User
from bot.config import LIBERATION_CODE
from sqlalchemy import select


async def fix_liberation_codes():
    """Fix liberation_code for all users"""
    print(f"Liberation code: {LIBERATION_CODE} (length: {len(LIBERATION_CODE)})")
    print("Fixing liberation codes for all users...")

    async for session in get_session():
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"Found {len(users)} users")

        for user in users:
            old_code = user.liberation_code

            # Build correct code based on completed_days
            code_list = list('_' * len(LIBERATION_CODE))

            for day in range(1, user.completed_days + 1):
                if day <= len(LIBERATION_CODE):
                    code_list[day - 1] = LIBERATION_CODE[day - 1]

            new_code = ''.join(code_list)

            if old_code != new_code:
                user.liberation_code = new_code
                print(f"User {user.telegram_id}: '{old_code}' -> '{new_code}' (completed {user.completed_days} days)")
            else:
                print(f"User {user.telegram_id}: '{old_code}' (already correct)")

        await session.commit()
        print("✅ All liberation codes fixed!")
        break  # Only need one iteration


if __name__ == '__main__':
    asyncio.run(fix_liberation_codes())
