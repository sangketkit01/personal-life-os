import logging
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .news_service import ingest_news_for_ticker

logger = logging.getLogger(__name__)

_scheduler = None


def sync_hourly_portfolio_news() -> Dict[str, Any]:
    """
    งานตั้งเวลาประจำชั่วโมง (Hourly Cron):
    1. กวาดหาสัญลักษณ์หุ้น/สินทรัพย์ทั้งหมดที่ไม่ซ้ำกันจากผู้ใช้ทุกคนในระบบ
    2. ดึงข่าวสารล่าสุดจาก Yahoo Finance และ Google News
    3. ตรวจสอบกับ URL ในฐานข้อมูล:
       - ถ้าเป็นข่าวใหม่ -> แปลภาษาด้วย Gemini และบันทึกเข้าระบบ
       - ถ้าไม่มีข่าวใหม่หรือเคยมีแล้ว -> ข้ามไปอย่างราบรื่น (ไม่มีข้อผิดพลาด)
    """
    from .models import StockHolding

    try:
        distinct_tickers = list(
            StockHolding.objects.values_list('ticker', flat=True).distinct()
        )
    except Exception as e:
        logger.warning(f"[Hourly News Sync] Database not ready or failed to list tickers: {e}")
        return {'status': 'skipped', 'reason': str(e)}

    if not distinct_tickers:
        logger.info("[Hourly News Sync] No active stock holdings in system. Skipping.")
        return {'status': 'no_tickers', 'tickers_count': 0, 'new_articles': 0}

    logger.info(f"[Hourly News Sync] Starting hourly news sync for {len(distinct_tickers)} unique tickers...")
    total_new = 0

    for ticker in distinct_tickers:
        try:
            # ดึง 3 ข่าวล่าสุดต่อสำนักข่าว
            new_count = ingest_news_for_ticker(ticker, limit_per_source=3)
            total_new += new_count
        except Exception as e:
            logger.warning(f"[Hourly News Sync] Error syncing ticker {ticker}: {e}")

    logger.info(
        f"[Hourly News Sync] Completed. Ingested & translated {total_new} new articles across {len(distinct_tickers)} tickers."
    )
    return {
        'status': 'completed',
        'tickers_count': len(distinct_tickers),
        'new_articles': total_new
    }


def start_portfolio_scheduler():
    """เริ่มต้น Background Scheduler สำหรับงาน Recurring Jobs ประจำแอป Portfolio"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    try:
        _scheduler = BackgroundScheduler(timezone="Asia/Bangkok")
        # ตั้งเวลาให้ดึงข่าวใหม่ทุกชั่วโมง (interval hours=1)
        _scheduler.add_job(
            sync_hourly_portfolio_news,
            trigger=IntervalTrigger(hours=1),
            id='hourly_portfolio_news_sync',
            name='Hourly Portfolio Market News Ingestion',
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        _scheduler.start()
        logger.info("[Portfolio Scheduler] APScheduler background engine started successfully (Hourly News Sync Active).")
        return _scheduler
    except Exception as e:
        logger.error(f"[Portfolio Scheduler] Failed to start APScheduler: {e}")
        return None


def stop_portfolio_scheduler():
    """หยุด Background Scheduler อย่างปลอดภัย"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
