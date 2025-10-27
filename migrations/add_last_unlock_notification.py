#!/usr/bin/env python3
"""
Migration: Add last_unlock_notification and timezone fields to users table
"""

import asyncio
import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.database.database import async_session_maker
from sqlalchemy import text


async def migrate():
    """Add last_unlock_notification and timezone columns to users table"""
    async with async_session_maker() as session:
        try:
            # Check if last_unlock_notification column exists
            check_query1 = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users'
                AND column_name='last_unlock_notification'
            """)
            result1 = await session.execute(check_query1)
            exists1 = result1.scalar_one_or_none()

            if not exists1:
                # Add last_unlock_notification column
                alter_query1 = text("""
                    ALTER TABLE users
                    ADD COLUMN last_unlock_notification TIMESTAMP WITHOUT TIME ZONE
                """)
                await session.execute(alter_query1)
                print("✅ Successfully added 'last_unlock_notification' column")
            else:
                print("⏭️  Column 'last_unlock_notification' already exists")

            # Check if timezone column exists
            check_query2 = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users'
                AND column_name='timezone'
            """)
            result2 = await session.execute(check_query2)
            exists2 = result2.scalar_one_or_none()

            if not exists2:
                # Add timezone column with default value
                alter_query2 = text("""
                    ALTER TABLE users
                    ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow'
                """)
                await session.execute(alter_query2)
                print("✅ Successfully added 'timezone' column")
            else:
                print("⏭️  Column 'timezone' already exists")

            await session.commit()
            print("✅ Migration completed successfully")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRATION: Add last_unlock_notification and timezone to users")
    print("=" * 60)
    print()

    asyncio.run(migrate())

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
