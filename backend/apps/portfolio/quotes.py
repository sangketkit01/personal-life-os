"""Quote freshness and one shared background price refresh for every tracked asset."""
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.db.models import Q
from .exchange_sessions import latest_completed_session, regular_session_open


def quote_metadata(snapshot, now=None):
    from .market_hours import get_market_category
    now = now or timezone.now()
    if snapshot is None:
        return {'state': 'MISSING', 'as_of': None, 'fetched_at': None, 'error': 'No market quote available'}
    market = get_market_category(snapshot.ticker)
    stamp = snapshot.regular_quote_at or snapshot.quote_at
    state = 'UNKNOWN'
    if stamp and stamp <= now + timedelta(minutes=2):
        if market == 'FOREX' and now.weekday() >= 5:
            state = 'CLOSED' if now - stamp <= timedelta(days=3) else 'STALE'
        elif market in ('US', 'SET') and not regular_session_open(market, now):
            closed = latest_completed_session(market, now + timedelta(minutes=15))
            end = closed['close'] if closed else None
            if market == 'SET':
                from .exchange_sessions import SET_LUNCH_START, set_afternoon_times, session
                local = now.astimezone(ZoneInfo('Asia/Bangkok'))
                _, afternoon_open = set_afternoon_times(local.date())
                if SET_LUNCH_START <= local.time().replace(tzinfo=None) < afternoon_open and session('SET', local.date()):
                    end = datetime.combine(local.date(), SET_LUNCH_START, local.tzinfo)
            state = 'CLOSED' if end and end - timedelta(minutes=15) <= stamp <= end + timedelta(minutes=15) else 'STALE'
        else:
            state = 'CURRENT' if now - stamp <= timedelta(minutes=5) else 'STALE'
    if snapshot.last_error:
        state = 'STALE'
    return {'state': state, 'as_of': stamp.isoformat() if stamp else None,
            'fetched_at': snapshot.fetched_at.isoformat(),
            'attempted_at': snapshot.last_attempt_at.isoformat() if snapshot.last_attempt_at else None,
            'error': snapshot.last_error}


def tracked_tickers(user=None, include_recent=True):
    from .identity import active_tickers
    from .models import StockWatchlist, StockTransaction, PriceAlert
    ticks = active_tickers(user)
    watch = StockWatchlist.objects.all()
    rules = PriceAlert.objects.filter(is_active=True)
    if user:
        watch, rules = watch.filter(user=user), rules.filter(user=user)
    ticks.update(watch.values_list('ticker', flat=True))
    ticks.update(rules.values_list('ticker', flat=True))
    if include_recent:
        txs = StockTransaction.objects.filter(executed_at__gte=timezone.now() - timedelta(days=7))
        if user:
            txs = txs.filter(user=user)
        ticks.update(txs.values_list('holding__ticker', flat=True))
    if ticks:
        ticks.add('USDTHB=X')
    return sorted(ticks)


def sync_result(tickers, started):
    from .models import StockPriceSnapshot
    rows = {s.ticker: s for s in StockPriceSnapshot.objects.filter(ticker__in=tickers)}
    result = {'refreshed': [], 'cached': [], 'failed': [], 'quotes': {}}
    for ticker in tickers:
        row = rows.get(ticker)
        if row is None or (row.last_error and row.last_attempt_at and row.last_attempt_at >= started):
            result['failed'].append(ticker)
        elif row.last_attempt_at and row.last_attempt_at >= started:
            result['refreshed'].append(ticker)
        else:
            result['cached'].append(ticker)
        result['quotes'][ticker] = quote_metadata(row)
    return result


def worker_health():
    from apps.bot.models import SchedulerLease
    row = SchedulerLease.objects.filter(key='portfolio-prices').first()
    stamp = row.last_started_at if row else None
    return {'healthy': bool(stamp and timezone.now() - stamp < timedelta(minutes=3)),
            'started_at': stamp.isoformat() if stamp else None,
            'finished_at': row.last_finished_at.isoformat() if row and row.last_finished_at else None}


def sync_tracked_prices():
    from apps.bot.leases import job_lease
    from .services import fetch_and_cache_market_prices
    with job_lease('portfolio-prices', seconds=600) as acquired:
        if not acquired:
            return {'skipped': 'already_running'}
        tickers = tracked_tickers()
        started = timezone.now()
        fetch_and_cache_market_prices(tickers)
        return sync_result(tickers, started)
