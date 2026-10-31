"""One-shot price rules and market-close PnL with explicit trade cash flows."""
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from apps.bot.models import NotificationDelivery, NotificationPreference
from apps.bot.delivery import preferences, quiet_until
from .models import PriceAlert, MarketCloseReport, StockPriceSnapshot, StockHolding
from .exchange_sessions import latest_completed_session, regular_session_open
from .market_hours import get_market_category
from .quotes import quote_metadata


def evaluate_price_alerts(now=None):
    now = now or timezone.now()
    for rule_id in PriceAlert.objects.filter(is_active=True, user__is_active=True).values_list('pk', flat=True):
        with transaction.atomic():
            rule = PriceAlert.objects.select_for_update().select_related('user').get(pk=rule_id)
            if not rule.is_active or not rule.user.telegram_chat_id:
                continue
            pref = preferences(rule.user)
            snap = StockPriceSnapshot.objects.filter(ticker=rule.ticker).first()
            if not pref.price_alerts or not snap or snap.currency != rule.currency:
                continue
            if not regular_session_open(get_market_category(rule.ticker), now) or quote_metadata(snap, now)['state'] != 'CURRENT':
                continue
            if now - snap.fetched_at > timedelta(minutes=5):
                continue
            reached = snap.price >= rule.target_price if rule.condition == 'GTE' else snap.price <= rule.target_price
            if not reached:
                continue
            stamp = snap.regular_quote_at or snap.quote_at
            payload = {'text': f'🔔 {rule.ticker} · {rule.currency}\nราคา {format(snap.price.normalize(), "f")} {"≥" if rule.condition == "GTE" else "≤"} {format(rule.target_price.normalize(), "f")}\nAs of {stamp.isoformat()}\nแจ้งแล้ว · เงื่อนไขนี้พักการทำงาน เปิดใช้งานใหม่ได้ในเว็บ'}
            if settings.APP_PUBLIC_URL:
                payload['reply_markup'] = {'inline_keyboard': [[{'text': 'Open asset', 'url': f'{settings.APP_PUBLIC_URL}/portfolio/asset/{rule.ticker}'}]]}
            NotificationDelivery.objects.get_or_create(user=rule.user, event_key=f'price:{rule.id}:{rule.revision}', defaults={
                'category': 'price_alerts', 'payload': payload,
                'reference': {'price_alert_id': str(rule.id), 'revision': str(rule.revision)},
                'available_at': quiet_until(pref, now)})
            rule.is_active, rule.triggered_at = False, now
            rule.save(update_fields=['is_active', 'triggered_at'])


def build_close_report(user, market, closed, now=None):
    """PnL = end value - start value - purchases + sales + dividends, in native currency."""
    now = now or timezone.now()
    currency = 'THB' if market == 'SET' else 'USD'
    holdings = StockHolding.objects.filter(user=user).prefetch_related('transactions')
    snapshots = {s.ticker: s for s in StockPriceSnapshot.objects.all()}
    entries, missing = [], set()
    start_total = end_total = purchases = sales = dividends = Decimal('0')
    baseline_ok = True
    for holding in holdings:
        if get_market_category(holding.ticker, holding.asset_type) != market:
            continue
        begin = end = bought = sold = div = Decimal('0')
        period_txs = False
        for tx in sorted(holding.transactions.all(), key=lambda t: (t.executed_at, str(t.id))):
            if tx.executed_at > closed['close']:
                continue
            signed = tx.shares if tx.transaction_type == 'BUY' else -tx.shares if tx.transaction_type == 'SELL' else Decimal('0')
            end += signed
            if tx.executed_at <= closed['previous_close']:
                begin += signed
            else:
                period_txs = True
                if tx.transaction_type == 'BUY':
                    bought += tx.shares * tx.price_per_share + tx.fee
                elif tx.transaction_type == 'SELL':
                    sold += tx.shares * tx.price_per_share - tx.fee
                elif tx.transaction_type == 'DIVIDEND':
                    div += tx.shares * tx.price_per_share - tx.fee
        if not begin and not end and not period_txs:
            continue
        snap = snapshots.get(holding.ticker)
        stamp = snap.regular_quote_at if snap else None
        # A quote from a different session, an old intraday quote, or another currency is not a closing price.
        if (not snap or not stamp or snap.currency != currency or holding.currency != currency
                or not closed['close'] - timedelta(minutes=15) <= stamp <= closed['close'] + timedelta(minutes=15)):
            missing.add(holding.ticker)
            baseline_ok = False
            continue
        close_price = snap.regular_price or snap.price
        if begin and not snap.previous_close:
            baseline_ok = False
        start_value = begin * (snap.previous_close or Decimal('0'))
        end_value = end * close_price
        pnl = end_value - start_value - bought + sold + div
        entries.append({'ticker': holding.ticker, 'shares': str(end), 'close': str(close_price),
                        'pnl': str(pnl) if not begin or snap.previous_close else None})
        start_total += start_value
        end_total += end_value
        purchases += bought
        sales += sold
        dividends += div
    if not entries and not missing:
        return None
    if missing and now < closed['close'] + timedelta(hours=2):
        return None
    return {'currency': currency, 'market_value': str(end_total), 'start_value': str(start_total),
            'daily_pnl': str(end_total - start_total - purchases + sales + dividends) if baseline_ok else None,
            'purchases': str(purchases), 'sales': str(sales), 'dividends': str(dividends),
            'positions': entries, 'missing': sorted(missing), 'close_at': closed['close'].isoformat()}


def prepare_close_reports(now=None):
    now = now or timezone.now()
    for pref in NotificationPreference.objects.filter(market_close=True, user__is_active=True).select_related('user'):
        if not pref.user.telegram_chat_id:
            continue
        for market in ('SET', 'US'):
            closed = latest_completed_session(market, now)
            if not closed or now - closed['close'] > timedelta(hours=24):
                continue
            report = MarketCloseReport.objects.filter(user=pref.user, market=market, session_date=closed['date']).first()
            if not report:
                data = build_close_report(pref.user, market, closed, now)
                if not data:
                    continue
                report, _ = MarketCloseReport.objects.get_or_create(user=pref.user, market=market, session_date=closed['date'], defaults={'data': data})
            data = report.data
            pnl = f"{Decimal(data['daily_pnl']):+,.2f}" if data['daily_pnl'] is not None else 'Unavailable · closing quote or baseline missing'
            lines = [f"📊 {market} close · {closed['date']}", f"{'Known value' if data['missing'] else 'Market value'}: {data['currency']} {Decimal(data['market_value']):,.2f}", f"Daily PnL: {pnl}", f"Close: {data['close_at']}"]
            movers = sorted((p for p in data['positions'] if p['pnl'] is not None), key=lambda p: abs(Decimal(p['pnl'])), reverse=True)[:3]
            lines += [f"{p['ticker']}: {data['currency']} {Decimal(p['pnl']):+,.2f}" for p in movers]
            if data['missing']:
                lines.append('Missing quotes: ' + ', '.join(data['missing']))
            reference = {}
            if pref.portfolio_news:
                from .models import StockNewsArticle
                from .identity import story_keys
                seen = set()
                for ref in NotificationDelivery.objects.filter(user=pref.user, status__in=['SENT', 'PENDING', 'SENDING'], created_at__gte=now-timedelta(days=7)).values_list('reference', flat=True):
                    seen.update(ref.get('news_urls', []))
                picked = []
                for article in StockNewsArticle.objects.filter(relevance='ACCEPTED', ticker__in={p['ticker'] for p in data['positions']}, published_at__gte=now-timedelta(hours=48)).order_by('-published_at')[:20]:
                    keys = story_keys(article)
                    if not keys.intersection(seen):
                        headline = article.title_th or article.title if pref.user.preferred_language == 'th' else article.title or article.title_th
                        picked.append(f'{article.ticker}: {headline[:180]}')
                        seen.update(keys)
                        reference.setdefault('news_urls', []).extend(keys)
                    if len(picked) == 2:
                        break
                if picked:
                    lines.append('News:')
                    lines.extend(picked)
            payload = {'text': '\n'.join(lines)}
            if settings.APP_PUBLIC_URL:
                payload['reply_markup'] = {'inline_keyboard': [[{'text': 'Open portfolio', 'url': settings.APP_PUBLIC_URL + '/portfolio'}]]}
            NotificationDelivery.objects.get_or_create(user=pref.user, event_key=f'close:{market}:{closed["date"]}', defaults={
                'category': 'market_close', 'payload': payload, 'reference': reference, 'available_at': quiet_until(pref, now)})
