"""
Fix certificate_code unique constraint issue
Removes the unique constraint to allow multiple users with same code
"""
import asyncio
from sqlalchemy import text
from bot.database.database import get_engine

async def fix_constraint():
    """Remove unique constraint from certificate_code"""
    engine = get_engine()

    async with engine.begin() as conn:
        try:
            # Drop the unique constraint
            await conn.execute(text(
                "ALTER TABLE certificates DROP CONSTRAINT IF EXISTS certificates_certificate_code_key;"
            ))
            print("✅ Successfully removed unique constraint from certificate_code")
        except Exception as e:
            print(f"❌ Error removing constraint: {e}")

if __name__ == "__main__":
    asyncio.run(fix_constraint())
