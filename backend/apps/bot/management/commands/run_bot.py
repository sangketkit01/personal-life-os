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
    news_handler
)
from apps.bot.handlers.callbacks import callback_query_handler
from apps.bot.handlers.messages import text_message_handler
from apps.bot.dispatcher import dispatch_daily_alerts, dispatch_morning_briefings


async def scheduled_morning_briefing(context):
    """Callback สำหรับ Job Queue เวลา 08:30 น. (Morning Executive Briefing)"""
    print(f"[{datetime.datetime.now()}] Running 08:30 AM Morning Executive Briefing...")
    await dispatch_morning_briefings(context.bot)


async def scheduled_daily_job(context):
    """Callback สำหรับ Job Queue เวลา 10:00 น. (บิลการเงิน & กำหนดส่งงาน)"""
    print(f"[{datetime.datetime.now()}] Running 10:00 AM daily alert check...")
    await dispatch_daily_alerts(context.bot)


async def scheduled_hourly_news_sync(context):
    """Callback ประจำชั่วโมง ดึงข่าวและแปลภาษาอัตโนมัติสำหรับหุ้นในพอร์ต"""
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

        # สร้าง Application instance
        app = ApplicationBuilder().token(token).build()

        # 1. Command Handlers
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("status", status_handler))
        app.add_handler(CommandHandler("portfolio", portfolio_handler))
        app.add_handler(CommandHandler("brief", brief_handler))
        app.add_handler(CommandHandler("news", news_handler))
        app.add_handler(CommandHandler("help", help_handler))

        # 2. Inline Keyboard Callback Handler
        app.add_handler(CallbackQueryHandler(callback_query_handler))

        # 3. Quick-Capture Text Message Handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

        # 4. ตั้งเวลางานเตือนประจำวันและงานดึงข่าว (Bangkok Time)
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

            # Hourly News Ingestion & Translation (ทุก 1 ชั่วโมง)
            job_queue.run_repeating(scheduled_hourly_news_sync, interval=3600, first=10, name="hourly_news_sync")
            self.stdout.write(self.style.SUCCESS("[OK] Hourly News Sync & Translation Scheduler registered"))
        else:
            self.stdout.write(self.style.WARNING("JobQueue is not enabled; install python-telegram-bot[job-queue]"))

        self.stdout.write(self.style.SUCCESS("Bot is now listening for messages... Press Ctrl+C to stop."))
        # เริ่มการ Polling ข้อความ
        app.run_polling(drop_pending_updates=True)
