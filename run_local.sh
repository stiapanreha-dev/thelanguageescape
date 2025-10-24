#!/bin/bash

# Local development script for The Language Escape Bot
# Runs bot in polling mode with local PostgreSQL

echo "🚀 Starting The Language Escape Bot in LOCAL mode..."
echo ""

# Load local environment
export $(cat .env.local | grep -v '^#' | xargs)

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip3 list | grep -q aiogram || pip3 install -q aiogram asyncpg sqlalchemy python-dotenv apscheduler yookassa Pillow || {
    echo "❌ Failed to install dependencies"
    exit 1
}

# Check database connection
echo "🔍 Checking database connection..."
python3 -c "
import asyncio
import sys
import os
os.environ['MATERIALS_PATH'] = './materials'
os.environ['CERTIFICATES_PATH'] = './certificates'
os.environ['LOGS_PATH'] = './logs'
sys.path.insert(0, '.')

# Create local directories
import pathlib
pathlib.Path('./materials').mkdir(exist_ok=True)
pathlib.Path('./certificates').mkdir(exist_ok=True)
pathlib.Path('./logs').mkdir(exist_ok=True)

from bot.database.database import init_db

async def check_db():
    try:
        await init_db()
        print('✅ Database connection OK')
        return True
    except Exception as e:
        print(f'❌ Database error: {e}')
        return False

if not asyncio.run(check_db()):
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database check failed. Please check your .env.local settings."
    exit 1
fi

echo ""
echo "✅ All checks passed!"
echo "🤖 Starting bot in POLLING mode..."
echo "📍 Press Ctrl+C to stop"
echo ""

# Override paths for local testing
export MATERIALS_PATH=./materials
export CERTIFICATES_PATH=./certificates
export LOGS_PATH=./logs

# Run bot
python3 bot/main.py
