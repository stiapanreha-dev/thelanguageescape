#!/usr/bin/env python3
"""
Migration script: Change telegram_id from INTEGER to BIGINT

This script fixes the issue where large Telegram IDs (> 2147483647)
cause "value out of int32 range" errors.

Usage:
    python3 scripts/migrate_telegram_id_to_bigint.py

Requirements:
    - PostgreSQL database
    - psycopg2 or asyncpg
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import config
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def migrate_telegram_id():
    """
    Migrate telegram_id column from INTEGER to BIGINT in users table
    """
    print("🔧 Starting migration: telegram_id INTEGER → BIGINT")
    print(f"📊 Database: {config.DATABASE_URL.split('@')[1]}")  # Hide password

    # Create async engine
    engine = create_async_engine(
        config.DATABASE_URL,
        echo=True  # Show SQL statements
    )

    try:
        async with engine.begin() as conn:
            print("\n✅ Connected to database")

            # Check current data type
            print("\n📋 Checking current telegram_id type...")
            result = await conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'telegram_id';
            """))
            current_type = result.fetchone()
            if current_type:
                print(f"   Current type: {current_type[1]}")

            # Check if there are any large telegram_ids that would fail
            print("\n🔍 Checking for large telegram_ids (> 2147483647)...")
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM users WHERE telegram_id > 2147483647;
            """))
            count = result.scalar()
            if count:
                print(f"   ⚠️  Found {count} users with large telegram_ids")
            else:
                print("   ✓ No large telegram_ids found yet")

            # Alter column type
            print("\n🔄 Altering telegram_id column type...")
            await conn.execute(text("""
                ALTER TABLE users
                ALTER COLUMN telegram_id TYPE BIGINT;
            """))
            print("   ✓ Column type changed to BIGINT")

            # Verify the change
            print("\n✅ Verifying migration...")
            result = await conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'telegram_id';
            """))
            new_type = result.fetchone()
            if new_type:
                print(f"   New type: {new_type[1]}")

            print("\n🎉 Migration completed successfully!")
            print("   ✓ telegram_id can now store values up to 9223372036854775807")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    print("=" * 60)
    print("   TELEGRAM_ID MIGRATION SCRIPT")
    print("   INTEGER → BIGINT")
    print("=" * 60)

    try:
        asyncio.run(migrate_telegram_id())
        print("\n✅ All done! Bot can now handle large Telegram IDs.")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
