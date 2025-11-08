"""
Inline keyboards for bot
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import COURSE_PRICE, COURSE_CURRENCY


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for welcome message (no access)
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Купить курс - {COURSE_PRICE} {COURSE_CURRENCY}",
            callback_data="buy_course"
        )],
        [InlineKeyboardButton(
            text="📚 О курсе",
            callback_data="course_info"
        )],
        [InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="show_help"
        )],
    ])
    return keyboard


def get_main_menu_keyboard(current_day: int, has_access: bool) -> InlineKeyboardMarkup:
    """
    Main menu keyboard for users with access
    """
    keyboard_rows = []

    if has_access and current_day > 0:
        # Current day button
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"🎬 День {current_day}",
                callback_data=f"start_day_{current_day}"
            )
        ])

        # Progress button
        keyboard_rows.append([
            InlineKeyboardButton(
                text="📊 Мой прогресс",
                callback_data="show_progress"
            )
        ])

        # All days button (if completed multiple days)
        if current_day > 1:
            keyboard_rows.append([
                InlineKeyboardButton(
                    text="📅 Все дни",
                    callback_data="show_all_days"
                )
            ])

    elif not has_access:
        # No access - show purchase button
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"💰 Купить курс - {COURSE_PRICE} {COURSE_CURRENCY}",
                callback_data="buy_course"
            )
        ])

    # Help button
    keyboard_rows.append([
        InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="show_help"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_day_keyboard(day_number: int, has_video: bool = True, has_brief: bool = True) -> InlineKeyboardMarkup:
    """
    Keyboard for a specific day
    """
    keyboard_rows = []

    # Video button
    if has_video:
        keyboard_rows.append([
            InlineKeyboardButton(
                text="🎬 Смотреть видео",
                callback_data=f"watch_video_{day_number}"
            )
        ])

    # Brief button
    if has_brief:
        keyboard_rows.append([
            InlineKeyboardButton(
                text="📄 Читать брифинг",
                callback_data=f"read_brief_{day_number}"
            )
        ])

    # Tasks button
    keyboard_rows.append([
        InlineKeyboardButton(
            text="✅ Начать задания",
            callback_data=f"start_tasks_{day_number}"
        )
    ])

    # Back to menu
    keyboard_rows.append([
        InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_task_keyboard(day: int, task_number: int, options: list[str]) -> InlineKeyboardMarkup:
    """
    Keyboard for multiple choice task
    Options format: ["A) Answer 1", "B) Answer 2", "C) Answer 3", "D) Answer 4"]
    """
    keyboard_rows = []

    for option in options:
        # Extract letter (A, B, C, D)
        letter = option.split(")")[0].strip()
        keyboard_rows.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"answer_{day}_{task_number}_{letter}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_task_result_keyboard(
    day: int,
    task_number: int,
    total_tasks: int,
    is_correct: bool,
    remaining_attempts: int = 3
) -> InlineKeyboardMarkup:
    """
    Keyboard after task answer

    Args:
        day: Day number
        task_number: Current task number
        total_tasks: Total tasks in day
        is_correct: Whether answer was correct
        remaining_attempts: Remaining attempts (0-3)
    """
    keyboard_rows = []

    if is_correct:
        # Next task or finish day
        if task_number < total_tasks:
            keyboard_rows.append([
                InlineKeyboardButton(
                    text="➡️ Следующее задание",
                    callback_data=f"next_task_{day}_{task_number + 1}"
                )
            ])
        else:
            keyboard_rows.append([
                InlineKeyboardButton(
                    text="🎉 Завершить день",
                    callback_data=f"finish_day_{day}"
                )
            ])
    else:
        # Try again (only if attempts remaining)
        if remaining_attempts > 0:
            keyboard_rows.append([
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=f"retry_task_{day}_{task_number}"
                )
            ])

    # Back to menu
    keyboard_rows.append([
        InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_voice_task_keyboard(day: int, task_number: int) -> InlineKeyboardMarkup:
    """
    Keyboard for voice task
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎤 Отправить голосовое",
            callback_data=f"voice_instructions_{day}_{task_number}"
        )],
        [InlineKeyboardButton(
            text="⏭️ Пропустить задание",
            callback_data=f"skip_task_{day}_{task_number}"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"start_day_{day}"
        )],
    ])
    return keyboard


def get_dialog_keyboard(day: int, task_number: int, step: int, options: list[str]) -> InlineKeyboardMarkup:
    """
    Keyboard for dialog task step
    """
    keyboard_rows = []

    for i, option in enumerate(options):
        keyboard_rows.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"dialog_{day}_{task_number}_{step}_{i}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_progress_keyboard(current_day: int) -> InlineKeyboardMarkup:
    """
    Keyboard for progress view
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎬 Продолжить День {current_day}",
            callback_data=f"start_day_{current_day}"
        )],
        [InlineKeyboardButton(
            text="📅 Все дни",
            callback_data="show_all_days"
        )],
        [InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="back_to_menu"
        )],
    ])
    return keyboard


def get_all_days_keyboard(current_day: int, total_days: int = 10) -> InlineKeyboardMarkup:
    """
    Keyboard showing all days
    """
    keyboard_rows = []

    # Create rows with 2 days per row
    for i in range(0, total_days, 2):
        row = []
        for j in range(2):
            day = i + j + 1
            if day <= total_days:
                # Determine emoji based on completion
                if day < current_day:
                    emoji = "✅"  # Completed
                elif day == current_day:
                    emoji = "▶️"  # Current
                else:
                    emoji = "🔒"  # Locked

                row.append(InlineKeyboardButton(
                    text=f"{emoji} День {day}",
                    callback_data=f"view_day_{day}" if day <= current_day else f"locked_day_{day}"
                ))
        keyboard_rows.append(row)

    # Back button
    keyboard_rows.append([
        InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_day_completion_keyboard(day: int, total_days: int) -> InlineKeyboardMarkup:
    """
    Keyboard after completing a day
    """
    keyboard_rows = []

    if day < total_days:
        # Next day button
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"➡️ Начать День {day + 1}",
                callback_data=f"start_day_{day + 1}"
            )
        ])

    # View progress
    keyboard_rows.append([
        InlineKeyboardButton(
            text="📊 Мой прогресс",
            callback_data="show_progress"
        )
    ])

    # Back to menu
    keyboard_rows.append([
        InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_certificate_keyboard(certificate_url: str = None) -> InlineKeyboardMarkup:
    """
    Keyboard for final certificate
    """
    keyboard_rows = []

    if certificate_url:
        keyboard_rows.append([
            InlineKeyboardButton(
                text="📜 Скачать сертификат",
                url=certificate_url
            )
        ])

    # Join channel (if available)
    keyboard_rows.append([
        InlineKeyboardButton(
            text="📢 Наш канал",
            url="https://t.me/languageescape"
        )
    ])

    # Rate the course
    keyboard_rows.append([
        InlineKeyboardButton(
            text="⭐ Оценить курс",
            callback_data="rate_course"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Admin panel keyboard
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👥 Статистика пользователей",
            callback_data="admin_users"
        )],
        [InlineKeyboardButton(
            text="💰 Статистика платежей",
            callback_data="admin_payments"
        )],
        [InlineKeyboardButton(
            text="📊 Статистика прогресса",
            callback_data="admin_progress"
        )],
        [InlineKeyboardButton(
            text="🔧 Управление пользователями",
            callback_data="admin_management"
        )],
        [InlineKeyboardButton(
            text="📢 Рассылка",
            callback_data="admin_broadcast"
        )],
        [InlineKeyboardButton(
            text="⬅️ Закрыть",
            callback_data="admin_close"
        )],
    ])
    return keyboard
