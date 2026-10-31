"""Scheduled entry points. Prices, news and delivery run independently."""
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import timedelta
from .delivery import AutomatedBot, preferences, flush_deliveries
from .dispatcher import get_users_with_telegram, send_morning_briefing


def prepare_rules_and_reports():
    from apps.portfolio.automation import evaluate_price_alerts, prepare_close_reports
    from .leases import job_lease
    with job_lease('portfolio-rules-and-reports') as acquired:
        if acquired:
            evaluate_price_alerts()
            prepare_close_reports()


async def scheduled_prices(context):
    from apps.portfolio.quotes import sync_tracked_prices
    await sync_to_async(sync_tracked_prices, thread_sensitive=False)()


async def scheduled_notifications(context):
    from zoneinfo import ZoneInfo
    from apps.workspace.models import CalendarEvent
    await sync_to_async(prepare_rules_and_reports, thread_sensitive=False)()
    for user in await get_users_with_telegram():
        if not user.telegram_chat_id:
            continue
        pref = await sync_to_async(preferences)(user)
        local = timezone.now().astimezone(ZoneInfo(pref.timezone))
        day = local.date().isoformat()
        if local.hour >= 10:
            from .dispatcher import dispatch_daily_alerts
            await dispatch_daily_alerts(context.bot, users=[user])
        if pref.briefing and local.time().replace(tzinfo=None) >= pref.briefing_time:
            from .models import NotificationDelivery
            exists = await sync_to_async(NotificationDelivery.objects.filter(user=user, event_key=f'brief:{day}').exists)()
            if not exists:
                await send_morning_briefing(AutomatedBot(context.bot, user, 'briefing', f'brief:{day}', {'date': day, 'render_brief': True}), user.telegram_chat_id, user)
        if pref.calendar:
            events = await sync_to_async(list)(CalendarEvent.objects.filter(user=user, start_at__gte=timezone.now(), start_at__lte=timezone.now()+timedelta(minutes=30)).values('id', 'title', 'start_at'))
            for event in events:
                reference = {'event_id': str(event['id']), 'start_at': event['start_at'].isoformat(), 'path': f'/workspace/calendar?event_id={event["id"]}'}
                await AutomatedBot(context.bot, user, 'calendar', f'event:{event["id"]}:{event["start_at"].isoformat()}', reference).send_message(
                    text=f"📅 {event['title']}\n{event['start_at'].astimezone(ZoneInfo(pref.timezone)).strftime('%H:%M %Z')}")
    await flush_deliveries(context.bot)
