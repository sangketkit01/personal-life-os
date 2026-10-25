import sys
import datetime
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from apps.bot.handlers.start import (
    start_handler,
    status_handler,
    help_handler,
    portfolio_handler,
    brief_handler,
    news_handler,
    servers_handler,
    ma_handler
)
from apps.bot.handlers.callbacks import callback_query_handler
from apps.bot.handlers.messages import text_message_handler
from apps.bot.dispatcher import (
    dispatch_daily_alerts,
    dispatch_morning_briefings,
    dispatch_vps_watchdog_alerts
)


async def scheduled_morning_briefing(context):
    """Job queue callback for 08:30 AM Morning Executive Briefing."""
    print(f"[{datetime.datetime.now()}] Running 08:30 AM Morning Executive Briefing...")
    await dispatch_morning_briefings(context.bot)


async def scheduled_daily_job(context):
    """Job queue callback for 10:00 AM daily alerts (bills and task deadlines)."""
    print(f"[{datetime.datetime.now()}] Running 10:00 AM daily alert check...")
    await dispatch_daily_alerts(context.bot)


async def scheduled_vps_watchdog(context):
    """Job queue callback for the 15-minute VPS watchdog sweep."""
    print(f"[{datetime.datetime.now()}] Running VPS Watchdog sweep...")
    await dispatch_vps_watchdog_alerts(context.bot)


async def scheduled_hourly_news_sync(context):
    """Hourly callback to ingest and translate portfolio market news."""
    from asgiref.sync import sync_to_async
    from apps.portfolio.news_service import sync_all_portfolio_news
    print(f"[{datetime.datetime.now()}] Running Hourly Portfolio News Sync & Translation...")
    await sync_to_async(sync_all_portfolio_news)()


class Command(BaseCommand):
    help = 'Starts the Telegram Butler Bot worker in polling mode'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured in .env"))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("Starting Telegram Butler Bot worker..."))
        self.stdout.write(f"Bot Username: @{settings.TELEGRAM_BOT_USERNAME}")

        # Create Application instance
        app = ApplicationBuilder().token(token).build()

        # 1. Command Handlers
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("status", status_handler))
        app.add_handler(CommandHandler("portfolio", portfolio_handler))
        app.add_handler(CommandHandler("brief", brief_handler))
        app.add_handler(CommandHandler("news", news_handler))
        app.add_handler(CommandHandler("servers", servers_handler))
        app.add_handler(CommandHandler("ma", ma_handler))
        app.add_handler(CommandHandler("help", help_handler))

        # 2. Inline Keyboard Callback Handler
        app.add_handler(CallbackQueryHandler(callback_query_handler))

        # 3. Quick-Capture Text Message Handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

        # 4. Register Scheduled Alerts & Hourly Ingestion (Bangkok Time)
        job_queue = app.job_queue
        if job_queue:
            bangkok_tz = ZoneInfo("Asia/Bangkok")
            
            # 08:30 AM Morning Briefing
            brief_time = datetime.time(hour=8, minute=30, second=0, tzinfo=bangkok_tz)
            job_queue.run_daily(scheduled_morning_briefing, time=brief_time, name="daily_830am_briefing")
            self.stdout.write(self.style.SUCCESS("[OK] 08:30 AM Morning Briefing Scheduler registered (Asia/Bangkok)"))

            # 10:00 AM Daily Alerts
            alert_time = datetime.time(hour=10, minute=0, second=0, tzinfo=bangkok_tz)
            job_queue.run_daily(scheduled_daily_job, time=alert_time, name="daily_10am_alert")
            self.stdout.write(self.style.SUCCESS("[OK] 10:00 AM Daily Alert Scheduler registered (Asia/Bangkok)"))

            # Hourly News Ingestion & Translation
            job_queue.run_repeating(scheduled_hourly_news_sync, interval=3600, first=10, name="hourly_news_sync")
            self.stdout.write(self.style.SUCCESS("[OK] Hourly News Sync & Translation Scheduler registered"))

            # VPS / MA Watchdog every 15 minutes
            job_queue.run_repeating(scheduled_vps_watchdog, interval=900, first=30, name="vps_watchdog_15min")
            self.stdout.write(self.style.SUCCESS("[OK] VPS Watchdog Scheduler registered (every 15 min)"))
        else:
            self.stdout.write(self.style.WARNING("JobQueue is not enabled; install python-telegram-bot[job-queue]"))

        self.stdout.write(self.style.SUCCESS("Bot is now listening for messages... Press Ctrl+C to stop."))
        # Start polling
        app.run_polling(drop_pending_updates=True)
