#!/usr/bin/env python3
"""
Fix user progress data based on completed Progress records
Recalculates completed_days and liberation_code for all users
"""

import asyncio
import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.database.database import async_session_maker
from bot.database.models import User, Progress
from bot.config import LIBERATION_CODE
from sqlalchemy import select


def get_code_letter(day_number: int) -> str:
    """Get liberation code letter for a day"""
    if 1 <= day_number <= len(LIBERATION_CODE):
        return LIBERATION_CODE[day_number - 1]
    return ''


async def fix_user_progress():
    """Fix progress data for all users based on their Progress records"""
    async with async_session_maker() as session:
        # Get all users with access
        result = await session.execute(
            select(User).where(User.has_access == True)
        )
        users = result.scalars().all()

        print(f"Found {len(users)} users with access")
        print()

        fixed_count = 0
        for user in users:
            # Get all completed Progress records for this user
            progress_result = await session.execute(
                select(Progress).where(
                    Progress.user_id == user.id,
                    Progress.tasks_completed == True
                ).order_by(Progress.day_number)
            )
            completed_progresses = progress_result.scalars().all()

            if not completed_progresses:
                print(f"⏭️  User {user.telegram_id} (@{user.username}): No completed days")
                continue

            # Calculate correct completed_days (maximum completed day)
            max_completed_day = max(prog.day_number for prog in completed_progresses)

            # Build liberation code from ALL completed days
            code_list = list('_' * len(LIBERATION_CODE))
            for prog in completed_progresses:
                day_letter = get_code_letter(prog.day_number)
                if day_letter and 1 <= prog.day_number <= len(LIBERATION_CODE):
                    code_list[prog.day_number - 1] = day_letter

            new_liberation_code = ''.join(code_list)

            # Check if data needs fixing
            old_completed_days = user.completed_days
            old_liberation_code = user.liberation_code

            needs_fix = (
                user.completed_days != max_completed_day or
                user.liberation_code != new_liberation_code
            )

            if needs_fix:
                print(f"🔧 Fixing user {user.telegram_id} (@{user.username}):")
                print(f"   Completed days: {old_completed_days} → {max_completed_day}")
                print(f"   Liberation code: {old_liberation_code} → {new_liberation_code}")
                print(f"   Completed Progress records: {[p.day_number for p in completed_progresses]}")

                # Update user data
                user.completed_days = max_completed_day
                user.liberation_code = new_liberation_code

                fixed_count += 1
            else:
                print(f"✅ User {user.telegram_id} (@{user.username}): Already correct")
                print(f"   Completed days: {user.completed_days}")
                print(f"   Liberation code: {user.liberation_code}")

            print()

        # Commit changes
        if fixed_count > 0:
            await session.commit()
            print(f"✅ Fixed {fixed_count} user(s)")
        else:
            print("✅ All users already have correct data")


if __name__ == "__main__":
    print("=" * 60)
    print("FIX USER PROGRESS DATA")
    print("=" * 60)
    print()

    asyncio.run(fix_user_progress())

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
