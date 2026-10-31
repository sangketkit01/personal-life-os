"""Exchange sessions from an offline calendar, including holidays and early closes."""
from functools import lru_cache
from datetime import timedelta, time
from zoneinfo import ZoneInfo
import pandas as pd
import exchange_calendars as xc
from django.utils import timezone

NAMES = {'US': 'XNYS', 'SET': 'XBKK'}
ZONES = {'US': 'America/New_York', 'SET': 'Asia/Bangkok'}
# SET's calendar supplies dates/open/close but currently has no intraday break.
# SET extended afternoon trading on 2024-03-25 (official trading-hours schedule).
SET_LUNCH_START = time(12, 30)


def set_afternoon_times(day):
    return (time(13, 30), time(14)) if str(day) >= '2024-03-25' else (time(14), time(14, 30))


@lru_cache(maxsize=2)
def calendar(market):
    return xc.get_calendar(NAMES[market])


def session(market, day, direction='none'):
    if market not in NAMES:
        return None
    try:
        cal = calendar(market)
        label = cal.date_to_session(str(day), direction=direction)
        previous = cal.previous_session(label)
        return {
            'date': label.date(),
            'open': cal.session_open(label).to_pydatetime(),
            'close': cal.session_close(label).to_pydatetime(),
            'previous_close': cal.session_close(previous).to_pydatetime(),
        }
    except (ValueError, KeyError):
        return None


def latest_completed_session(market, now=None):
    now = now or timezone.now()
    day = now.astimezone(ZoneInfo(ZONES[market])).date()
    result = session(market, day, 'previous')
    if result and result['close'] + timedelta(minutes=15) > now:
        result = session(market, result['date'] - timedelta(days=1), 'previous')
    return result


def regular_session_open(market, now=None):
    if market not in NAMES:
        return market == 'CRYPTO'
    now = now or timezone.now()
    if market == 'SET':
        local = now.astimezone(ZoneInfo(ZONES['SET']))
        _, afternoon_open = set_afternoon_times(local.date())
        if SET_LUNCH_START <= local.time().replace(tzinfo=None) < afternoon_open:
            return False
    try:
        return bool(calendar(market).is_open_on_minute(pd.Timestamp(now).floor('min')))
    except ValueError:
        return False
