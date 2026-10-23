import zoneinfo
from datetime import datetime, time as dtime, timedelta
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .models import StockPriceSnapshot


def get_market_category(ticker: str, asset_type: Optional[str] = None) -> str:
    """Determine market category for an asset: CRYPTO, SET, US, or FOREX."""
    if not ticker:
        return 'US'
    t = ticker.strip().upper()
    if asset_type == 'CRYPTO' or t.endswith('-USD') or t in ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'XRP', 'ADA']:
        return 'CRYPTO'
    if t.endswith('=X'):
        return 'FOREX'
    if t.endswith('.BK') or asset_type == 'FUND':
        return 'SET'
    return 'US'


def get_set_market_status(now_ict: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Check market hours for Stock Exchange of Thailand (SET / MAI).
    - Trading days: Monday - Friday (Weekends closed)
    - Active trading window: 09:30 - 17:00 ICT (includes morning/afternoon pre-open and evening run-off).
    """
    tz_ict = zoneinfo.ZoneInfo('Asia/Bangkok')
    if not now_ict:
        now_ict = datetime.now(tz_ict)
    elif now_ict.tzinfo is None:
        now_ict = now_ict.replace(tzinfo=tz_ict)

    weekday = now_ict.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    current_time = now_ict.time()

    # Weekend check
    if weekday >= 5:
        days_until_mon = (7 - weekday) % 7
        next_open_dt = (now_ict + timedelta(days=days_until_mon)).replace(
            hour=9, minute=30, second=0, microsecond=0
        )
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': False,
            'session': 'Weekend Closed',
            'opens_at': 'Mon 09:30 ICT',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }

    # Weekdays: Market session intervals
    t_pre_morning = dtime(9, 30)
    t_open_morning = dtime(10, 0)
    t_close_morning = dtime(12, 30)
    t_pre_afternoon = dtime(14, 0)
    t_open_afternoon = dtime(14, 30)
    t_close_day = dtime(17, 0)

    if current_time < t_pre_morning:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': False,
            'session': 'Pre-Market Closed',
            'opens_at': 'Today 09:30 ICT',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    elif t_pre_morning <= current_time < t_open_morning:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': True,
            'session': 'Morning Pre-Open',
            'opens_at': 'Now Active (Pre-Open)',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    elif t_open_morning <= current_time < t_close_morning:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': True,
            'session': 'Morning Trading',
            'opens_at': 'Now Active (Trading)',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    elif t_close_morning <= current_time < t_pre_afternoon:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': False,
            'session': 'Lunch Break',
            'opens_at': 'Today 14:00 ICT (Pre-Open)',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    elif t_pre_afternoon <= current_time < t_open_afternoon:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': True,
            'session': 'Afternoon Pre-Open',
            'opens_at': 'Now Active (Pre-Open)',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    elif t_open_afternoon <= current_time < t_close_day:
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': True,
            'session': 'Afternoon Trading',
            'opens_at': 'Now Active (Trading)',
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }
    else:
        # After 17:00 ICT
        next_day = 'Tomorrow 09:30 ICT' if weekday < 4 else 'Mon 09:30 ICT'
        return {
            'market': 'SET',
            'name': 'Stock Exchange of Thailand',
            'is_open': False,
            'session': 'Market Closed',
            'opens_at': next_day,
            'current_time_local': now_ict.strftime('%H:%M ICT'),
            'hours_description': 'Mon-Fri 09:30 - 17:00 ICT'
        }


def get_us_market_status(now_et: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Check market hours for US equity markets (NYSE / NASDAQ).
    - Trading days: Monday - Friday (Weekends closed)
    - Pre-Market: 04:00 - 09:30 ET
    - Regular Trading: 09:30 - 16:00 ET
    - After-Hours: 16:00 - 20:00 ET
    - Total active hours: 04:00 - 20:00 ET (approx 15:00 - 07:00 ICT next day).
    """
    tz_et = zoneinfo.ZoneInfo('America/New_York')
    if not now_et:
        now_et = datetime.now(tz_et)
    elif now_et.tzinfo is None:
        now_et = now_et.replace(tzinfo=tz_et)

    weekday = now_et.weekday()
    current_time = now_et.time()

    if weekday >= 5:
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': False,
            'session': 'Weekend Closed',
            'opens_at': 'Mon 04:00 ET (15:00 ICT)',
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'Mon-Fri 04:00 - 20:00 ET (Pre/Regular/After)'
        }

    t_pre = dtime(4, 0)
    t_open = dtime(9, 30)
    t_close = dtime(16, 0)
    t_after = dtime(20, 0)

    if current_time < t_pre:
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': False,
            'session': 'Pre-Market Closed',
            'opens_at': 'Today 04:00 ET (15:00 ICT)',
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'Mon-Fri 04:00 - 20:00 ET'
        }
    elif t_pre <= current_time < t_open:
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': True,
            'session': 'Pre-Market',
            'opens_at': 'Now Active (Pre-Market)',
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'Regular opens 09:30 ET'
        }
    elif t_open <= current_time < t_close:
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': True,
            'session': 'Regular Trading',
            'opens_at': 'Now Active (Regular Trading)',
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'Closes 16:00 ET'
        }
    elif t_close <= current_time < t_after:
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': True,
            'session': 'After-Hours',
            'opens_at': 'Now Active (After-Hours)',
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'After-hours until 20:00 ET'
        }
    else:
        next_day = 'Tomorrow 04:00 ET' if weekday < 4 else 'Mon 04:00 ET'
        return {
            'market': 'US',
            'name': 'US Markets (NYSE/NASDAQ)',
            'is_open': False,
            'session': 'Market Closed',
            'opens_at': next_day,
            'current_time_local': now_et.strftime('%H:%M ET'),
            'hours_description': 'Mon-Fri 04:00 - 20:00 ET'
        }


def get_crypto_market_status() -> Dict[str, Any]:
    """Crypto markets operate 24/7 continuously."""
    return {
        'market': 'CRYPTO',
        'name': 'Crypto Spot Market',
        'is_open': True,
        'session': '24/7 Live',
        'opens_at': 'Always Active',
        'current_time_local': 'Continuous',
        'hours_description': '24/7/365 Non-stop'
    }


def get_all_market_statuses() -> Dict[str, Any]:
    """Retrieve status for all key markets (SET, US, CRYPTO)."""
    set_status = get_set_market_status()
    us_status = get_us_market_status()
    crypto_status = get_crypto_market_status()

    is_any_open = set_status['is_open'] or us_status['is_open'] or crypto_status['is_open']

    return {
        'is_any_market_open': is_any_open,
        'markets': {
            'SET': set_status,
            'US': us_status,
            'CRYPTO': crypto_status
        }
    }


def is_market_open_for_ticker(ticker: str, asset_type: Optional[str] = None) -> bool:
    """Check whether the market for this ticker is currently open."""
    m = get_market_category(ticker, asset_type)
    if m == 'CRYPTO':
        return True
    elif m == 'SET':
        return get_set_market_status()['is_open']
    elif m == 'US':
        return get_us_market_status()['is_open']
    elif m == 'FOREX':
        now_utc = datetime.now(zoneinfo.ZoneInfo('UTC'))
        return now_utc.weekday() < 5
    return False


def should_refresh_ticker(ticker: str, asset_type: Optional[str] = None, force: bool = False) -> bool:
    """
    Smart evaluation of whether an asset price should be refreshed via market API.
    1. If force=True: Always fetch.
    2. If the asset's market is open: Fetch according to schedule.
    3. If the market is closed:
       - If no snapshot exists in DB: Fetch once to establish baseline price.
       - If snapshot exists and was fetched recently: Skip to conserve API quota and reduce load.
    """
    if force:
        return True

    # 1. If market is open, allow routine refresh
    if is_market_open_for_ticker(ticker, asset_type):
        return True

    # 2. If market is closed, inspect snapshot freshness
    snap = StockPriceSnapshot.objects.filter(ticker=ticker).first()
    if not snap:
        # No price data exists yet, fetch once
        return True

    # Apply market-specific TTL when closed
    now = timezone.now()
    m = get_market_category(ticker, asset_type)
    if m == 'US' and now.weekday() < 5:
        # On weekdays for US equities, post-market & overnight activity: cache for 15 minutes
        if (now - snap.fetched_at) < timedelta(minutes=15):
            return False
    else:
        if (now - snap.fetched_at) < timedelta(hours=4):
            return False

    return True
