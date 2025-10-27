"""
Timezone detection utilities
Determines user's timezone based on Telegram language code
"""

import logging

logger = logging.getLogger(__name__)


# Mapping of language codes to most likely timezones
LANGUAGE_TO_TIMEZONE = {
    # Russian-speaking countries
    'ru': 'Europe/Moscow',
    'uk': 'Europe/Kiev',
    'be': 'Europe/Minsk',
    'kk': 'Asia/Almaty',
    'uz': 'Asia/Tashkent',

    # English-speaking countries (default to US Eastern)
    'en': 'America/New_York',

    # European languages
    'de': 'Europe/Berlin',
    'fr': 'Europe/Paris',
    'es': 'Europe/Madrid',
    'it': 'Europe/Rome',
    'pl': 'Europe/Warsaw',
    'nl': 'Europe/Amsterdam',
    'pt': 'Europe/Lisbon',
    'cs': 'Europe/Prague',
    'ro': 'Europe/Bucharest',
    'sv': 'Europe/Stockholm',
    'no': 'Europe/Oslo',
    'fi': 'Europe/Helsinki',
    'da': 'Europe/Copenhagen',
    'el': 'Europe/Athens',
    'tr': 'Europe/Istanbul',

    # Asian languages
    'zh': 'Asia/Shanghai',
    'ja': 'Asia/Tokyo',
    'ko': 'Asia/Seoul',
    'hi': 'Asia/Kolkata',
    'ar': 'Asia/Dubai',
    'he': 'Asia/Jerusalem',
    'th': 'Asia/Bangkok',
    'vi': 'Asia/Ho_Chi_Minh',
    'id': 'Asia/Jakarta',

    # Other
    'fa': 'Asia/Tehran',
    'az': 'Asia/Baku',
    'ka': 'Asia/Tbilisi',
    'hy': 'Asia/Yerevan',
}


def detect_timezone_from_language(language_code: str = None) -> str:
    """
    Detect timezone based on Telegram language code

    Args:
        language_code: Telegram user's language code (e.g., "ru", "en", "es")

    Returns:
        Timezone string (e.g., "Europe/Moscow")

    Examples:
        >>> detect_timezone_from_language("ru")
        'Europe/Moscow'
        >>> detect_timezone_from_language("en")
        'America/New_York'
        >>> detect_timezone_from_language("unknown")
        'Europe/Moscow'
    """
    if not language_code:
        logger.debug("No language code provided, using default timezone Europe/Moscow")
        return 'Europe/Moscow'

    # Convert to lowercase for consistency
    language_code = language_code.lower()

    # Get timezone from mapping
    timezone = LANGUAGE_TO_TIMEZONE.get(language_code, 'Europe/Moscow')

    logger.debug(f"Detected timezone '{timezone}' for language code '{language_code}'")

    return timezone


def get_timezone_display_name(timezone: str) -> str:
    """
    Get human-readable timezone name

    Args:
        timezone: Timezone string (e.g., "Europe/Moscow")

    Returns:
        Human-readable name (e.g., "Moscow (UTC+3)")
    """
    from datetime import datetime
    import pytz

    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        offset = now.strftime('%z')
        # Format offset as UTC+X or UTC-X
        offset_hours = int(offset[:3])
        offset_display = f"UTC{offset_hours:+d}"

        city = timezone.split('/')[-1].replace('_', ' ')
        return f"{city} ({offset_display})"
    except:
        return timezone
