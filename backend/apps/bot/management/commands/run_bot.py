import sys
import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import BotCommand
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
    dispatch_vps_watchdog_alerts
)


async def post_init_commands(application):
    """Register slash commands in the Telegram chat menu."""
    commands = [
        BotCommand("brief", "Executive Morning Briefing summary"),
        BotCommand("status", "Monthly Burn Rate & upcoming bills"),
        BotCommand("portfolio", "Investment portfolio & PnL overview"),
        BotCommand("news", "Latest market & asset news"),
        BotCommand("servers", "Servers & infrastructure live status"),
        BotCommand("ma", "MA contracts, expiry & next billing"),
        BotCommand("help", "Show available commands & guide"),
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as exc:
        print(f"[WARN] Could not register Telegram bot commands: {exc}")


async def scheduled_vps_watchdog(context):
    """Job queue callback for the 15-minute VPS watchdog sweep."""
    print(f"[{datetime.datetime.now()}] Running VPS Watchdog sweep...")
    await dispatch_vps_watchdog_alerts(context.bot)


async def scheduled_hourly_news_sync(context):
    """Hourly callback to ingest and translate portfolio market news."""
    from asgiref.sync import sync_to_async
    from apps.portfolio.news_service import sync_all_portfolio_news
    print(f"[{datetime.datetime.now()}] Running Hourly Portfolio News Sync & Translation...")
    await sync_to_async(sync_all_portfolio_news, thread_sensitive=False)()


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
        app = ApplicationBuilder().token(token).post_init(post_init_commands).build()

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
            
            from apps.bot.automation import scheduled_prices, scheduled_notifications
            job_queue.run_repeating(scheduled_prices, interval=60, first=1, name='portfolio_prices', job_kwargs={'max_instances': 1, 'coalesce': True})
            job_queue.run_repeating(scheduled_notifications, interval=60, first=20, name='notification_dispatch', job_kwargs={'max_instances': 1, 'coalesce': True})
            self.stdout.write(self.style.SUCCESS("[OK] Configurable briefing and notification dispatcher registered"))

            # The minute dispatcher catches up after restarts and deduplicates each local-day event.
            self.stdout.write(self.style.SUCCESS("[OK] Local-day due reminders and restart catch-up enabled"))

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
