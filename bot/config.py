"""
Configuration module for The Language Escape Bot
Loads settings from environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
MATERIALS_PATH = Path(os.getenv('MATERIALS_PATH', BASE_DIR / 'materials'))
CERTIFICATES_PATH = Path(os.getenv('CERTIFICATES_PATH', BASE_DIR / 'certificates'))
LOGS_PATH = Path(os.getenv('LOGS_PATH', BASE_DIR / 'logs'))

# Create directories if they don't exist
MATERIALS_PATH.mkdir(parents=True, exist_ok=True)
CERTIFICATES_PATH.mkdir(parents=True, exist_ok=True)
LOGS_PATH.mkdir(parents=True, exist_ok=True)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

ADMIN_TELEGRAM_ID = os.getenv('ADMIN_TELEGRAM_ID')
if ADMIN_TELEGRAM_ID:
    try:
        ADMIN_TELEGRAM_ID = int(ADMIN_TELEGRAM_ID)
    except ValueError:
        print("Warning: ADMIN_TELEGRAM_ID is not a valid integer")
        ADMIN_TELEGRAM_ID = None
else:
    print("Warning: ADMIN_TELEGRAM_ID is not set")
    ADMIN_TELEGRAM_ID = None

# YooKassa Configuration (Telegram Payments)
YOOKASSA_PROVIDER_TOKEN = os.getenv('YOOKASSA_PROVIDER_TOKEN')
YOOKASSA_TEST_MODE = os.getenv('YOOKASSA_TEST_MODE', 'True').lower() == 'true'

# Optional: Direct YooKassa API credentials
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')

# PostgreSQL Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'language_escape')
    DB_USER = os.getenv('DB_USER', 'bot_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Course Configuration
COURSE_NAME = os.getenv('COURSE_NAME', 'The Language Escape')
COURSE_PRICE = int(os.getenv('COURSE_PRICE', '999'))
COURSE_CURRENCY = os.getenv('COURSE_CURRENCY', 'RUB')
COURSE_DAYS = int(os.getenv('COURSE_DAYS', '10'))
LIBERATION_CODE = os.getenv('LIBERATION_CODE', 'LIBERATION')

# Timezone and Schedule
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Moscow')
DAILY_RELEASE_TIME = os.getenv('DAILY_RELEASE_TIME', '09:00')

# Reminders Configuration
MAX_REMINDERS = int(os.getenv('MAX_REMINDERS', '3'))
REMINDER_INTERVAL_HOURS = int(os.getenv('REMINDER_INTERVAL_HOURS', '24'))

# Logging Configuration
LOG_USER_ACTIONS = os.getenv('LOG_USER_ACTIONS', 'True').lower() in ('true', '1', 'yes', 'on')

# Tasks Configuration
MAX_TASK_ATTEMPTS = 3
VOICE_MIN_DURATION = 1  # seconds
VOICE_MAX_DURATION = 30  # seconds

# Cyberpunk Theme Messages
THEME_MESSAGES = {
    'welcome': """🔓 **Welcome to NeoVoice, Subject X**

The simulation has you. Your identity is locked behind **{days} encrypted protocols**.

*Corporation ShadowNet* wants to erase you. But there's hope...

💰 **Access Code Price:** {price} {currency}
⏱️ **Protocol Duration:** {days} days
🎯 **Mission:** Collect the code **{code}** to break free

Will you unlock your voice and escape?""",

    'day_start': """⚡ **Day {day}/{total_days}: {title}**

Subject {name}, your next protocol is ready.
The simulation is watching...

🎥 Watch the briefing
📄 Read the intelligence
✅ Complete the challenges

**Time to hack the system.**""",

    'task_correct': """✅ **Protocol Breached!**

Excellent work, {name}! You've unlocked: **{letter}**

**Progress:** Level {day}/{total_days}
**Code Fragment:** `{code_fragment}`

Keep going. Freedom is closer.""",

    'task_incorrect': """❌ **System Glitch Detected**

{hint}

**Attempts remaining:** {attempts}/3
Try again, Subject {name}. The code is within reach.""",

    'reminder': """⚠️ **Subject {name}, Your Mission Awaits!**

You've been inactive for {hours}h.
**Day {day}** protocol is still locked.

*The hackers are waiting. Don't let ShadowNet win.*

Continue your escape now! 🔓""",

    'completion': """🎉 **CODE LIBERATION UNLOCKED!**

Congratulations, **{name}**!

You've broken free from the simulation.
✅ **10/10 Days Complete**
🔑 **Final Code:** `{code}`

Your certificate of freedom is ready:
📜 [Download Certificate]

**What's next?**
🔗 Join our channel: {channel}
📚 Next course: {next_course}

You're a true hacker. Welcome to reality."""
}

# Certificate Configuration
CERTIFICATE_TEMPLATE = {
    'width': 1920,
    'height': 1080,
    'background_color': '#0a0e27',
    'primary_color': '#00ff9f',
    'secondary_color': '#ff006e',
    'font_title': 'Arial',
    'font_size_title': 72,
    'font_size_name': 60,
    'font_size_code': 48,
}

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Feature Flags
ENABLE_VOICE_RECOGNITION = os.getenv('ENABLE_VOICE_RECOGNITION', 'True').lower() == 'true'
ENABLE_PAYMENTS = os.getenv('ENABLE_PAYMENTS', 'True').lower() == 'true'
ENABLE_REMINDERS = os.getenv('ENABLE_REMINDERS', 'True').lower() == 'true'

# Debug mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

def validate_config():
    """Validate critical configuration parameters"""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")

    if ENABLE_PAYMENTS and (not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY):
        errors.append("YooKassa credentials required when ENABLE_PAYMENTS=True")

    if not DATABASE_URL:
        errors.append("DATABASE_URL is required")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    return True

# Validate on import
if not DEBUG:
    try:
        validate_config()
    except ValueError as e:
        print(f"⚠️  Configuration warning: {e}")
