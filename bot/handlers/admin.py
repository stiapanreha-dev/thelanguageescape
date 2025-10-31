"""
Admin panel handlers
Statistics, user management, broadcast
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_TELEGRAM_ID
from bot.database.models import User, Payment, PaymentStatus, Progress, TaskResult, Certificate, Reminder
from bot.keyboards.inline import get_admin_keyboard
from bot.middlewares.admin import admin_required

logger = logging.getLogger(__name__)

router = Router(name="admin")


@router.message(Command("admin"))
@admin_required
async def cmd_admin(message: Message, is_admin: bool, session: AsyncSession):
    """
    Show admin panel
    """
    admin_text = f"""
🔐 **Admin Panel**

Welcome, Administrator!

Use the buttons below to manage the bot:

👥 **Users** - View user statistics
💰 **Payments** - Payment analytics
📊 **Progress** - Course progress stats
🔧 **Management** - User management commands
📢 **Broadcast** - Send message to all users

Admin ID: `{message.from_user.id}`
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    await message.answer(
        admin_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin_users")
@admin_required
async def callback_admin_users(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    """
    Show user statistics
    """
    # Total users
    total_users_result = await session.execute(
        select(func.count(User.id))
    )
    total_users = total_users_result.scalar()

    # Users with access
    paid_users_result = await session.execute(
        select(func.count(User.id)).where(User.has_access == True)
    )
    paid_users = paid_users_result.scalar()

    # New users today
    today = datetime.utcnow().date()
    new_today_result = await session.execute(
        select(func.count(User.id)).where(
            func.date(User.created_at) == today
        )
    )
    new_today = new_today_result.scalar()

    # New users this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_week_result = await session.execute(
        select(func.count(User.id)).where(
            User.created_at >= week_ago
        )
    )
    new_week = new_week_result.scalar()

    # Active users (last 24h)
    day_ago = datetime.utcnow() - timedelta(days=1)
    active_result = await session.execute(
        select(func.count(User.id)).where(
            User.last_activity >= day_ago
        )
    )
    active_users = active_result.scalar()

    # Completed course
    completed_result = await session.execute(
        select(func.count(User.id)).where(
            User.course_completed_at.isnot(None)
        )
    )
    completed_users = completed_result.scalar()

    # Conversion rate
    conversion = (paid_users / total_users * 100) if total_users > 0 else 0
    completion_rate = (completed_users / paid_users * 100) if paid_users > 0 else 0

    users_text = f"""
👥 **User Statistics**

**Total Users:** {total_users}
**Paid Users:** {paid_users} ({conversion:.1f}% conversion)
**Free Users:** {total_users - paid_users}

**Activity:**
• New today: {new_today}
• New this week: {new_week}
• Active (24h): {active_users}

**Course Completion:**
• Completed: {completed_users} ({completion_rate:.1f}%)
• In progress: {paid_users - completed_users}

**Engagement:**
• Active rate: {(active_users / total_users * 100):.1f}%
"""

    await callback.message.edit_text(
        users_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payments")
@admin_required
async def callback_admin_payments(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    """
    Show payment statistics
    """
    # Total payments
    total_payments_result = await session.execute(
        select(func.count(Payment.id))
    )
    total_payments = total_payments_result.scalar()

    # Successful payments
    success_result = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    successful = success_result.scalar()

    # Total revenue
    revenue_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    total_revenue = revenue_result.scalar() or 0

    # Payments today
    today = datetime.utcnow().date()
    today_payments_result = await session.execute(
        select(func.count(Payment.id)).where(
            func.date(Payment.created_at) == today,
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    today_payments = today_payments_result.scalar()

    # Revenue today
    today_revenue_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            func.date(Payment.created_at) == today,
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    today_revenue = today_revenue_result.scalar() or 0

    # This week
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_payments_result = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.created_at >= week_ago,
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    week_payments = week_payments_result.scalar()

    week_revenue_result = await session.execute(
        select(func.sum(Payment.amount)).where(
            Payment.created_at >= week_ago,
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    week_revenue = week_revenue_result.scalar() or 0

    # Failed payments
    failed_result = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.CANCELED])
        )
    )
    failed = failed_result.scalar()

    payments_text = f"""
💰 **Payment Statistics**

**Total Payments:** {total_payments}
• Successful: {successful}
• Failed/Canceled: {failed}

**Revenue:**
• Total: {total_revenue:,.2f} RUB
• Average: {(total_revenue / successful if successful > 0 else 0):,.2f} RUB

**Today:**
• Payments: {today_payments}
• Revenue: {today_revenue:,.2f} RUB

**This Week:**
• Payments: {week_payments}
• Revenue: {week_revenue:,.2f} RUB
• Avg/day: {(week_revenue / 7):,.2f} RUB

**Success Rate:** {(successful / total_payments * 100 if total_payments > 0 else 0):.1f}%
"""

    await callback.message.edit_text(
        payments_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_progress")
@admin_required
async def callback_admin_progress(callback: CallbackQuery, is_admin: bool, session: AsyncSession):
    """
    Show course progress statistics
    """
    # Total progress records
    total_progress_result = await session.execute(
        select(func.count(Progress.id))
    )
    total_progress = total_progress_result.scalar()

    # Completed days distribution
    day_stats = {}
    for day in range(1, 11):
        result = await session.execute(
            select(func.count(Progress.id)).where(
                Progress.day_number == day,
                Progress.tasks_completed == True
            )
        )
        day_stats[day] = result.scalar()

    # Average completion rate per day
    avg_completion = sum(day_stats.values()) / 10 if day_stats else 0

    # Task results
    total_tasks_result = await session.execute(
        select(func.count(TaskResult.id))
    )
    total_tasks = total_tasks_result.scalar()

    correct_tasks_result = await session.execute(
        select(func.count(TaskResult.id)).where(
            TaskResult.is_correct == True
        )
    )
    correct_tasks = correct_tasks_result.scalar()

    # Average attempts
    avg_attempts_result = await session.execute(
        select(func.avg(TaskResult.attempts))
    )
    avg_attempts = avg_attempts_result.scalar() or 0

    progress_text = f"""
📊 **Course Progress Statistics**

**Overall:**
• Total progress records: {total_progress}
• Avg completion/day: {avg_completion:.1f}

**Day Completion:**
"""

    # Add day-by-day stats
    for day in range(1, 11):
        completed = day_stats.get(day, 0)
        progress_text += f"Day {day:2d}: {'█' * (completed // 5)}{completed:3d} users\n"

    progress_text += f"""
**Tasks:**
• Total attempts: {total_tasks}
• Correct answers: {correct_tasks}
• Accuracy: {(correct_tasks / total_tasks * 100 if total_tasks > 0 else 0):.1f}%
• Avg attempts: {avg_attempts:.1f}

**Engagement:**
• Users starting: {day_stats.get(1, 0)}
• Reaching Day 10: {day_stats.get(10, 0)}
• Drop-off rate: {((day_stats.get(1, 1) - day_stats.get(10, 0)) / day_stats.get(1, 1) * 100 if day_stats.get(1, 0) > 0 else 0):.1f}%
"""

    await callback.message.edit_text(
        progress_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_management")
@admin_required
async def callback_admin_management(callback: CallbackQuery, is_admin: bool):
    """
    User management commands info
    """
    management_text = """
🔧 **User Management Commands**

**Available Commands:**

**1. Grant Access**
`/grant_access <telegram_id>`
• Give course access to a user
• Automatically starts from Day 1
• Sends notification to user

**2. Reset Progress**
`/reset_progress <telegram_id>`
• Delete all user progress
• Resets to Day 0
• Keeps access active
• ⚠️ Cannot be undone!

**3. User Info**
`/user_info <telegram_id>`
• View detailed user information
• Shows progress, stats, payments
• Activity status
• Certificates

**Examples:**
`/grant_access 123456789`
`/reset_progress 123456789`
`/user_info 123456789`

**Note:** You need the user's Telegram ID to use these commands.
"""

    await callback.message.edit_text(
        management_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
@admin_required
async def callback_admin_broadcast(callback: CallbackQuery, is_admin: bool):
    """
    Broadcast message feature
    """
    broadcast_text = """
📢 **Broadcast Message**

To send a message to all users, use:
`/broadcast Your message here`

**Examples:**
`/broadcast 🎉 New course available!`
`/broadcast Update: Bug fixes released`

**Note:** Messages will be sent to all registered users.
Use with caution!
"""

    await callback.message.edit_text(
        broadcast_text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.message(Command("broadcast"))
@admin_required
async def cmd_broadcast(message: Message, is_admin: bool, session: AsyncSession):
    """
    Broadcast message to all users
    """
    # Get message text (remove /broadcast command)
    text = message.text.replace('/broadcast', '').strip()

    if not text:
        await message.answer(
            "❌ Please provide a message to broadcast:\n"
            "`/broadcast Your message here`",
            parse_mode="Markdown"
        )
        return

    # Get all users
    result = await session.execute(
        select(User)
    )
    users = result.scalars().all()

    # Send broadcast
    success_count = 0
    fail_count = 0

    status_msg = await message.answer(
        f"📤 Sending broadcast to {len(users)} users..."
    )

    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 **Broadcast from Admin:**\n\n{text}",
                parse_mode="Markdown"
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            fail_count += 1

    # Update status
    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"Sent: {success_count}\n"
        f"Failed: {fail_count}\n"
        f"Total: {len(users)}"
    )

    logger.info(f"Broadcast sent by admin {message.from_user.id}: {success_count}/{len(users)} successful")


@router.callback_query(F.data == "admin_close")
async def callback_admin_close(callback: CallbackQuery):
    """Close admin panel"""
    await callback.message.delete()
    await callback.answer("Admin panel closed")


# Command to check own admin status
@router.message(Command("am_i_admin"))
async def cmd_am_i_admin(message: Message, session: AsyncSession):
    """Check if user is admin"""
    user_id = message.from_user.id

    # Check config
    is_config_admin = ADMIN_TELEGRAM_ID and user_id == ADMIN_TELEGRAM_ID

    # Check database
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    is_db_admin = user.is_admin if user else False

    status_text = f"""
🔐 **Admin Status Check**

Your Telegram ID: `{user_id}`
Config Admin ID: `{ADMIN_TELEGRAM_ID or 'Not set'}`

**Status:**
• Config Admin: {'✅ Yes' if is_config_admin else '❌ No'}
• Database Admin: {'✅ Yes' if is_db_admin else '❌ No'}

**Overall:** {'🔐 You are an ADMIN' if (is_config_admin or is_db_admin) else '👤 Regular user'}
"""

    await message.answer(status_text, parse_mode="Markdown")


@router.message(Command("grant_access"))
@admin_required
async def cmd_grant_access(message: Message, is_admin: bool, session: AsyncSession):
    """
    Grant course access to user
    Usage: /grant_access <telegram_id>
    """
    # Parse telegram_id from command
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Usage Error**\n\n"
            "Please provide Telegram ID:\n"
            "`/grant_access <telegram_id>`\n\n"
            "**Example:**\n"
            "`/grant_access 123456789`",
            parse_mode="Markdown"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer(
            "❌ **Invalid Telegram ID**\n\n"
            "Telegram ID must be a number.\n\n"
            "**Example:**\n"
            "`/grant_access 123456789`",
            parse_mode="Markdown"
        )
        return

    # Find user
    result = await session.execute(
        select(User).where(User.telegram_id == target_telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            f"❌ **User Not Found**\n\n"
            f"User with Telegram ID `{target_telegram_id}` not found in database.\n\n"
            f"**Note:** User must start the bot first (`/start`)",
            parse_mode="Markdown"
        )
        return

    # Check if already has access
    if user.has_access:
        await message.answer(
            f"ℹ️ **Already Has Access**\n\n"
            f"User `{target_telegram_id}` (@{user.username or 'N/A'}) already has course access.\n\n"
            f"**Current Status:**\n"
            f"• Name: {user.first_name or 'N/A'} {user.last_name or ''}\n"
            f"• Current Day: {user.current_day}\n"
            f"• Completed Days: {user.completed_days}",
            parse_mode="Markdown"
        )
        return

    # Grant access
    user.has_access = True
    user.current_day = 1  # Start from day 1

    if not user.course_started_at:
        user.course_started_at = datetime.utcnow()

    await session.commit()

    # Send confirmation
    await message.answer(
        f"✅ **Access Granted**\n\n"
        f"User `{target_telegram_id}` (@{user.username or 'N/A'}) now has course access.\n\n"
        f"**User Info:**\n"
        f"• Name: {user.first_name or 'N/A'} {user.last_name or ''}\n"
        f"• Current Day: {user.current_day}\n"
        f"• Started At: {user.course_started_at.strftime('%Y-%m-%d %H:%M:%S') if user.course_started_at else 'Just now'}",
        parse_mode="Markdown"
    )

    # Notify user
    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="""
🎉 **Добро пожаловать в The Language Escape!**

Вам предоставлен доступ к курсу администратором.

🚀 **Начните прямо сейчас:**
/day - Начать День 1

Удачи в прохождении курса!
""",
            parse_mode="Markdown"
        )
        logger.info(f"Sent access notification to user {target_telegram_id}")
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id}: {e}")

    logger.info(f"Admin {message.from_user.id} granted access to user {target_telegram_id}")


@router.message(Command("reset_progress"))
@admin_required
async def cmd_reset_progress(message: Message, is_admin: bool, session: AsyncSession):
    """
    Reset user's course progress
    Usage: /reset_progress <telegram_id>
    """
    # Parse telegram_id from command
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Usage Error**\n\n"
            "Please provide Telegram ID:\n"
            "`/reset_progress <telegram_id>`\n\n"
            "**Example:**\n"
            "`/reset_progress 123456789`\n\n"
            "⚠️ **Warning:** This will delete ALL progress data for the user!",
            parse_mode="Markdown"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer(
            "❌ **Invalid Telegram ID**\n\n"
            "Telegram ID must be a number.\n\n"
            "**Example:**\n"
            "`/reset_progress 123456789`",
            parse_mode="Markdown"
        )
        return

    # Find user
    result = await session.execute(
        select(User).where(User.telegram_id == target_telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            f"❌ **User Not Found**\n\n"
            f"User with Telegram ID `{target_telegram_id}` not found in database.",
            parse_mode="Markdown"
        )
        return

    # Store old data for confirmation message
    old_current_day = user.current_day
    old_completed_days = user.completed_days
    old_code = user.liberation_code

    # Get counts before deletion
    task_results_count = await session.execute(
        select(func.count(TaskResult.id)).where(TaskResult.user_id == user.id)
    )
    task_count = task_results_count.scalar()

    progress_count = await session.execute(
        select(func.count(Progress.id)).where(Progress.user_id == user.id)
    )
    prog_count = progress_count.scalar()

    certificates_result = await session.execute(
        select(func.count(Certificate.id)).where(Certificate.user_id == user.id)
    )
    cert_count = certificates_result.scalar()

    # Reset user progress
    user.current_day = 0
    user.completed_days = 0
    user.liberation_code = '__________'  # 10 underscores for "LIBERATION"
    user.course_started_at = None
    user.course_completed_at = None

    # Delete task results
    await session.execute(
        select(TaskResult).where(TaskResult.user_id == user.id)
    )
    delete_tasks = await session.execute(
        select(TaskResult).where(TaskResult.user_id == user.id)
    )
    for task_result in delete_tasks.scalars().all():
        await session.delete(task_result)

    # Delete progress records
    delete_progress = await session.execute(
        select(Progress).where(Progress.user_id == user.id)
    )
    for progress in delete_progress.scalars().all():
        await session.delete(progress)

    # Delete certificates
    delete_certs = await session.execute(
        select(Certificate).where(Certificate.user_id == user.id)
    )
    for cert in delete_certs.scalars().all():
        await session.delete(cert)

    # Delete reminders
    delete_reminders = await session.execute(
        select(Reminder).where(Reminder.user_id == user.id)
    )
    for reminder in delete_reminders.scalars().all():
        await session.delete(reminder)

    await session.commit()

    # Send confirmation
    await message.answer(
        f"✅ **Progress Reset Complete**\n\n"
        f"**User:** `{target_telegram_id}` (@{user.username or 'N/A'})\n"
        f"**Name:** {user.first_name or 'N/A'} {user.last_name or ''}\n\n"
        f"**Old Progress:**\n"
        f"• Current Day: {old_current_day} → 0\n"
        f"• Completed Days: {old_completed_days} → 0\n"
        f"• Liberation Code: `{old_code}` → `__________`\n\n"
        f"**Deleted:**\n"
        f"• Task Results: {task_count}\n"
        f"• Progress Records: {prog_count}\n"
        f"• Certificates: {cert_count}\n"
        f"• Reminders: cleared\n\n"
        f"⚠️ User still has access to course. To start again, they can use /day",
        parse_mode="Markdown"
    )

    # Notify user
    try:
        await message.bot.send_message(
            chat_id=target_telegram_id,
            text="""
🔄 **Ваш прогресс был сброшен**

Администратор сбросил ваш прогресс по курсу.

Вы можете начать заново:
/day - Начать с Дня 1

Удачи!
""",
            parse_mode="Markdown"
        )
        logger.info(f"Sent reset notification to user {target_telegram_id}")
    except Exception as e:
        logger.error(f"Failed to notify user {target_telegram_id}: {e}")

    logger.info(f"Admin {message.from_user.id} reset progress for user {target_telegram_id}")


@router.message(Command("user_info"))
@admin_required
async def cmd_user_info(message: Message, is_admin: bool, session: AsyncSession):
    """
    Get detailed user information
    Usage: /user_info <telegram_id>
    """
    # Parse telegram_id from command
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Usage Error**\n\n"
            "Please provide Telegram ID:\n"
            "`/user_info <telegram_id>`\n\n"
            "**Example:**\n"
            "`/user_info 123456789`",
            parse_mode="Markdown"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer(
            "❌ **Invalid Telegram ID**\n\n"
            "Telegram ID must be a number.\n\n"
            "**Example:**\n"
            "`/user_info 123456789`",
            parse_mode="Markdown"
        )
        return

    # Find user
    result = await session.execute(
        select(User).where(User.telegram_id == target_telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            f"❌ **User Not Found**\n\n"
            f"User with Telegram ID `{target_telegram_id}` not found in database.",
            parse_mode="Markdown"
        )
        return

    # Get statistics
    # Total tasks attempted
    total_tasks_result = await session.execute(
        select(func.count(TaskResult.id)).where(TaskResult.user_id == user.id)
    )
    total_tasks = total_tasks_result.scalar()

    # Correct answers
    correct_tasks_result = await session.execute(
        select(func.count(TaskResult.id)).where(
            TaskResult.user_id == user.id,
            TaskResult.is_correct == True
        )
    )
    correct_tasks = correct_tasks_result.scalar()

    # Progress records
    progress_result = await session.execute(
        select(func.count(Progress.id)).where(Progress.user_id == user.id)
    )
    progress_count = progress_result.scalar()

    # Completed days count
    completed_progress_result = await session.execute(
        select(func.count(Progress.id)).where(
            Progress.user_id == user.id,
            Progress.tasks_completed == True
        )
    )
    completed_days_count = completed_progress_result.scalar()

    # Payments
    payments_result = await session.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    payments = payments_result.scalars().all()

    # Reminders
    reminders_result = await session.execute(
        select(func.count(Reminder.id)).where(
            Reminder.user_id == user.id,
            Reminder.sent == True
        )
    )
    reminders_count = reminders_result.scalar()

    # Certificates
    certificates_result = await session.execute(
        select(Certificate).where(Certificate.user_id == user.id)
    )
    certificates = certificates_result.scalars().all()

    # Calculate accuracy
    accuracy = (correct_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Calculate activity
    if user.last_activity:
        inactive_hours = (datetime.utcnow() - user.last_activity).total_seconds() / 3600
        if inactive_hours < 1:
            activity_status = "🟢 Active (< 1h)"
        elif inactive_hours < 24:
            activity_status = f"🟡 Inactive {int(inactive_hours)}h"
        else:
            activity_status = f"🔴 Inactive {int(inactive_hours / 24)}d"
    else:
        activity_status = "⚪ Never active"

    # Build info message
    info_text = f"""
👤 **User Information**

**Basic Info:**
• Telegram ID: `{user.telegram_id}`
• Username: @{user.username or 'N/A'}
• Name: {user.first_name or 'N/A'} {user.last_name or ''}
• Email: {user.email or 'N/A'}

**Profile:**
• Country: {user.country or 'N/A'}
• Profession: {user.profession or 'N/A'}
• Timezone: {user.timezone}

**Access:**
• Has Access: {'✅ Yes' if user.has_access else '❌ No'}
• Is Admin: {'✅ Yes' if user.is_admin else '❌ No'}

**Course Progress:**
• Current Day: {user.current_day}/10
• Completed Days: {user.completed_days}/10
• Liberation Code: `{user.liberation_code}`

**Activity:**
• Status: {activity_status}
• Created: {user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'N/A'}
• Last Activity: {user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else 'Never'}
• Course Started: {user.course_started_at.strftime('%Y-%m-%d %H:%M') if user.course_started_at else 'Not started'}
• Course Completed: {user.course_completed_at.strftime('%Y-%m-%d %H:%M') if user.course_completed_at else 'Not completed'}

**Statistics:**
• Total Tasks: {total_tasks}
• Correct Answers: {correct_tasks}
• Accuracy: {accuracy:.1f}%
• Progress Records: {progress_count}
• Completed Days: {completed_days_count}
• Reminders Sent: {reminders_count}

**Payments:**
"""

    if payments:
        for payment in payments[:3]:  # Show last 3 payments
            info_text += f"• {payment.amount} {payment.currency} - {payment.status.value} ({payment.created_at.strftime('%Y-%m-%d')})\n"
        if len(payments) > 3:
            info_text += f"• ... and {len(payments) - 3} more\n"
    else:
        info_text += "• No payments\n"

    info_text += f"\n**Certificates:**\n"
    if certificates:
        for cert in certificates:
            info_text += f"• Code: `{cert.certificate_code}` - Accuracy: {cert.accuracy:.1f}%\n"
    else:
        info_text += "• No certificates\n"

    # Add management commands
    info_text += f"""
**Management:**
• Grant Access: `/grant_access {user.telegram_id}`
• Reset Progress: `/reset_progress {user.telegram_id}`
"""

    await message.answer(info_text, parse_mode="Markdown")
    logger.info(f"Admin {message.from_user.id} viewed info for user {target_telegram_id}")
