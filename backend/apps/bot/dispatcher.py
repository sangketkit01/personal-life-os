import asyncio
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationStatus, ObligationType, FlowDirection
from apps.finance.strategies import ObligationStrategyFactory
from apps.workspace.models import (
    TaskDocument, TaskStatus, CalendarEvent,
    WorkspaceProject, ProjectType, InfrastructureAsset
)
from .i18n import bot_msg, currency_symbol
from .markdown_utils import escape_md
from .delivery import AutomatedBot, preferences
from apps.portfolio.identity import active_tickers, revalidate_stored_news, story_keys

User = get_user_model()

# Days before expiry that trigger an advance notice (MA contracts, domains, SSL).
EXPIRY_NOTICE_DAYS = (30, 14, 7, 3, 1, 0)
# Minimum gap between repeated watchdog alerts for the same asset.
WATCHDOG_COOLDOWN = timedelta(hours=2)


def billing_summary(ob):
    from apps.finance.strategies import ObligationStrategyFactory
    summary = ObligationStrategyFactory.get_strategy(ob.type).get_summary(ob)
    pending = summary.get('pending_dynamic_count', 0)
    amount = summary.get('total_bill_amount') if summary.get('is_itemized') else ob.amount
    if ob.subtype == 'BNPL_ACCOUNT':
        amount = summary.get('current_bill_amount', ob.amount)
    elif ob.type == 'DEBT':
        amount = summary.get('remaining_balance', ob.amount)
    return {'id': str(ob.id), 'title': ob.title, 'currency': ob.currency, 'direction': ob.direction, 'path': obligation_path(ob), 'due_date': ob.due_date.isoformat() if ob.due_date else None,
            'amount': amount, 'known_amount': summary.get('fixed_total', ob.amount),
            'pending_dynamic_count': pending, 'summary': summary}


def billing_amount_text(bill):
    summary = bill.get('summary', {})
    pending = bill.get('pending_dynamic_count', summary.get('pending_dynamic_count', 0))
    cur = currency_symbol(bill.get('currency'))
    if pending:
        known = bill.get('known_amount', summary.get('fixed_total', 0))
        return f'{cur}{float(known):,.2f} + รอกรอก {pending} รายการ'
    amount = bill.get('amount')
    return f'{cur}{float(amount or 0):,.2f}'


def obligation_path(ob):
    section = 'bnpl' if ob.subtype == 'BNPL_ACCOUNT' else {'SUBSCRIPTION': 'subscriptions', 'FREE_TRIAL': 'subscriptions', 'DEBT': 'debts'}.get(ob.type, 'installments')
    return f'/finance/{section}/{ob.id}'


def brief_links(data):
    from django.conf import settings
    if not settings.APP_PUBLIC_URL.startswith(('https://', 'http://')):
        return None
    rows = []
    for item in data.get('bills', []):
        if item.get('id') and item.get('path'):
            rows.append([InlineKeyboardButton(item['title'][:45], url=settings.APP_PUBLIC_URL + item['path'])])
    for item in data.get('tasks', [])[:2]:
        if item.get('id'):
            rows.append([InlineKeyboardButton(item['title'][:45], url=f'{settings.APP_PUBLIC_URL}/workspace/calendar?task_id={item["id"]}')])
    for item in data.get('events', [])[:1]:
        if item.get('id'):
            rows.append([InlineKeyboardButton(item['title'][:45], url=f'{settings.APP_PUBLIC_URL}/workspace/calendar?event_id={item["id"]}')])
    return InlineKeyboardMarkup(rows) if rows else None


@sync_to_async
def get_users_with_telegram() -> List[Any]:
    """Retrieve all active users who linked a Telegram Chat ID."""
    return list(User.objects.filter(telegram_chat_id__isnull=False, is_active=True))


@sync_to_async
def get_due_tomorrow_obligations_for_user(user, target_date: date = None) -> List[Any]:
    """Retrieve due/overdue obligations within each configured notice window."""
    if target_date is None:
        from zoneinfo import ZoneInfo
        target_date = timezone.localdate(timezone=ZoneInfo(preferences(user).timezone))

    rows = FinancialObligation.objects.filter(user=user, parent__isnull=True, status=ObligationStatus.ACTIVE,
        due_date__lte=target_date + timedelta(days=30)).select_related('user').order_by('due_date')
    return [ob for ob in rows if (ob.due_date - target_date).days <= max(0, min(30, int((ob.metadata or {}).get('alert_days_before', 1))))]


@sync_to_async
def get_due_tasks_for_user(user, target_date: date = None) -> List[Any]:
    """Retrieve pending tasks through the end of the user's tomorrow, including backlog."""
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(preferences(user).timezone)
    if target_date is None:
        target_date = timezone.localdate(timezone=zone)

    tomorrow = target_date + timedelta(days=1)
    tomorrow_end = timezone.make_aware(timezone.datetime.combine(tomorrow, timezone.datetime.max.time()), zone)

    return list(
        TaskDocument.objects.filter(
            user=user,
            status__in=[
                TaskStatus.TODO, TaskStatus.DOING,
                'DRAFTING', 'WAITING',  # legacy aliases, kept for old rows
            ],
            deadline__lte=tomorrow_end,
        ).select_related('project', 'user').order_by('deadline')
    )


async def send_alert_for_task(bot: Bot, chat_id: str, task: TaskDocument):
    """Send alert message for upcoming task / document deadline"""
    user = task.user
    from zoneinfo import ZoneInfo
    pref = await sync_to_async(preferences)(user)
    deadline_str = task.deadline.astimezone(ZoneInfo(pref.timezone)).strftime('%d/%m/%Y %H:%M') if task.deadline else ''
    project_str = f"[{escape_md(task.project.name)}] " if task.project else ""

    text = (
        f"{bot_msg(user, 'alert.task.title')}\n\n"
        f"{bot_msg(user, 'alert.task.task')}: *{project_str}{escape_md(task.title)}*\n"
    )
    if task.doc_number:
        text += f"{bot_msg(user, 'alert.task.doc')}`{escape_md(task.doc_number)}`\n"
    text += f"{bot_msg(user, 'alert.task.deadline')}: *{deadline_str}*\n\n{bot_msg(user, 'alert.task.footer')}"

    keyboard = []
    if task.file_url and task.file_url.startswith('http'):
        keyboard.append([InlineKeyboardButton(bot_msg(user, 'alert.task.open_btn'), url=task.file_url)])
    keyboard.append([InlineKeyboardButton(bot_msg(user, 'alert.task.done_btn'), callback_data=f"done_task:{task.id}")])

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_alert_for_obligation(bot: Bot, chat_id: str, ob: FinancialObligation):
    """Format and send notification message with inline action buttons"""
    strategy = ObligationStrategyFactory.get_strategy(ob.type)
    summary = await sync_to_async(strategy.get_summary)(ob)
    if isinstance(bot, AutomatedBot):
        bot.reference = {**(bot.reference or {}), 'obligation_id': str(ob.id),
            'due_date': ob.due_date.isoformat() if ob.due_date else None,
            'cycle_key': summary.get('cycle_key'), 'path': obligation_path(ob)}
    user = ob.user
    today = timezone.localdate()
    is_today = ob.due_date == today
    reference = getattr(bot, 'reference', None)
    if isinstance(reference, dict) and reference.get('date'):
        today = date.fromisoformat(reference['date'])
        is_today = ob.due_date == today
    day_label = bot_msg(user, 'alert.today') if is_today else bot_msg(user, 'alert.tomorrow')
    days_left = (ob.due_date - today).days if ob.due_date else 0
    if days_left not in (0, 1):
        if getattr(user, 'preferred_language', 'en') == 'th':
            day_label = f'เกินกำหนด {abs(days_left)} วัน' if days_left < 0 else f'อีก {days_left} วัน'
        else:
            day_label = f'{abs(days_left)} days overdue' if days_left < 0 else f'in {days_left} days'

    formatted_due = ob.due_date.strftime('%d/%m/%Y') if ob.due_date else ''
    meta = ob.metadata or {}
    cur = currency_symbol(ob.currency)

    # A revolving credit limit is not its current statement balance.
    if ob.subtype == 'BNPL_ACCOUNT':
        bill = summary.get('current_statement') or {}
        amount = bill.get('total_due', summary.get('current_bill_amount', 0))
        if not amount or float(amount) <= 0:
            return
        text = f"{escape_md(ob.title)} · {escape_md(day_label)}\nStatement: {escape_md(str(bill.get('statement_month', '')))}\n{cur}{float(amount):,.2f}\n{formatted_due}"
        from django.conf import settings
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('เปิดบิลและชำระ', url=settings.APP_PUBLIC_URL + obligation_path(ob))]]) if settings.APP_PUBLIC_URL else None
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown', reply_markup=markup)
    # 1. Installment
    elif ob.type == ObligationType.INSTALLMENT:
        next_term = int(summary.get('current_term', 0)) + 1
        total_terms = summary.get('total_terms', 0)
        lender = summary.get('lender', '')

        amount_val = f'{cur}{float(ob.amount):,.2f}'
        remaining_val = f'{cur}{float(summary.get("remaining_balance", 0)):,.2f}'
        text = (
            f"{bot_msg(user, 'alert.inst.title', day=day_label)}\n\n"
            f"{bot_msg(user, 'alert.inst.body', item=escape_md(ob.title), amount=amount_val, term=next_term, total=total_terms, remaining=remaining_val)}"
        )
        if lender:
            text += bot_msg(user, 'alert.inst.lender_line', lender=escape_md(lender))
        text += bot_msg(user, 'alert.inst.due_line', due=formatted_due)
        text += bot_msg(user, 'alert.inst.footer')

        keyboard = [[InlineKeyboardButton(bot_msg(user, 'alert.inst.paid_btn'), callback_data=f"pay:{ob.id}")]]
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
            f"{bot_msg(user, 'alert.trial.title', day=day_label)}\n\n"
            f"{bot_msg(user, 'alert.trial.body', service=escape_md(ob.title), amount=f'{cur}{auto_renew:,.2f}')}"
        )
        if email:
            text += bot_msg(user, 'alert.trial.email_line', email=escape_md(email))
        if card:
            text += bot_msg(user, 'alert.trial.card_line', card=escape_md(card))
        text += bot_msg(user, 'alert.trial.due_line', due=formatted_due)
        text += bot_msg(user, 'alert.trial.footer')

        keyboard = []
        if cancel_url and cancel_url.startswith('http'):
            keyboard.append([InlineKeyboardButton(bot_msg(user, 'alert.trial.cancel_url_btn'), url=cancel_url)])
        keyboard.append([InlineKeyboardButton(bot_msg(user, 'alert.trial.cancelled_btn'), callback_data=f"cancel_trial:{ob.id}")])

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 3a. MA / Client income (INFLOW) - invoice due for money coming IN
    elif ob.type == ObligationType.SUBSCRIPTION and (
        ob.direction == FlowDirection.INFLOW or meta.get('source_type') == 'MA_CONTRACT'
    ):
        client_label = meta.get('client_name') or ''
        text = (
            f"{bot_msg(user, 'billing.ma_inflow')}: {day_label}\n\n"
            f"{bot_msg(user, 'alert.ma.item_line', item=escape_md(ob.title))}"
        )
        if client_label:
            text += bot_msg(user, 'alert.ma.client_line', client=escape_md(client_label))
        text += bot_msg(user, 'alert.ma.body', amount=f'{cur}{float(ob.amount):,.2f}', due=formatted_due)
        text += bot_msg(user, 'alert.ma.footer')
        cur_ck = summary.get('cycle_key') or (meta.get('current_cycle') or {}).get('cycle_key') or (strategy.get_cycle_key(ob.due_date, meta.get('billing_cycle', 'MONTHLY')) if ob.due_date else '')
        cb_data = f"pay:{ob.id}:{cur_ck}" if cur_ck else f"pay:{ob.id}"
        keyboard = [[InlineKeyboardButton(bot_msg(user, 'billing.ma_button'), callback_data=cb_data)]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 3b. Self-funded infrastructure billing (synced from an infra asset)
    elif ob.type == ObligationType.SUBSCRIPTION and meta.get('source_type') == 'INFRA_ASSET':
        text = (
            f"{bot_msg(user, 'alert.infra.title', day=day_label)}\n\n"
            f"{bot_msg(user, 'alert.infra.body', item=escape_md(ob.title), amount=f'{cur}{float(ob.amount):,.2f}', due=formatted_due)}"
            f"{bot_msg(user, 'alert.infra.footer')}"
        )
        cur_ck = summary.get('cycle_key') or (meta.get('current_cycle') or {}).get('cycle_key') or (strategy.get_cycle_key(ob.due_date, meta.get('billing_cycle', 'MONTHLY')) if ob.due_date else '')
        cb_data = f"pay:{ob.id}:{cur_ck}" if cur_ck else f"pay:{ob.id}"
        keyboard = [[InlineKeyboardButton(bot_msg(user, 'billing.infra_button'), callback_data=cb_data)]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 4. Regular Subscriptions
    elif ob.type == ObligationType.SUBSCRIPTION:
        cycle = bot_msg(user, 'alert.sub.yearly') if summary.get('is_yearly') else bot_msg(user, 'alert.sub.monthly')
        is_itemized = summary.get('is_itemized', False)
        pending_dynamic_count = summary.get('pending_dynamic_count', 0)
        is_terminated = summary.get('is_terminated', False)

        if is_itemized:
            fixed_tot = summary.get('fixed_total', 0)
            if pending_dynamic_count > 0:
                amount_str = f"คงที่ {cur}{float(fixed_tot):,.2f} (รอกรอก {pending_dynamic_count} รายการ)"
            else:
                total_amt = summary.get('total_bill_amount', fixed_tot)
                amount_str = f"{cur}{float(total_amt):,.2f}"
        else:
            amount_str = f"{cur}{float(ob.amount):,.2f}"

        title_suffix = " (บิลสุดท้าย)" if is_terminated else ""
        text = (
            f"{bot_msg(user, 'alert.sub.title', day=day_label)}{title_suffix}\n\n"
            f"{bot_msg(user, 'alert.sub.body', service=escape_md(ob.title), cycle=cycle, amount=escape_md(amount_str), due=formatted_due)}"
        )

        if is_itemized and pending_dynamic_count > 0:
            text += f"\n\n⚠️ มี {pending_dynamic_count} รายการที่ต้องกรอกยอดในเว็บแอปก่อนชำระ"
            keyboard = []
        else:
            pay_btn_label = "ชำระบิลสุดท้าย" if is_terminated else bot_msg(user, 'alert.sub.pay_btn')
            cur_ck = summary.get('cycle_key') or (meta.get('current_cycle') or {}).get('cycle_key') or ''
            cb_data = f"pay:{ob.id}:{cur_ck}" if cur_ck else f"pay:{ob.id}"
            keyboard = [[InlineKeyboardButton(pay_btn_label, callback_data=cb_data)]]

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # 5. Debt
    elif ob.type == ObligationType.DEBT:
        remaining = float(summary.get('remaining_balance', ob.amount))
        person = summary.get('counterparty', '')
        text = (
            f"{bot_msg(user, 'alert.debt.title', day=day_label)}\n\n"
            f"{bot_msg(user, 'alert.debt.body', item=escape_md(ob.title), counterparty=escape_md(person), remaining=f'{cur}{remaining:,.2f}', due=formatted_due)}"
        )
        keyboard = [[InlineKeyboardButton(bot_msg(user, 'alert.debt.pay_btn'), callback_data=f"pay:{ob.id}")]]
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------------------------------------------------------------------
# MA contract / domain expiry reminders
# ---------------------------------------------------------------------------

@sync_to_async
def get_expiring_items_for_user(user):
    """MA contracts and infra assets whose expiry lands on a notice day."""
    today = timezone.localdate()
    notice_dates = [today + timedelta(days=d) for d in EXPIRY_NOTICE_DAYS]

    ma_projects = list(WorkspaceProject.objects.filter(
        user=user,
        ma_end_date__isnull=False,
        ma_end_date__in=notice_dates
    ).filter(
        Q(project_type=ProjectType.MA_CONTRACT) | Q(ma_amount__gt=0)
    ))
    expiring_assets = list(InfrastructureAsset.objects.filter(
        user=user,
        expiry_date__isnull=False,
        expiry_date__in=notice_dates
    ))
    return ma_projects, expiring_assets


def _expiry_day_label(user, expiry_date: date) -> str:
    days = (expiry_date - timezone.localdate()).days
    if days <= 0:
        return bot_msg(user, 'expiry.today')
    return bot_msg(user, 'expiry.days_left', n=days)


async def send_ma_expiry_alert(bot: Bot, chat_id: str, user, project: WorkspaceProject):
    label = _expiry_day_label(user, project.ma_end_date)
    text = (
        f"{bot_msg(user, 'expiry.ma.title')}\n\n"
        f"Project: *{escape_md(project.name)}*\n"
        f"• Client: {escape_md(project.client_name) or '-'}\n"
        f"• End Date: *{project.ma_end_date.strftime('%d/%m/%Y')}* ({label})\n"
    )
    if project.ma_amount and float(project.ma_amount) > 0:
        text += f"• MA Fee: {currency_symbol(project.ma_currency)}{float(project.ma_amount):,.2f} / {escape_md(project.ma_billing_cycle)}\n"
    sla = project.sla_details or {}
    if sla.get('uptime_target'):
        text += f"• SLA Uptime: {escape_md(sla['uptime_target'])}\n"
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')


async def send_asset_expiry_alert(bot: Bot, chat_id: str, user, asset: InfrastructureAsset):
    label = _expiry_day_label(user, asset.expiry_date)
    provider = f" ({asset.provider})" if asset.provider else ''
    text = (
        f"{bot_msg(user, 'expiry.asset.title')}\n\n"
        f"Resource: *{escape_md(asset.name)}*{escape_md(provider)} "
        f"[{asset.get_asset_type_display()}]\n"
        f"• Expiry Date: *{asset.expiry_date.strftime('%d/%m/%Y')}* ({label})\n"
    )
    if asset.primary_domain:
        text += f"• Domain: {escape_md(asset.primary_domain)}\n"
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')


# ---------------------------------------------------------------------------
# VPS watchdog (every 15 minutes)
# ---------------------------------------------------------------------------

def evaluate_watchdog_breaches(asset: InfrastructureAsset, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare a fresh telemetry snapshot against the asset thresholds.
    Returns a list of structured breach descriptors (empty = healthy).
    """
    breaches: List[Dict[str, Any]] = []
    if telemetry.get('error') or asset.health_status == 'OFFLINE':
        return [{'kind': 'offline'}]

    if telemetry.get('cpu_pct') is not None and telemetry['cpu_pct'] >= asset.alert_cpu_threshold:
        breaches.append({'kind': 'cpu', 'value': telemetry['cpu_pct'], 'threshold': asset.alert_cpu_threshold})
    if telemetry.get('ram_pct') is not None and telemetry['ram_pct'] >= asset.alert_ram_threshold:
        breaches.append({'kind': 'ram', 'value': telemetry['ram_pct'], 'threshold': asset.alert_ram_threshold})
    if telemetry.get('disk_pct') is not None and telemetry['disk_pct'] >= asset.alert_disk_threshold:
        breaches.append({'kind': 'disk', 'value': telemetry['disk_pct'], 'threshold': asset.alert_disk_threshold})

    for container in telemetry.get('containers') or []:
        if str(container.get('State', '')).lower() != 'running':
            breaches.append({
                'kind': 'container',
                'name': container.get('Names') or container.get('ID') or '?',
                'status': container.get('Status') or 'exited'
            })
    return breaches


@sync_to_async
def _get_watchdog_assets() -> List[InfrastructureAsset]:
    """Load every watchdog-enabled asset once (with its user prefetched)."""
    return list(InfrastructureAsset.objects.filter(
        watchdog_enabled=True
    ).select_related('user'))


@sync_to_async(thread_sensitive=False)
def _probe_one_watchdog_asset(asset) -> Optional[Dict[str, Any]]:
    """
    Probe a single watchdog asset and decide whether an alert should fire
    (cooldown-aware, recovery bypasses the cooldown). Runs on its own worker
    thread so several servers can be probed concurrently.
    """
    from apps.workspace.ssh_service import probe_server_telemetry

    close_old_connections()
    try:
        previous_status = asset.health_status
        try:
            telemetry = probe_server_telemetry(asset)
        except Exception as exc:
            telemetry = {'error': str(exc), 'containers': []}
            asset.health_status = 'OFFLINE'

        breaches = evaluate_watchdog_breaches(asset, telemetry)
        recovered = previous_status == 'OFFLINE' and asset.health_status == 'ONLINE'

        now = timezone.now()
        within_cooldown = (
            asset.last_alerted_at is not None
            and not recovered
            and (now - asset.last_alerted_at) < WATCHDOG_COOLDOWN
        )

        if (breaches or recovered) and not within_cooldown:
            asset.last_alerted_at = now
            asset.save(update_fields=['last_alerted_at', 'updated_at'])
            return {
                'asset_id': str(asset.id),
                'chat_id': asset.user.telegram_chat_id,
                'user_id': asset.user_id,
                'username': asset.user.username,
                'name': asset.name,
                'breaches': breaches,
                'recovered': recovered,
                'health': asset.health_status,
                'telemetry': telemetry,
            }
        return None
    finally:
        close_old_connections()


async def scan_watchdog_assets() -> List[Dict[str, Any]]:
    """Probe every watchdog-enabled asset, up to 5 servers concurrently."""
    sem = asyncio.Semaphore(5)

    async def _bounded_probe(asset):
        async with sem:
            return await _probe_one_watchdog_asset(asset)

    assets = await _get_watchdog_assets()
    results = await asyncio.gather(*(_bounded_probe(a) for a in assets))
    return [item for item in results if item is not None]


def _breach_line(user, breach: Dict[str, Any]) -> str:
    kind = breach.get('kind')
    if kind == 'offline':
        return f"• {bot_msg(user, 'watchdog.offline')}"
    if kind == 'container':
        return f"• {bot_msg(user, 'watchdog.container_down', name=escape_md(breach.get('name', '?')), status=escape_md(breach.get('status', '')))}"
    if kind in ('cpu', 'ram', 'disk'):
        return f"• {bot_msg(user, f'watchdog.{kind}', value=breach.get('value'), threshold=breach.get('threshold'))}"
    return f"• {kind}"


@sync_to_async
def _get_user_by_id(user_id):
    return User.objects.filter(id=user_id, is_active=True).first()


async def send_watchdog_alert(bot: Bot, item: Dict[str, Any]):
    """Render one watchdog alert (or recovery notice) and send it."""
    user = await _get_user_by_id(item['user_id'])
    if user is None:
        return
    chat_id = item.get('chat_id')
    if not chat_id:
        return

    bot = AutomatedBot(bot, user, 'infrastructure', f'watchdog:{item["asset_id"]}:{item.get("recovered", False)}:{timezone.now().strftime("%Y%m%d%H%M")}',
        {'watchdog_asset_id': str(item['asset_id']), 'recovered': bool(item.get('recovered'))})
    await render_watchdog_alert(bot, chat_id, user, item)


async def render_watchdog_alert(bot, chat_id, user, item):
    if item['recovered']:
        lines = [bot_msg(user, 'watchdog.recovered', name=escape_md(item['name']))]
    else:
        lines = [
            bot_msg(user, 'watchdog.title'),
            f"Server: *{escape_md(item['name'])}*",
            ""
        ]
        lines.extend(_breach_line(user, b) for b in item['breaches'])
        lines.append("")

    telemetry = item.get('telemetry') or {}
    if telemetry.get('uptime_human'):
        lines.append(f"Uptime: {telemetry['uptime_human']}")
    if telemetry.get('kernel'):
        lines.append(f"Kernel: {telemetry['kernel']}")

    keyboard = [[InlineKeyboardButton(
        bot_msg(user, 'watchdog.probe_again'),
        callback_data=f"probe_vps:{item['asset_id']}"
    )]]
    await bot.send_message(
        chat_id=chat_id,
        text="\n".join(lines),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def dispatch_vps_watchdog_alerts(bot: Bot):
    """Periodic job (15 min): probe watchdog assets and alert on problems."""
    close_old_connections()
    try:
        alerts = await scan_watchdog_assets()
        for item in alerts:
            try:
                await send_watchdog_alert(bot, item)
            except Exception as e:
                print(f"Error sending watchdog alert for {item.get('name')}: {e}")
    finally:
        close_old_connections()


# ---------------------------------------------------------------------------
# Scheduled dispatchers
# ---------------------------------------------------------------------------

async def dispatch_daily_alerts(bot: Bot, users=None):
    """
    Daily task at 10:00 AM.
    Scan all users and dispatch notifications for financial obligations,
    task deadlines, MA contract expiry and domain/server expiry.
    """
    close_old_connections()
    try:
        if users is None:
            users = await get_users_with_telegram()
        for user in users:
            chat_id = user.telegram_chat_id
            if not chat_id:
                continue
            from zoneinfo import ZoneInfo
            pref = await sync_to_async(preferences)(user)
            local_day = timezone.localdate(timezone=ZoneInfo(pref.timezone))

            # 1. Alert for financial obligations (incl. MA inflow / infra bills)
            due_items = await get_due_tomorrow_obligations_for_user(user, target_date=local_day)
            for ob in due_items:
                if ob.due_date < local_day:
                    continue
                try:
                    await send_alert_for_obligation(AutomatedBot(bot, user, 'bills', f'bill:{ob.id}:{local_day}', {'obligation_id': str(ob.id), 'cycle_key': (ob.metadata or {}).get('current_cycle', {}).get('cycle_key'), 'date': local_day.isoformat(), 'path': obligation_path(ob)}), chat_id, ob)
                except Exception as e:
                    print(f"Error sending financial alert to {user.username}: {e}")

            # 2. Alert for pending tasks/documents
            due_tasks = await get_due_tasks_for_user(user)
            for task in due_tasks:
                if task.deadline.astimezone(ZoneInfo(pref.timezone)).date() < local_day:
                    continue
                try:
                    await send_alert_for_task(AutomatedBot(bot, user, 'tasks', f'task:{task.id}:{task.deadline.isoformat()}:{local_day}', {'date': local_day.isoformat(), 'task_id': str(task.id), 'deadline': task.deadline.isoformat(), 'path': f'/workspace/calendar?task_id={task.id}'}), chat_id, task)
                except Exception as e:
                    print(f"Error sending task alert to {user.username}: {e}")

            for category in ('bills', 'tasks'):
                await send_overdue_digest(AutomatedBot(bot, user, category, f'overdue:{category}:{local_day}', {'date': local_day.isoformat(), 'render_overdue': category}), chat_id, user, category)

            # 3. MA contract + domain/server expiry reminders
            ma_projects, expiring_assets = await get_expiring_items_for_user(user)
            for project in ma_projects:
                try:
                    await send_ma_expiry_alert(AutomatedBot(bot, user, 'infrastructure', f'ma-expiry:{project.id}:{local_day}'), chat_id, user, project)
                except Exception as e:
                    print(f"Error sending MA expiry alert to {user.username}: {e}")
            for asset in expiring_assets:
                try:
                    await send_asset_expiry_alert(AutomatedBot(bot, user, 'infrastructure', f'asset-expiry:{asset.id}:{local_day}'), chat_id, user, asset)
                except Exception as e:
                    print(f"Error sending asset expiry alert to {user.username}: {e}")
    finally:
        close_old_connections()


@sync_to_async
def get_morning_briefing_data(user):
    from apps.finance.models import FinancialObligation, ObligationStatus
    from apps.portfolio.models import StockNewsArticle
    from apps.portfolio.services import get_portfolio_overview
    from django.utils import timezone

    from zoneinfo import ZoneInfo
    pref = preferences(user)
    local_zone = ZoneInfo(pref.timezone)
    today = timezone.localdate(timezone=local_zone)
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()), local_zone)
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()), local_zone)
    revalidate_stored_news()

    # 1. Tasks due today
    today_tasks = list(TaskDocument.objects.filter(
        user=user,
        status__in=[
            TaskStatus.TODO, TaskStatus.DOING,
            'DRAFTING', 'WAITING',  # legacy aliases
        ],
        deadline__lte=today_end
    ).order_by('deadline').values('id', 'title', 'priority')[:3])

    # 2. Bills due today
    today_bills = list(FinancialObligation.objects.filter(
        user=user,
        parent__isnull=True,
        status=ObligationStatus.ACTIVE,
        due_date__lte=today
    ).order_by('-due_date', 'title'))
    from apps.finance.strategies import ObligationStrategyFactory
    today_bills = [billing_summary(ob) for ob in today_bills]

    # 3. Calendar events today (standalone schedule)
    today_events = list(CalendarEvent.objects.filter(
        user=user,
        start_at__range=[today_start, today_end]
    ).order_by('start_at').values('id', 'title', 'start_at')[:5])

    # 4. Portfolio & market news
    portfolio = get_portfolio_overview(user)
    held_tickers = [h['ticker'] for h in portfolio.get('holdings', []) if h['position']['is_active']]
    if pref.watchlist_news:
        from apps.portfolio.models import StockWatchlist
        held_tickers += list(StockWatchlist.objects.filter(user=user).values_list('ticker', flat=True))

    top_news = list(StockNewsArticle.objects.filter(
        ticker__in=held_tickers, relevance='ACCEPTED', published_at__gte=timezone.now() - timedelta(hours=48)
    ).order_by('-published_at').values('id', 'ticker', 'title_th', 'title', 'sentiment', 'canonical_url', 'url')[:20])
    from .models import NotificationDelivery
    sent_news = set()
    for refs in NotificationDelivery.objects.filter(user=user, status__in=['SENT', 'PENDING'], created_at__gte=timezone.now()-timedelta(days=7)).values_list('reference', flat=True):
        sent_news.update(refs.get('news_urls', []))
    selected, seen = [], set(sent_news)
    for item in top_news:
        keys = story_keys(item)
        if not keys.intersection(seen):
            selected.append(item)
            seen.update(keys)
    top_news = selected[:2] if pref.portfolio_news else []

    # 5. Infrastructure fleet & MA/domain expiry snapshot (next 7 days)
    total_servers = InfrastructureAsset.objects.filter(user=user).count()
    online_servers = InfrastructureAsset.objects.filter(
        user=user, health_status='ONLINE'
    ).count()
    unhealthy_servers = list(InfrastructureAsset.objects.filter(
        user=user, health_status__in=['WARNING', 'OFFLINE']
    ).values('name', 'health_status')[:5])
    window_end = today + timedelta(days=7)
    expiring_soon_count = (
        WorkspaceProject.objects.filter(
            user=user, ma_end_date__range=[today, window_end]
        ).filter(Q(project_type=ProjectType.MA_CONTRACT) | Q(ma_amount__gt=0)).count()
        + InfrastructureAsset.objects.filter(
            user=user, expiry_date__range=[today, window_end]
        ).count()
    )

    return {
        'today': today.strftime('%d/%m/%Y'),
        'timezone': pref.timezone,
        'as_of': timezone.now().isoformat(),
        'tasks': today_tasks if pref.tasks else [],
        'bills': today_bills[:3] if pref.bills else [],
        'bills_total': len(today_bills) if pref.bills else 0,
        'events': today_events if pref.calendar else [],
        'infra': ({
            'total': total_servers,
            'online': online_servers,
            'unhealthy': unhealthy_servers,
            'expiring_soon_count': expiring_soon_count
        } if pref.infrastructure else {}),
        'portfolio_val': float(portfolio.get('total_market_value', 0)),
        'unrealized_pnl': float(portfolio.get('total_unrealized_pnl', 0)),
        'unrealized_pct': float(portfolio.get('total_unrealized_pnl_pct', 0)),
        'news': top_news,
        'quote_sync': portfolio.get('quote_sync', {}),
        'news_urls': list(set().union(*(story_keys(n) for n in top_news))) if top_news else []
    }


async def send_morning_briefing(bot: Bot, chat_id: str, user):
    """Send Morning Executive Briefing daily at 08:30 AM"""
    data = await get_morning_briefing_data(user)

    pnl_sign = "+" if data['unrealized_pnl'] >= 0 else ""
    pnl_icon = "\U0001F7E2" if data['unrealized_pnl'] >= 0 else "\U0001F534"

    lines = [
        bot_msg(user, 'brief.title', today=data['today']),
        bot_msg(user, 'brief.greeting', username=escape_md(user.username)),
        "",
        bot_msg(user, 'brief.portfolio'),
        bot_msg(user, 'brief.value', value=f"{data['portfolio_val']:,.2f}"),
        bot_msg(user, 'brief.pnl', icon=pnl_icon, sign=pnl_sign, value=f"{data['unrealized_pnl']:,.2f}", pct=f"{data['unrealized_pct']:.2f}"),
        ""
    ]

    # Bills today
    if data['bills']:
        lines.append(bot_msg(user, 'brief.bills_today'))
        for b in data['bills']:
            due = f" ({b['due_date']})" if b.get('due_date') else ''
            lines.append('  - ' + escape_md(b['title'][:180]) + ': ' + escape_md(billing_amount_text(b) + due))
        if data.get('bills_total', len(data['bills'])) > len(data['bills']):
            lines.append(f"  + {data['bills_total'] - len(data['bills'])} more")
        lines.append("")
    else:
        lines.append(bot_msg(user, 'brief.bills_none'))
        lines.append("")

    # Tasks today
    if data['tasks']:
        lines.append(bot_msg(user, 'brief.tasks_today'))
        for t in data['tasks']:
            lines.append(f"  - {escape_md(t['title'][:180])} [{t['priority']}]")
        lines.append("")
    else:
        lines.append(bot_msg(user, 'brief.tasks_none'))
        lines.append("")

    # Calendar events today
    if data['events']:
        lines.append(bot_msg(user, 'brief.events'))
        for ev in data['events']:
            from zoneinfo import ZoneInfo
            time_str = ev['start_at'].astimezone(ZoneInfo(data.get('timezone', 'Asia/Bangkok'))).strftime('%H:%M') if ev['start_at'] else ''
            lines.append(f"  - {time_str} {escape_md(ev['title'][:180])}")
        lines.append("")
    else:
        lines.append(bot_msg(user, 'brief.no_events'))
        lines.append("")

    # Infrastructure & MA snapshot
    infra = data.get('infra') or {}
    if infra.get('total', 0) > 0 or infra.get('expiring_soon_count', 0) > 0:
        lines.append(bot_msg(user, 'brief.infra'))
        if infra.get('total', 0) > 0:
            lines.append(bot_msg(user, 'brief.infra_servers', online=infra.get('online', 0), total=infra.get('total', 0)))
        for s in infra.get('unhealthy', []):
            icon = "\U0001F7E1" if s.get('health_status') == 'WARNING' else "\U0001F534"
            lines.append(f"  {icon} {escape_md(s.get('name', ''))} [{s.get('health_status')}]")
        if infra.get('expiring_soon_count', 0) > 0:
            lines.append(bot_msg(user, 'brief.infra_expiring', n=infra.get('expiring_soon_count', 0)))
        lines.append("")

    # Market news
    if data['news']:
        lines.append(bot_msg(user, 'brief.news'))
        is_th = getattr(user, 'preferred_language', 'en') == 'th'
        for n in data['news']:
            headline = (n['title_th'] or n['title']) if is_th else (n['title'] or n['title_th'])
            sent_icon = "\U0001F7E2" if n['sentiment'] == 'BULLISH' else ("\U0001F534" if n['sentiment'] == 'BEARISH' else "\u26aa")
            lines.append(f"  {sent_icon} *[{escape_md(n['ticker'])}]* {escape_md(headline[:240])}")

    if data.get('quote_sync', {}).get('stale_count', 0) or data.get('quote_sync', {}).get('missing_count', 0):
        lines.append('⚠️ Portfolio contains stale or unavailable quotes. /portfolio')
    text = "\n".join(lines)
    if isinstance(bot, AutomatedBot):
        bot.reference = {**(bot.reference or {}), 'news_urls': data.get('news_urls', [])}
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown', reply_markup=brief_links(data))
    return {'news_urls': data.get('news_urls', [])}


@sync_to_async
def overdue_data(user, category):
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(preferences(user).timezone)
    day = timezone.localdate(timezone=zone)
    if category == 'bills':
        rows = FinancialObligation.objects.filter(user=user, parent__isnull=True, status='ACTIVE', due_date__lt=day).order_by('due_date')
        return rows.count(), [billing_summary(ob) for ob in rows[:5]]
    start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()), zone)
    rows = TaskDocument.objects.filter(user=user, deadline__lt=start, status__in=['TODO', 'DOING', 'DRAFTING', 'WAITING']).order_by('deadline')
    return rows.count(), [{'id': str(task.id), 'title': task.title, 'path': f'/workspace/calendar?task_id={task.id}'} for task in rows[:5]]


async def send_overdue_digest(bot, chat_id, user, category):
    count, rows = await overdue_data(user, category)
    if not count:
        return
    th = getattr(user, 'preferred_language', 'en') == 'th'
    title = ('บิลค้างชำระ' if category == 'bills' else 'งานเลยกำหนด') if th else ('Overdue bills' if category == 'bills' else 'Overdue tasks')
    lines = [f'⏰ {title}: {count}']
    for row in rows:
        text = row['title'][:160]
        if category == 'bills':
            text += ': ' + billing_amount_text(row)
        lines.append(text)
    if count > len(rows):
        lines.append(f'+ {count - len(rows)} more')
    markup = brief_links({'bills': rows, 'tasks': [], 'events': []})
    await bot.send_message(chat_id=chat_id, text='\n'.join(lines), reply_markup=markup)


async def dispatch_morning_briefings(bot: Bot):
    """Daily task at 08:30 AM: send morning briefing to all users."""
    close_old_connections()
    try:
        users = await get_users_with_telegram()
        for user in users:
            if user.telegram_chat_id:
                try:
                    await send_morning_briefing(AutomatedBot(bot, user, 'briefing', f'brief:{timezone.localdate()}', {'date': timezone.localdate().isoformat(), 'render_brief': True}), user.telegram_chat_id, user)
                except Exception as e:
                    print(f"Error sending morning briefing to {user.username}: {e}")
    finally:
        close_old_connections()
