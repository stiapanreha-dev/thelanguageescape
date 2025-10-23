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
from bot.database.models import User, Payment, PaymentStatus, Progress, TaskResult
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
