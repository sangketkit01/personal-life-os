from datetime import date, timedelta
from typing import List, Dict, Any
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationStatus, ObligationType
from apps.finance.strategies import ObligationStrategyFactory
from apps.workspace.models import TaskDocument, TaskStatus

User = get_user_model()


@sync_to_async
def get_users_with_telegram() -> List[Any]:
    """Retrieve all active users who linked a Telegram Chat ID."""
    return list(User.objects.filter(telegram_chat_id__isnull=False, is_active=True))


@sync_to_async
def get_due_tomorrow_obligations_for_user(user, target_date: date = None) -> List[Any]:
    """Retrieve obligations due tomorrow (1-day advance notice) and today."""
    if target_date is None:
        target_date = timezone.localdate()

    tomorrow = target_date + timedelta(days=1)

    return list(
        FinancialObligation.objects.filter(
            user=user,
            status=ObligationStatus.ACTIVE,
            due_date__in=[target_date, tomorrow]
        ).order_by('due_date')
    )


@sync_to_async
def get_due_tasks_for_user(user, target_date: date = None) -> List[Any]:
    """Retrieve pending tasks/documents due tomorrow and today."""
    if target_date is None:
        target_date = timezone.localdate()

    tomorrow = target_date + timedelta(days=1)
    now = timezone.now()
    tomorrow_end = timezone.make_aware(timezone.datetime.combine(tomorrow, timezone.datetime.max.time()))

    return list(
        TaskDocument.objects.filter(
            user=user,
            status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING],
            deadline__lte=tomorrow_end,
            deadline__gte=now - timedelta(days=1)
        ).select_related('project').order_by('deadline')
    )


async def send_alert_for_task(bot: Bot, chat_id: str, task: TaskDocument):
    """Send alert message for upcoming task / document deadline"""
    deadline_str = task.deadline.strftime('%d/%m/%Y %H:%M') if task.deadline else ''
    project_str = f"[{task.project.name}] " if task.project else ""

    text = (
        f"📄 *Task & Document Deadline Alert!*\n\n"
        f"Task: *{project_str}{task.title}*\n"
    )
    if task.doc_number:
        text += f"• Doc #: `{task.doc_number}`\n"
    text += f"• Deadline: *{deadline_str}*\n\n_Please ensure timely completion!_"

    keyboard = []
    if task.file_url and task.file_url.startswith('http'):
        keyboard.append([InlineKeyboardButton("🔗 Open Document / Drive", url=task.file_url)])
    keyboard.append([InlineKeyboardButton("✅ Mark Completed", callback_data=f"done_task:{task.id}")])

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_alert_for_obligation(bot: Bot, chat_id: str, ob: FinancialObligation):
    """Format and send notification message with inline action buttons"""
    strategy = ObligationStrategyFactory.get_strategy(ob.type)
    summary = strategy.get_summary(ob)
    today = timezone.localdate()
    is_today = ob.due_date == today
    day_label = "Today! 🚨" if is_today else "Tomorrow (1 day notice) ⚠️"

    formatted_due = ob.due_date.strftime('%d/%m/%Y') if ob.due_date else ''

    # 1. Installment
    if ob.type == ObligationType.INSTALLMENT:
        next_term = int(summary.get('current_term', 0)) + 1
        total_terms = summary.get('total_terms', 0)
        lender = summary.get('lender', '')

        text = (
            f"🏍️ *Installment Due Alert: {day_label}*\n\n"
            f"Item: *{ob.title}*\n"
            f"• Due Amount: *฿{float(ob.amount):,.2f}*\n"
            f"• Term: *{next_term} / {total_terms}*\n"
            f"• Remaining Balance: ฿{float(summary.get('remaining_balance', 0)):,.2f}\n"
        )
        if lender:
            text += f"• Lender / Bank: {lender}\n"
        text += f"• Due Date: *{formatted_due}*\n\n_Tap the button below to record settlement._"

        keyboard = [[InlineKeyboardButton("✅ Paid This Term", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 2. Free Trial Hunter
    elif ob.type == ObligationType.FREE_TRIAL:
        auto_renew = float(summary.get('auto_renew_cost', ob.amount))
        email = summary.get('account_email', '')
        card = summary.get('linked_card', '')
        cancel_url = summary.get('cancel_url', '')

        text = (
            f"🚨 *Urgent! Free Trial Expiring: {day_label}*\n\n"
            f"Service: *{ob.title}*\n"
            f"• Auto-renew Charge: *฿{auto_renew:,.2f}*\n"
        )
        if email:
            text += f"• Account Email: `{email}`\n"
        if card:
            text += f"• Linked Card: {card}\n"
        text += f"• Expiration Date: *{formatted_due}*\n\n_Cancel now to avoid unwanted charges!_"

        keyboard = []
        if cancel_url and cancel_url.startswith('http'):
            keyboard.append([InlineKeyboardButton("🔗 Open Cancellation Page", url=cancel_url)])
        keyboard.append([InlineKeyboardButton("✅ Marked as Cancelled", callback_data=f"cancel_trial:{ob.id}")])

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 3. Subscriptions
    elif ob.type == ObligationType.SUBSCRIPTION:
        cycle = "Yearly" if summary.get('is_yearly') else "Monthly"
        text = (
            f"🔄 *Subscription Renewal Alert: {day_label}*\n\n"
            f"Service: *{ob.title}* ({cycle})\n"
            f"• Amount: *฿{float(ob.amount):,.2f}*\n"
            f"• Billing Date: *{formatted_due}*\n"
        )
        keyboard = [[InlineKeyboardButton("💳 Record Payment", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 4. Debt
    elif ob.type == ObligationType.DEBT:
        remaining = float(summary.get('remaining_balance', ob.amount))
        person = summary.get('counterparty', '')
        text = (
            f"🤝 *Debt Settlement Due: {day_label}*\n\n"
            f"Item: *{ob.title}*\n"
            f"• Counterparty: *{person}*\n"
            f"• Remaining Balance: *฿{remaining:,.2f}*\n"
            f"• Due Date: *{formatted_due}*\n"
        )
        keyboard = [[InlineKeyboardButton("🤝 Record Payment / Settle", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def dispatch_daily_alerts(bot: Bot):
    """
    Daily task at 10:00 AM.
    Scan all users and dispatch notifications for financial obligations and deadlines.
    """
    close_old_connections()
    try:
        users = await get_users_with_telegram()
        for user in users:
            chat_id = user.telegram_chat_id
            if not chat_id:
                continue

            # 1. Alert for financial obligations
            due_items = await get_due_tomorrow_obligations_for_user(user)
            for ob in due_items:
                try:
                    await send_alert_for_obligation(bot, chat_id, ob)
                except Exception as e:
                    print(f"Error sending financial alert to {user.username}: {e}")

            # 2. Alert for pending tasks/documents
            due_tasks = await get_due_tasks_for_user(user)
            for task in due_tasks:
                try:
                    await send_alert_for_task(bot, chat_id, task)
                except Exception as e:
                    print(f"Error sending task alert to {user.username}: {e}")
    finally:
        close_old_connections()


@sync_to_async
def get_morning_briefing_data(user):
    from apps.finance.models import FinancialObligation, ObligationStatus
    from apps.workspace.models import TaskDocument, TaskStatus
    from apps.portfolio.models import StockNewsArticle
    from apps.portfolio.services import get_portfolio_overview
    from django.utils import timezone

    today = timezone.localdate()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

    # 1. Tasks due today
    today_tasks = list(TaskDocument.objects.filter(
        user=user,
        status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING],
        deadline__range=[today_start, today_end]
    ).values('title', 'priority')[:3])

    # 2. Bills due today
    today_bills = list(FinancialObligation.objects.filter(
        user=user,
        status=ObligationStatus.ACTIVE,
        due_date=today
    ).values('title', 'amount', 'currency')[:3])

    # 3. Portfolio & market news
    portfolio = get_portfolio_overview(user)
    held_tickers = [h['ticker'] for h in portfolio.get('holdings', []) if h['position']['is_active']]

    top_news = list(StockNewsArticle.objects.filter(
        ticker__in=held_tickers
    ).order_by('-published_at').values('ticker', 'title_th', 'title', 'sentiment')[:2])

    return {
        'today': today.strftime('%d/%m/%Y'),
        'tasks': today_tasks,
        'bills': today_bills,
        'portfolio_val': float(portfolio.get('total_market_value', 0)),
        'unrealized_pnl': float(portfolio.get('total_unrealized_pnl', 0)),
        'unrealized_pct': float(portfolio.get('total_unrealized_pnl_pct', 0)),
        'news': top_news
    }


async def send_morning_briefing(bot: Bot, chat_id: str, user):
    """Send Morning Executive Briefing daily at 08:30 AM"""
    data = await get_morning_briefing_data(user)

    pnl_sign = "+" if data['unrealized_pnl'] >= 0 else ""
    pnl_icon = "🟢" if data['unrealized_pnl'] >= 0 else "🔴"

    lines = [
        f"☀️ *Executive Morning Briefing* ({data['today']})",
        f"Good morning *{user.username}*, here is your morning snapshot:\n",
        f"📈 *Portfolio Snapshot*",
        f"• Value: *฿{data['portfolio_val']:,.2f}*",
        f"• Unrealized PnL: {pnl_icon} *{pnl_sign}฿{data['unrealized_pnl']:,.2f}* ({pnl_sign}{data['unrealized_pct']:.2f}%)\n"
    ]

    # Bills today
    if data['bills']:
        lines.append("💸 *Obligations Due Today:*")
        for b in data['bills']:
            lines.append(f"  - {b['title']}: ฿{float(b['amount']):,.2f}")
        lines.append("")
    else:
        lines.append("💸 *Bills Today:* No bills due today\n")

    # Tasks today
    if data['tasks']:
        lines.append("📄 *Tasks / Documents Due Today:*")
        for t in data['tasks']:
            lines.append(f"  - {t['title']} [{t['priority']}]")
        lines.append("")
    else:
        lines.append("📄 *Tasks Today:* No urgent deadlines\n")

    # Market news
    if data['news']:
        lines.append("📰 *Portfolio Asset News:*")
        for n in data['news']:
            headline = n['title'] or n['title_th']
            sent_icon = "🟢" if n['sentiment'] == 'BULLISH' else ("🔴" if n['sentiment'] == 'BEARISH' else "⚪")
            lines.append(f"  {sent_icon} *[{n['ticker']}]* {headline}")

    text = "\n".join(lines)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')


async def dispatch_morning_briefings(bot: Bot):
    """Daily task at 08:30 AM: send morning briefing to all users."""
    close_old_connections()
    try:
        users = await get_users_with_telegram()
        for user in users:
            if user.telegram_chat_id:
                try:
                    await send_morning_briefing(bot, user.telegram_chat_id, user)
                except Exception as e:
                    print(f"Error sending morning briefing to {user.username}: {e}")
    finally:
        close_old_connections()
