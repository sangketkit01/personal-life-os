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
    """ดึงผู้ใช้ทุกคนที่มีการผูก Telegram Chat ID ไว้"""
    return list(User.objects.filter(telegram_chat_id__isnull=False, is_active=True))


@sync_to_async
def get_due_tomorrow_obligations_for_user(user, target_date: date = None) -> List[Any]:
    """ดึงบิลที่จะครบกำหนดในวันพรุ่งนี้ (ล่วงหน้า 1 วัน) และวันนี้"""
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
    """ดึงงาน/เอกสารที่จะถึงกำหนดส่งในวันพรุ่งนี้และวันนี้ที่ยังไม่เสร็จ"""
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
    """ส่งข้อความแจ้งเตือนกำหนดส่งเอกสาร/งาน"""
    deadline_str = task.deadline.strftime('%d/%m/%Y %H:%M') if task.deadline else ''
    project_str = f"[{task.project.name}] " if task.project else ""

    text = (
        f"📄 *แจ้งเตือนกำหนดส่งงาน/เอกสาร!*\n\n"
        f"ชื่องาน: *{project_str}{task.title}*\n"
    )
    if task.doc_number:
        text += f"• เลขที่เอกสาร: `{task.doc_number}`\n"
    text += f"• กำหนดส่ง: *{deadline_str}*\n\n_อย่าลืมส่งงานให้ตรงเวลานะครับ!_"

    keyboard = []
    if task.file_url and task.file_url.startswith('http'):
        keyboard.append([InlineKeyboardButton("🔗 เปิดดูเอกสาร / Drive", url=task.file_url)])
    keyboard.append([InlineKeyboardButton("✅ ทำเสร็จแล้ว (Completed)", callback_data=f"done_task:{task.id}")])

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_alert_for_obligation(bot: Bot, chat_id: str, ob: FinancialObligation):
    """ฟังก์ชันจัด Format ข้อความและแนบปุ่มส่งแจ้งเตือนรายบิล"""
    strategy = ObligationStrategyFactory.get_strategy(ob.type)
    summary = strategy.get_summary(ob)
    today = timezone.localdate()
    is_today = ob.due_date == today
    day_label = "วันนี้! 🚨" if is_today else "พรุ่งนี้ (ล่วงหน้า 1 วัน) ⚠️"

    formatted_due = ob.due_date.strftime('%d/%m/%Y') if ob.due_date else ''

    # 1. เคสผ่อนชำระ (Installment)
    if ob.type == ObligationType.INSTALLMENT:
        next_term = int(summary.get('current_term', 0)) + 1
        total_terms = summary.get('total_terms', 0)
        lender = summary.get('lender', '')

        text = (
            f"🏍️ *แจ้งเตือนค่างวด: {day_label}*\n\n"
            f"รายการ: *{ob.title}*\n"
            f"• ยอดชำระ: *฿{float(ob.amount):,.2f}*\n"
            f"• งวดที่ต้องจ่าย: *{next_term} / {total_terms}*\n"
            f"• ยอดหนี้คงเหลือ: ฿{float(summary.get('remaining_balance', 0)):,.2f}\n"
        )
        if lender:
            text += f"• สถาบันการเงิน: {lender}\n"
        text += f"• วันครบกำหนด: *{formatted_due}*\n\n_อย่าลืมโอนจ่ายนะ! กดปุ่มด้านล่างเพื่อตัดงวดได้ทันที_"

        keyboard = [[InlineKeyboardButton("✅ จ่ายงวดนี้แล้ว", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 2. เคส Free Trial Hunter
    elif ob.type == ObligationType.FREE_TRIAL:
        auto_renew = float(summary.get('auto_renew_cost', ob.amount))
        email = summary.get('account_email', '')
        card = summary.get('linked_card', '')
        cancel_url = summary.get('cancel_url', '')

        text = (
            f"🚨 *ด่วน! Free Trial จะหมดอายุ: {day_label}*\n\n"
            f"บริการ: *{ob.title}*\n"
            f"• ยอดที่จะโดนตัดถ้าลืมยกเลิก: *฿{auto_renew:,.2f}*\n"
        )
        if email:
            text += f"• ใช้อีเมลสมัคร: `{email}`\n"
        if card:
            text += f"• ผูกบัตร: {card}\n"
        text += f"• หมดอายุ: *{formatted_due}*\n\n_รีบกดยกเลิกเพื่อป้องกันการถูกตัดเงินอัตโนมัติ!_"

        keyboard = []
        if cancel_url and cancel_url.startswith('http'):
            keyboard.append([InlineKeyboardButton("🔗 เปิดลิงก์หน้ากดยกเลิก", url=cancel_url)])
        keyboard.append([InlineKeyboardButton("✅ กดยกเลิกเรียบร้อยแล้ว", callback_data=f"cancel_trial:{ob.id}")])

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 3. เคส Subscriptions
    elif ob.type == ObligationType.SUBSCRIPTION:
        cycle = "รายปี" if summary.get('is_yearly') else "รายเดือน"
        text = (
            f"🔄 *แจ้งเตือนรอบตัดเงิน Subscription: {day_label}*\n\n"
            f"บริการ: *{ob.title}* ({cycle})\n"
            f"• ยอดเงิน: *฿{float(ob.amount):,.2f}*\n"
            f"• วันตัดรอบ: *{formatted_due}*\n"
        )
        keyboard = [[InlineKeyboardButton("💳 บันทึกชำระเงินแล้ว", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 4. เคส หนี้สิน (Debt)
    elif ob.type == ObligationType.DEBT:
        remaining = float(summary.get('remaining_balance', ob.amount))
        person = summary.get('counterparty', '')
        text = (
            f"🤝 *แจ้งเตือนกำหนดคืนหนี้สิน: {day_label}*\n\n"
            f"รายการ: *{ob.title}*\n"
            f"• คู่สัญญา: *{person}*\n"
            f"• ยอดหนี้คงเหลือ: *฿{remaining:,.2f}*\n"
            f"• วันกำหนดคืน: *{formatted_due}*\n"
        )
        keyboard = [[InlineKeyboardButton("🤝 ทยอยคืน / คืนครบแล้ว", callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def dispatch_daily_alerts(bot: Bot):
    """
    งานประจำวันเวลา 10:00 น.
    กวาดหา User ทุกคน และยิงแจ้งเตือนทั้งบิลการเงินและเอกสารที่ต้องส่ง
    """
    close_old_connections()
    try:
        users = await get_users_with_telegram()
        for user in users:
            chat_id = user.telegram_chat_id
            if not chat_id:
                continue

            # 1. ยิงเตือนบิลการเงิน
            due_items = await get_due_tomorrow_obligations_for_user(user)
            for ob in due_items:
                try:
                    await send_alert_for_obligation(bot, chat_id, ob)
                except Exception as e:
                    print(f"Error sending financial alert to {user.username}: {e}")

            # 2. ยิงเตือนงานเอกสารที่ต้องส่ง
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

    # 1. งานที่ต้องส่งวันนี้
    today_tasks = list(TaskDocument.objects.filter(
        user=user,
        status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING],
        deadline__range=[today_start, today_end]
    ).values('title', 'priority')[:3])

    # 2. บิลที่ต้องจ่ายวันนี้
    today_bills = list(FinancialObligation.objects.filter(
        user=user,
        status=ObligationStatus.ACTIVE,
        due_date=today
    ).values('title', 'amount', 'currency')[:3])

    # 3. พอร์ต & ข่าวเด่นแปลไทย
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
    """ส่งข้อความ Morning Executive Briefing ประจำวันเวลา 08:30 น."""
    data = await get_morning_briefing_data(user)

    pnl_sign = "+" if data['unrealized_pnl'] >= 0 else ""
    pnl_icon = "🟢" if data['unrealized_pnl'] >= 0 else "🔴"

    lines = [
        f"☀️ *Executive Morning Briefing* ({data['today']})",
        f"สวัสดีคุณ *{user.username}* สรุปสถานการณ์เช้านี้:\n",
        f"📈 *Portfolio Snapshot*",
        f"• มูลค่าพอร์ต: *฿{data['portfolio_val']:,.2f}*",
        f"• ผลตอบแทนสะสม: {pnl_icon} *{pnl_sign}฿{data['unrealized_pnl']:,.2f}* ({pnl_sign}{data['unrealized_pct']:.2f}%)\n"
    ]

    # บิลวันนี้
    if data['bills']:
        lines.append("💸 *บิลที่ครบกำหนดวันนี้:*")
        for b in data['bills']:
            lines.append(f"  - {b['title']}: ฿{float(b['amount']):,.2f}")
        lines.append("")
    else:
        lines.append("💸 *บิลวันนี้:* ไม่มีบิลต้องชำระ\n")

    # งานวันนี้
    if data['tasks']:
        lines.append("📄 *งาน/เอกสารที่ต้องส่งวันนี้:*")
        for t in data['tasks']:
            lines.append(f"  - {t['title']} [{t['priority']}]")
        lines.append("")
    else:
        lines.append("📄 *ภารกิจวันนี้:* ไม่มีกำหนดส่งงานด่วน\n")

    # ข่าวหุ้นแปลไทย
    if data['news']:
        lines.append("📰 *ข่าวด่วนสินทรัพย์ในพอร์ต (แปลไทย):*")
        for n in data['news']:
            headline = n['title_th'] or n['title']
            sent_icon = "🟢" if n['sentiment'] == 'BULLISH' else ("🔴" if n['sentiment'] == 'BEARISH' else "⚪")
            lines.append(f"  {sent_icon} *[{n['ticker']}]* {headline}")

    text = "\n".join(lines)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')


async def dispatch_morning_briefings(bot: Bot):
    """งานประจำวัน 08:30 น. ส่ง Morning Briefing ให้ผู้ใช้ทุกคน"""
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
