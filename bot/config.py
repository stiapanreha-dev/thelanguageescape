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

# Webhook Configuration
WEBHOOK_ENABLED = os.getenv('WEBHOOK_ENABLED', 'False').lower() == 'true'
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN', '')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook/telegram')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))
WEBAPP_HOST = os.getenv('WEBAPP_HOST', '0.0.0.0')
WEBHOOK_URL = f"{WEBHOOK_DOMAIN}{WEBHOOK_PATH}" if WEBHOOK_DOMAIN else None

# YooKassa Configuration (Telegram Payments)
# YooKassa API credentials
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '1193453')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_PROVIDER_TOKEN', 'test_I3cKZsggMbi7Ct9XX8M1-B1fBblP0EyIj0q7HzS4_QE')
YOOKASSA_TEST_MODE = os.getenv('YOOKASSA_TEST_MODE', 'True').lower() == 'true'

# Legacy: Telegram Payments provider token (not used with direct API)
YOOKASSA_PROVIDER_TOKEN = os.getenv('YOOKASSA_PROVIDER_TOKEN')

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
    'welcome': """🔓 **Добро пожаловать в NeoVoice, Субъект X**

Сердце стучит: что ждёт в NeoVoice? **{days}-дневный квест A1-A2:** взломай код, задавай вопросы и почувствуй адреналин свободы! Твоя тайна раскрыта?

*Корпорация ShadowNet* хочет стереть тебя. Но есть надежда...

💰 **Цена кода доступа:** {price} {currency}
⏱️ **Длительность протокола:** {days} дней
🎯 **Миссия:** Собери секретный код, чтобы вырваться на свободу

⚠️ **Время уходит.** Каждая секунда на счету.

Разблокируешь ли ты свой голос и сбежишь? **Оплати доступ и прими вызов сейчас же!**""",

    'day_start': """⚡ **День {day}/{total_days}: {title}**

{name}, твой следующий протокол готов.
Симуляция наблюдает...

🎥 Посмотри брифинг
📄 Прочитай разведданные
✅ Выполни испытания

**Время взломать систему.**""",

    'task_correct': """✅ **Протокол взломан!**

Отличная работа, {name}! Ты разблокировал: **{letter}**

**Прогресс:** Уровень {day}/{total_days}
**Фрагмент кода:** `{code_fragment}`

Продолжай. Свобода ближе.""",

    'task_incorrect': """❌ **Обнаружен сбой системы**

{hint}

**Осталось попыток:** {attempts}/3
Попробуй снова, Субъект {name}. Код в пределах досягаемости.""",

    'reminder': """⚠️ **Субъект {name}, твоя миссия ждёт!**

Ты неактивен уже {hours}ч.
Протокол **Дня {day}** всё ещё заблокирован.

*Хакеры ждут. Не дай ShadowNet победить.*

Продолжи побег прямо сейчас! 🔓""",

    'completion': """🎉 **КОД ОСВОБОЖДЕНИЯ РАЗБЛОКИРОВАН!**

Поздравляем, **{name}**!

Ты вырвался из симуляции.
✅ **10/10 дней пройдено**
🔑 **Финальный код:** `{code}`

Твой сертификат свободы готов:
📜 [Скачать сертификат]

**Что дальше?**
🔗 Подпишись на канал: {channel}
📚 Следующий курс: {next_course}

Ты настоящий хакер. Добро пожаловать в реальность."""
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
