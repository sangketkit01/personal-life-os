"""Durable automated messages with per-user preferences, quiet hours and deduplication."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from telegram import InlineKeyboardMarkup
from telegram.error import RetryAfter, NetworkError
from django.conf import settings
from .models import NotificationPreference, NotificationDelivery


def preferences(user):
    return NotificationPreference.objects.get_or_create(user=user)[0]


def quiet_until(pref, now):
    local = now.astimezone(ZoneInfo(pref.timezone))
    start, end = pref.quiet_start, pref.quiet_end
    if not start or not end or start == end:
        return now
    clock = local.time().replace(tzinfo=None)
    quiet = start <= clock < end if start < end else clock >= start or clock < end
    if not quiet:
        return now
    day = local.date() + (timedelta(days=1) if start > end and clock >= start else timedelta())
    return datetime.combine(day, end, tzinfo=local.tzinfo)


def enabled(pref, category):
    return bool(getattr(pref, category, True))


def add_app_link(payload, reference):
    path = reference.get('path')
    if path and path.startswith('/') and settings.APP_PUBLIC_URL.startswith(('https://', 'http://')):
        markup = payload.get('reply_markup') or {'inline_keyboard': []}
        markup['inline_keyboard'].append([{'text': 'เปิดรายการ', 'url': settings.APP_PUBLIC_URL + path}])
        payload['reply_markup'] = markup
    return payload


@sync_to_async
def _enqueue(user, category, event_key, payload, reference):
    pref = preferences(user)
    if not enabled(pref, category) or not user.is_active or not user.telegram_chat_id:
        return None
    if reference.get('watchdog_asset_id'):
        NotificationDelivery.objects.filter(user=user, status='PENDING',
            reference__watchdog_asset_id=reference['watchdog_asset_id']).exclude(event_key=event_key).update(status='SKIPPED')
    row, _ = NotificationDelivery.objects.get_or_create(user=user, event_key=event_key, defaults={
        'category': category, 'payload': payload, 'reference': reference,
        'available_at': quiet_until(pref, timezone.now())})
    return row.pk


@sync_to_async
def _claim(pk):
    from apps.finance.models import FinancialObligation
    from apps.finance.strategies import ObligationStrategyFactory
    now = timezone.now()
    with transaction.atomic():
        row = NotificationDelivery.objects.select_for_update().select_related('user').get(pk=pk)
        if row.status != 'PENDING' or row.available_at > now:
            return None
        pref = preferences(row.user)
        if not row.user.is_active or not row.user.telegram_chat_id or not enabled(pref, row.category):
            row.status = 'SKIPPED'
            row.save(update_fields=['status'])
            return None
        after = quiet_until(pref, now)
        if after > now:
            row.available_at = after
            row.save(update_fields=['available_at'])
            return None
        ref = row.reference
        if ref.get('task_id'):
            from apps.workspace.models import TaskDocument
            task = TaskDocument.objects.filter(pk=ref['task_id'], user=row.user).exclude(status__in=['DONE', 'ARCHIVED', 'COMPLETED']).first()
            local = now.astimezone(ZoneInfo(pref.timezone))
            tomorrow = local.date() + timedelta(days=1)
            if (not task or not task.deadline or task.deadline.astimezone(local.tzinfo).date() > tomorrow
                    or (ref.get('deadline') and task.deadline != datetime.fromisoformat(ref['deadline']))):
                row.status = 'SKIPPED'
                row.save(update_fields=['status'])
                return None
        if ref.get('price_alert_id'):
            from apps.portfolio.models import PriceAlert
            if not PriceAlert.objects.filter(pk=ref['price_alert_id'], user=row.user, revision=ref.get('revision'), triggered_at__isnull=False).exists():
                row.status = 'SKIPPED'
                row.save(update_fields=['status'])
                return None
        if ref.get('event_id'):
            from apps.workspace.models import CalendarEvent
            if not CalendarEvent.objects.filter(pk=ref['event_id'], user=row.user, start_at__gt=now, start_at=ref['start_at']).exists():
                row.status = 'SKIPPED'
                row.save(update_fields=['status'])
                return None
        if ref.get('obligation_id'):
            ob = FinancialObligation.objects.filter(id=ref['obligation_id'], user=row.user, status='ACTIVE').first()
            if not ob or (ref.get('due_date') and (ob.due_date.isoformat() if ob.due_date else None) != ref['due_date']) or (ref.get('cycle_key') and ObligationStrategyFactory.get_strategy(ob.type).get_summary(ob).get('cycle_key') != ref['cycle_key']):
                row.status = 'SKIPPED'
                row.save(update_fields=['status'])
                return None
        if ref.get('date') and ref['date'] != now.astimezone(ZoneInfo(pref.timezone)).date().isoformat():
            row.status = 'SKIPPED'
            row.save(update_fields=['status'])
            return None
        row.status, row.claimed_at, row.attempts = 'SENDING', now, row.attempts + 1
        row.save(update_fields=['status', 'claimed_at', 'attempts'])
        return row.user.telegram_chat_id, row.payload, row.attempts, row.user, row.reference


@sync_to_async
def _finish(pk, status, error='', message_id=None, delay=0):
    error = str(error)
    if settings.TELEGRAM_BOT_TOKEN:
        error = error.replace(settings.TELEGRAM_BOT_TOKEN, '[redacted]')
    values = {'status': status, 'error': error[:500]}
    if status == 'SENT':
        values.update(sent_at=timezone.now(), message_id=message_id if isinstance(message_id, int) else None)
    if delay:
        values['available_at'] = values['retry_not_before'] = timezone.now() + timedelta(seconds=delay)
    NotificationDelivery.objects.filter(pk=pk, status='SENDING').update(**values)


async def render_current_payload(chat_id, user, reference):
    class Capture:
        def __init__(self):
            self.payload = None
            self.reference = reference
        async def send_message(self, **kwargs):
            self.payload = kwargs
    capture = Capture()
    fresh = {}
    if reference.get('render_brief'):
        from .dispatcher import send_morning_briefing
        fresh = await send_morning_briefing(capture, chat_id, user) or {}
    elif reference.get('render_overdue'):
        from .dispatcher import send_overdue_digest
        await send_overdue_digest(capture, chat_id, user, reference['render_overdue'])
    elif reference.get('obligation_id'):
        from apps.finance.models import FinancialObligation
        from .dispatcher import send_alert_for_obligation
        ob = await sync_to_async(FinancialObligation.objects.select_related('user').filter(id=reference['obligation_id'], user=user, status='ACTIVE').first)()
        if ob:
            await send_alert_for_obligation(capture, chat_id, ob)
    elif reference.get('task_id'):
        from apps.workspace.models import TaskDocument
        from .dispatcher import send_alert_for_task
        task = await sync_to_async(TaskDocument.objects.select_related('user', 'project').filter(pk=reference['task_id'], user=user).first)()
        if task:
            await send_alert_for_task(capture, chat_id, task)
    elif reference.get('watchdog_asset_id'):
        from apps.workspace.models import InfrastructureAsset
        from .dispatcher import evaluate_watchdog_breaches, render_watchdog_alert
        asset = await sync_to_async(InfrastructureAsset.objects.filter(pk=reference['watchdog_asset_id'], user=user, watchdog_enabled=True).first)()
        if asset and asset.last_checked_at and timezone.now()-asset.last_checked_at <= timedelta(minutes=30):
            breaches = evaluate_watchdog_breaches(asset, asset.last_telemetry or {})
            recovered = reference.get('recovered', False)
            if (recovered and asset.health_status == 'ONLINE' and not breaches) or (not recovered and breaches):
                await render_watchdog_alert(capture, chat_id, user, {'asset_id':str(asset.id), 'name':asset.name,
                    'recovered':recovered, 'breaches':breaches, 'telemetry':asset.last_telemetry})
    else:
        return False, None, reference
    payload = capture.payload
    if payload is None:
        return True, None, reference
    payload.pop('chat_id', None)
    markup = payload.get('reply_markup')
    if markup is not None and hasattr(markup, 'to_dict'):
        payload['reply_markup'] = markup.to_dict()
    return True, add_app_link(payload, reference), {**reference, **fresh}


async def deliver_one(bot, pk):
    claim = await _claim(pk)
    if not claim:
        return
    chat_id, payload, attempts, user, reference = claim
    try:
        rendered, current, reference = await render_current_payload(chat_id, user, reference)
        if rendered:
            if current is None:
                await _finish(pk, 'SKIPPED')
                return
            payload = current
            await sync_to_async(NotificationDelivery.objects.filter(pk=pk).update)(payload=payload, reference=reference)
    except Exception as exc:
        # Rendering failed before any Telegram request, so a bounded retry is safe.
        await _finish(pk, 'PENDING' if attempts < 3 else 'FAILED', exc, delay=60)
        return
    payload = dict(payload)
    if payload.get('reply_markup'):
        payload['reply_markup'] = InlineKeyboardMarkup.de_json(payload['reply_markup'], bot)
    try:
        message = await bot.send_message(chat_id=chat_id, **payload)
        await _finish(pk, 'SENT', message_id=getattr(message, 'message_id', None))
    except RetryAfter as exc:
        delay = exc.retry_after.total_seconds() if isinstance(exc.retry_after, timedelta) else exc.retry_after
        await _finish(pk, 'PENDING' if attempts < 3 else 'FAILED', exc, delay=max(1, int(delay)))
    except NetworkError as exc:
        # A timeout can happen after Telegram accepted the message. Do not blindly resend it.
        await _finish(pk, 'UNKNOWN', exc)
    except Exception as exc:
        await _finish(pk, 'FAILED', exc)


async def queue_message(bot, user, category, event_key, reference=None, **payload):
    payload.pop('chat_id', None)
    markup = payload.get('reply_markup')
    if markup is not None and hasattr(markup, 'to_dict'):
        payload['reply_markup'] = markup.to_dict()
    pk = await _enqueue(user, category, event_key, payload, reference or {})
    if pk:
        await deliver_one(bot, pk)


class AutomatedBot:
    """Keep message rendering shared with commands and use a durable send for scheduled jobs."""
    def __init__(self, bot, user, category, event_key, reference=None):
        self.bot, self.user, self.category, self.event_key, self.reference = bot, user, category, event_key, reference

    async def send_message(self, **kwargs):
        markup = kwargs.get('reply_markup')
        if markup is not None and hasattr(markup, 'to_dict'):
            kwargs['reply_markup'] = markup.to_dict()
        kwargs = add_app_link(kwargs, self.reference or {})
        await queue_message(self.bot, self.user, self.category, self.event_key, self.reference, **kwargs)


def reschedule_pending(user, pref, now=None):
    """Apply quiet-hour changes without bypassing Telegram/render retry backoff."""
    now = now or timezone.now()
    after = quiet_until(pref, now)
    for row in NotificationDelivery.objects.filter(user=user, status='PENDING'):
        ready = max(after, row.retry_not_before or now)
        NotificationDelivery.objects.filter(pk=row.pk, status='PENDING').update(available_at=ready)


@sync_to_async
def _pending():
    now = timezone.now()
    NotificationDelivery.objects.filter(status='SENDING', claimed_at__lt=now - timedelta(minutes=5)).update(status='UNKNOWN', error='Worker stopped during send; delivery outcome unknown')
    return list(NotificationDelivery.objects.filter(status='PENDING', available_at__lte=now).order_by('available_at').values_list('pk', flat=True)[:100])


async def flush_deliveries(bot):
    for pk in await _pending():
        await deliver_one(bot, pk)
