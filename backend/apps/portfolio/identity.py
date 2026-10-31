"""Conservative asset identity checks shared by ingestion, feeds and the bot."""
import re
import hashlib
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from django.db.models import Q, F
from django.utils import timezone
from .asset_catalog import MASTER_ASSET_CATALOG

# Verified company/brand names, independent of user-entered holding labels.
COMPANY_ALIASES = {
    'AMD': ('AMD',), 'GOOG': ('Google',), 'GOOGL': ('Google',),
    'META': ('Meta', 'Facebook', 'Instagram'), 'AMZN': ('Amazon',),
    'TSM': ('TSMC',), 'BRK.B': ('Berkshire Hathaway',),
    'DIS': ('Disney',), 'COIN': ('Coinbase',), 'PLTR': ('Palantir',),
}


def asset_identity(ticker):
    from .models import StockHolding, StockWatchlist, StockPriceSnapshot
    ticker = ticker.upper().strip()
    item = next((dict(a) for a in MASTER_ASSET_CATALOG if a['ticker'] == ticker), None)
    if item:
        return item
    holding = StockHolding.objects.filter(ticker=ticker).exclude(name='').first()
    holding = holding or StockWatchlist.objects.filter(ticker=ticker).exclude(name='').first()
    snap = StockPriceSnapshot.objects.filter(ticker=ticker).first()
    return {'ticker': ticker, 'name': snap.asset_name if snap and snap.asset_name else ticker,
            'currency': holding.currency if holding else (snap.currency if snap else None),
            'exchange': snap.exchange if snap and snap.exchange else ('SET' if ticker.endswith('.BK') else 'US')}


def canonical_url(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return ''
    if parts.scheme.lower() not in ('http', 'https') or not parts.netloc:
        return ''
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith('utm_') and k.lower() not in ('guccounter', 'gclid', 'fbclid')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), urlencode(sorted(query)), ''))[:1000]


def story_keys(article):
    get = article.get if isinstance(article, dict) else lambda k, default='': getattr(article, k, default)
    title = re.sub(r'[^\w\s]', ' ', get('title').lower())
    title = ' '.join(title.split())
    return {get('canonical_url') or canonical_url(get('url')), 'headline:' + hashlib.sha256(title.encode()).hexdigest()}


def news_query(ticker):
    identity = asset_identity(ticker)
    name = identity['name']
    return f'"{name}" {ticker} stock when:3d' if name != ticker else f'"{ticker}" stock when:3d'


def classify_news(ticker, title, content='', related_tickers=None):
    identity = asset_identity(ticker)
    text = f'{title} {content}'.lower()
    name = re.sub(r'\s+(inc\.?|corporation|corp\.?|limited|ltd\.?|public company limited|plc)\b.*$', '', identity['name'], flags=re.I).strip().lower()
    financial = bool(re.search(r'\b(stock|shares?|earnings|revenue|dividend|nyse|nasdaq|profit|payments?|investors?|quarter|buyback|credit card|debit card|analyst|crypto|tokens?)\b|หุ้น|กำไร|รายได้|ปันผล|ชำระเงิน', text))
    corporate = bool(re.search(r'\b(chip|business|acquisition|merger|ceo|cloud|technology|product|renewable)\b', text))
    # A provider symbol alone does not turn a clearly unrelated article into company news.
    names = [name] if name != ticker.lower() and len(name) > 2 else []
    names.extend(alias.lower() for alias in COMPANY_ALIASES.get(ticker.upper(), ()))
    named = any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text) for alias in names)
    symbol = bool(re.search(r'(?:\$|nyse\s*[:：]\s*|nasdaq\s*[:：]\s*)' + re.escape(ticker.lower()) + r'(?!\w)', text))
    provider_match = ticker.upper() in {str(t).upper() for t in (related_tickers or [])}
    if name == 'visa':
        travel_context = bool(re.search(r'\b(travel|touris\w*|immigration|embass\w*|consulat\w*|passport|visa application|visa fees?|work visa|student visa)\b|วีซ่า|สถานทูต|ตรวจคนเข้าเมือง', text))
        explicit_company = bool(re.search(r'\bvisa\s+(inc\b|earnings\b|shares\b|stock\b)|nyse\s*:\s*v\b', text))
        if travel_context and not explicit_company:
            return 'UNKNOWN', 'Travel-visa context without explicit Visa company evidence'
        company_context = bool(re.search(r'\bvisa\s+(inc|earnings|shares|stock|reports)\b|\b(payments?|credit cards?|debit cards?|card network)\b|nyse\s*:\s*v\b', text))
        if not company_context and not provider_match:
            return 'UNKNOWN', 'Visa needs payment-company evidence, not a travel-visa keyword'
    if named and (financial or (corporate and name not in ('visa',))):
        return 'ACCEPTED', 'Company name and financial context matched'
    if symbol and financial and (len(ticker) > 2 or named):
        return 'ACCEPTED', 'Qualified market symbol matched'
    if provider_match and named:
        return 'ACCEPTED', 'Provider association and company identity matched'
    return 'UNKNOWN', 'Insufficient evidence of asset relevance'


def revalidate_stored_news(limit=300):
    from .models import StockNewsArticle
    now = timezone.now()
    rows = StockNewsArticle.objects.filter(
        Q(relevance='PENDING') | Q(relevance='UNKNOWN', relevance_checked_at__isnull=True)
        | Q(relevance='UNKNOWN', relevance_checked_at__lte=now-timedelta(hours=1))
    ).order_by(F('relevance_checked_at').asc(nulls_first=True), '-published_at')[:limit]
    count = 0
    for article in rows:
        article.relevance, article.relevance_reason = classify_news(article.ticker, article.title, article.summary + ' ' + article.content)
        article.canonical_url = canonical_url(article.url)
        article.relevance_checked_at = now
        if not article.canonical_url:
            article.relevance, article.relevance_reason = 'REJECTED', 'Invalid article URL'
        article.save(update_fields=['relevance', 'relevance_reason', 'canonical_url', 'relevance_checked_at'])
        count += 1
    return count


def active_tickers(user=None):
    from .models import StockHolding
    qs = StockHolding.objects.all().prefetch_related('transactions')
    if user is not None:
        qs = qs.filter(user=user)
    return {h.ticker for h in qs if h.calculate_position()['shares'] > 0}
