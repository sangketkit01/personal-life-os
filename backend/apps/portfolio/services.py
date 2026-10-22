import re
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .models import (
    StockHolding,
    StockTransaction,
    StockPriceSnapshot,
    TransactionType,
    AssetType,
    InvestmentPortfolio
)
from .asset_catalog import search_market_assets, verify_ticker_exists


# รายชื่อ Ticker หุ้นไทย SET ยอดนิยม (เพื่อเติม .BK ให้อัตโนมัติเมื่อพิมพ์แบบย่อ)
THAI_SET_SYMBOLS = {
    'PTT', 'DELTA', 'AOT', 'CPALL', 'ADVANC', 'GULF', 'SCB', 'KBANK', 'BBL',
    'KTB', 'BDMS', 'BH', 'SCC', 'CPN', 'CRC', 'MINT', 'TRUE', 'INTUCH',
    'HMPRO', 'WHA', 'BEM', 'BTS', 'BANPU', 'IVL', 'KTC', 'MTC', 'SAWAD',
    'OSP', 'CBG', 'BGRIM', 'GPSC', 'TOP', 'IRPC', 'PTTEP', 'TU', 'LH',
    'OR', 'CENTEL', 'COM7', 'EA', 'HANA', 'KCE', 'MEGA', 'RATCH', 'STA',
    'TCAP', 'TIDLOR', 'TISCO', 'VGI', 'BJC', 'GLOBAL', 'JMT', 'SIRI',
    'AMATA', 'AP', 'BCP', 'BLA', 'CHG', 'CK', 'DOHOME', 'FORTH', 'JMART',
    'MAJOR', 'PLANB', 'PRM', 'PSL', 'PTG', 'QH', 'RCL', 'SABUY', 'SAPPE',
    'SINGER', 'SPALI', 'SPRC', 'STEC', 'TASCO', 'THANI', 'TIPH', 'TKN',
    'TLI', 'TTB', 'VNG'
}

# รายชื่อ Crypto ยอดนิยม (เพื่อเติม -USD ให้อัตโนมัติ)
CRYPTO_SYMBOLS = {
    'BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'XRP', 'ADA', 'AVAX', 'SUI',
    'LINK', 'PEPE', 'SHIB', 'NEAR', 'DOT'
}


def normalize_ticker(raw_ticker: str, currency: Optional[str] = None) -> str:
    """
    จัดรูปแบบ Ticker ให้เป็นมาตรฐาน:
    1. ถ้ามีจุด (.) หรือขีด (-) อยู่แล้ว (เช่น PTT.BK, BTC-USD, BRK.B) -> คงเดิม
    2. ถ้าเป็น Crypto ยอดนิยม (เช่น BTC, ETH) -> เติม -USD
    3. ถ้าสกุลเงินระบุชัดเจนว่าเป็น USD -> เป็นหุ้นต่างประเทศ ห้ามเติม .BK
    4. ถ้าเป็นหุ้นไทยใน SET ยอดนิยม (เช่น PTT, DELTA, AOT, SCB) -> เติม .BK
    5. อื่นๆ ให้คงเดิม (เช่น GOOG, GOOGL, PLTR, BABA, DIS, AAPL) ไม่เติม .BK มั่วซั่ว
    """
    ticker = raw_ticker.strip().upper()
    if not ticker:
        return ""

    if '.' in ticker or '-' in ticker:
        return ticker

    if ticker in CRYPTO_SYMBOLS:
        return f"{ticker}-USD"

    # ถ้ากำหนดสกุลเงินเป็น USD หรือสินทรัพย์สกุลเงินดอลลาร์ -> ห้ามเติม .BK เด็ดขาด
    if currency and currency.upper() == 'USD':
        return ticker

    # ถ้าเป็นหุ้นไทยใน SET List -> เติม .BK
    if ticker in THAI_SET_SYMBOLS:
        return f"{ticker}.BK"

    return ticker


def fetch_and_cache_market_prices(
    tickers: List[str],
    force: bool = False,
    respect_market_hours: bool = True
) -> Dict[str, Decimal]:
    """
    ดึงราคาตลาดปัจจุบันของหุ้น/คริปโต และเก็บ snapshot ลงฐานข้อมูล:
    - เคารพเวลาเปิด-ปิดตลาด (Market Hours): ถ้าตลาดปิดและมีราคา Snapshot ภายใน 4 ชั่วโมง จะข้ามการยิงซ้ำ
    - ปรับ Cache TTL เป็น 1 นาทีสำหรับการซิงค์ Real-Time 1 นาที
    - รองรับทศนิยมสูงสุด 8 ตำแหน่งสำหรับเหรียญ Crypto และ Fractional Shares
    - Fallback คืนค่าจาก Snapshot ในฐานข้อมูลทันทีเมื่อ API ภายนอกช้าหรือล้มเหลว
    """
    if not tickers:
        return {}

    from .market_hours import should_refresh_ticker

    prices: Dict[str, Decimal] = {}
    tickers_to_fetch = list(set([normalize_ticker(t) for t in tickers if t]))
    now = timezone.now()
    cache_ttl = timedelta(minutes=1)

    # 1. ตรวจสอบ Snapshot ในฐานข้อมูลก่อน
    cached_snapshots = {
        s.ticker: s for s in StockPriceSnapshot.objects.filter(ticker__in=tickers_to_fetch)
    }

    missing_or_stale = []
    for t in tickers_to_fetch:
        snap = cached_snapshots.get(t)

        # ถ้าให้เคารพเวลาเปิด-ปิดตลาด และไม่ได้บังคับ (force=False)
        # ตรวจสอบว่าตลาดของหุ้นตัวนี้เปิดอยู่ หรือจำเป็นต้องดึงราคาหรือไม่
        if respect_market_hours and not force and not should_refresh_ticker(t, force=False):
            if snap:
                prices[t] = snap.price
            continue

        if snap and not force and (now - snap.fetched_at) < cache_ttl:
            prices[t] = snap.price
        else:
            missing_or_stale.append(t)

    # 2. ถ้ามีตัวที่ต้องดึงสด
    if missing_or_stale:
        try:
            import yfinance as yf
            for t in missing_or_stale:
                try:
                    stock = yf.Ticker(t)
                    fast_info = getattr(stock, 'fast_info', None)
                    price_val = None
                    regular_price_val = None
                    change_pct_val = Decimal('0.0000')
                    change_amount_val = Decimal('0.0000')
                    previous_close_val = None
                    session_val = 'REGULAR'

                    # ดึงข้อมูลจาก stock.info เพื่อรองรับ Pre-market และ Post-market ของหุ้นสหรัฐฯ
                    info = {}
                    try:
                        info = stock.info or {}
                    except Exception:
                        pass

                    # 1. Previous close
                    raw_prev_close = info.get('regularMarketPreviousClose') or (fast_info.get('previousClose') if fast_info else None)
                    if raw_prev_close is not None:
                        previous_close_val = Decimal(str(round(raw_prev_close, 8)))

                    # 2. Regular market price & change (ราคาหลักในเวลาทำการปกติ - ไม่ถูกทับโดย Pre/Post)
                    raw_reg_price = info.get('regularMarketPrice') or (fast_info.get('regularMarketPrice') if fast_info else None) or (fast_info.get('lastPrice') if fast_info else None)
                    if raw_reg_price is not None:
                        regular_price_val = Decimal(str(round(raw_reg_price, 8)))
                        price_val = regular_price_val

                    raw_reg_change = info.get('regularMarketChange') or (fast_info.get('regularMarketChange') if fast_info else None)
                    if raw_reg_change is not None:
                        change_amount_val = Decimal(str(round(raw_reg_change, 8)))
                    elif price_val and previous_close_val:
                        change_amount_val = price_val - previous_close_val

                    raw_reg_change_pct = info.get('regularMarketChangePercent') or (fast_info.get('regularMarketChangePercent') if fast_info else None)
                    if raw_reg_change_pct is not None:
                        change_pct_val = Decimal(str(round(raw_reg_change_pct, 4)))
                    elif previous_close_val and previous_close_val > Decimal('0') and price_val:
                        change_pct_val = Decimal(str(round(((price_val - previous_close_val) / previous_close_val) * 100, 4)))

                    # 3. ข้อมูลแยกสำหรับ Pre-Market และ Post-Market / Night Market (Extended Hours - เหมือน Dime / Webull)
                    market_state = str(info.get('marketState', '')).upper()
                    raw_post_price = info.get('postMarketPrice')
                    raw_pre_price = info.get('preMarketPrice')

                    extended_price_val = None
                    extended_change_val = None
                    extended_change_pct_val = None
                    session_val = 'REGULAR'

                    # ถ้าอยู่ในช่วง PRE-market และมีราคา preMarketPrice
                    if (market_state == 'PRE' or 'PRE' in market_state) and raw_pre_price is not None:
                        session_val = 'PRE'
                        extended_price_val = Decimal(str(round(raw_pre_price, 8)))
                        raw_pre_change_pct = info.get('preMarketChangePercent')
                        if raw_pre_change_pct is not None:
                            extended_change_pct_val = Decimal(str(round(raw_pre_change_pct, 4)))
                        elif previous_close_val and previous_close_val > Decimal('0'):
                            extended_change_pct_val = Decimal(str(round(((extended_price_val - previous_close_val) / previous_close_val) * 100, 4)))

                        raw_pre_change = info.get('preMarketChange')
                        if raw_pre_change is not None:
                            extended_change_val = Decimal(str(round(raw_pre_change, 8)))
                        elif previous_close_val:
                            extended_change_val = extended_price_val - previous_close_val

                    # ถ้าอยู่ในช่วง POST-market หรือนอกเวลาทำการ และมีราคา postMarketPrice
                    elif raw_post_price is not None and (market_state in ('POST', 'POSTPOST', 'CLOSED') or not market_state):
                        session_val = 'POST'
                        extended_price_val = Decimal(str(round(raw_post_price, 8)))
                        raw_post_change_pct = info.get('postMarketChangePercent')
                        if raw_post_change_pct is not None:
                            extended_change_pct_val = Decimal(str(round(raw_post_change_pct, 4)))
                        elif previous_close_val and previous_close_val > Decimal('0'):
                            extended_change_pct_val = Decimal(str(round(((extended_price_val - previous_close_val) / previous_close_val) * 100, 4)))

                        raw_post_change = info.get('postMarketChange')
                        if raw_post_change is not None:
                            extended_change_val = Decimal(str(round(raw_post_change, 8)))
                        elif previous_close_val:
                            extended_change_val = extended_price_val - previous_close_val

                    if price_val is not None and price_val > Decimal('0'):
                        StockPriceSnapshot.objects.update_or_create(
                            ticker=t,
                            defaults={
                                'price': price_val,
                                'regular_price': price_val,
                                'extended_price': extended_price_val,
                                'extended_change': extended_change_val,
                                'extended_change_pct': extended_change_pct_val,
                                'market_session': session_val,
                                'change_amount': change_amount_val,
                                'change_pct': change_pct_val,
                                'previous_close': previous_close_val,
                                'currency': 'THB' if t.endswith('.BK') else 'USD'
                            }
                        )
                        prices[t] = price_val
                    elif t in cached_snapshots:
                        prices[t] = cached_snapshots[t].price
                except Exception:
                    if t in cached_snapshots:
                        prices[t] = cached_snapshots[t].price
        except ImportError:
            pass

    # 3. Final Fallback: เติมตัวที่ยังตกหล่นด้วย cached snapshots
    for t in tickers_to_fetch:
        if t not in prices and t in cached_snapshots:
            prices[t] = cached_snapshots[t].price

    return prices


def calculate_detailed_position(
    holding: StockHolding,
    current_price: Decimal = None,
    usd_to_thb_rate: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    คำนวณต้นทุนเฉลี่ย (Weighted Average Cost), มูลค่าตลาด, กำไร/ขาดทุน Realized และ Unrealized
    พร้อมทั้งแปลงค่าเป็น Dual-Currency (THB และ USD) อย่างแม่นยำ
    """
    if hasattr(holding, '_prefetched_objects_cache') and 'transactions' in holding._prefetched_objects_cache:
        transactions = sorted(holding.transactions.all(), key=lambda x: x.executed_at)
    else:
        transactions = holding.transactions.all().order_by('executed_at')

    total_shares = Decimal('0')
    total_cost_basis = Decimal('0')
    total_realized_pnl = Decimal('0')
    total_dividends = Decimal('0')

    for tx in transactions:
        if tx.transaction_type == TransactionType.BUY:
            # ต้นทุนรวม = (จำนวนหุ้น * ราคาต่อหุ้น) + ค่าคอม
            tx_cost = (tx.shares * tx.price_per_share) + tx.fee
            total_cost_basis += tx_cost
            total_shares += tx.shares

        elif tx.transaction_type == TransactionType.SELL:
            if total_shares > Decimal('0'):
                shares_to_sell = min(tx.shares, total_shares)
                # ราคาต้นทุนเฉลี่ยก่อนขาย
                avg_cost_before_sell = total_cost_basis / total_shares
                cost_of_shares_sold = avg_cost_before_sell * shares_to_sell

                # เงินที่ได้รับหลังหักค่าคอม = (จำนวนหุ้นที่ขายได้ * ราคาขาย) - ค่าคอม
                net_proceeds = (shares_to_sell * tx.price_per_share) - tx.fee

                # กำไร/ขาดทุนจริงจากไม้นี้
                realized_from_tx = net_proceeds - cost_of_shares_sold
                total_realized_pnl += realized_from_tx

                total_shares -= shares_to_sell
                total_cost_basis -= cost_of_shares_sold

                if total_shares <= Decimal('0'):
                    total_shares = Decimal('0')
                    total_cost_basis = Decimal('0')

        elif tx.transaction_type == TransactionType.DIVIDEND:
            # เงินปันผลรับ = (จำนวนหุ้น * ปันผลต่อหุ้น) - หัก ณ ที่จ่าย
            net_dividend = (tx.shares * tx.price_per_share) - tx.fee
            total_dividends += net_dividend

    avg_cost = (total_cost_basis / total_shares) if total_shares > Decimal('0') else Decimal('0')

    # ราคาตลาดล่าสุด และข้อมูล Market Session (Regular, Pre-market, Post-market)
    snapshot = StockPriceSnapshot.objects.filter(ticker=holding.ticker).first()
    if current_price is None:
        current_price = snapshot.price if snapshot else avg_cost
    elif not isinstance(current_price, Decimal):
        current_price = Decimal(str(current_price))

    market_session = getattr(snapshot, 'market_session', 'REGULAR') if snapshot else 'REGULAR'
    regular_price = getattr(snapshot, 'regular_price', current_price) if snapshot else current_price
    if regular_price is not None and not isinstance(regular_price, Decimal):
        regular_price = Decimal(str(regular_price))

    extended_price = getattr(snapshot, 'extended_price', None) if snapshot else None
    if extended_price is not None and not isinstance(extended_price, Decimal):
        extended_price = Decimal(str(extended_price))

    extended_change = getattr(snapshot, 'extended_change', None) if snapshot else None
    if extended_change is not None and not isinstance(extended_change, Decimal):
        extended_change = Decimal(str(extended_change))

    extended_change_pct = getattr(snapshot, 'extended_change_pct', None) if snapshot else None
    if extended_change_pct is not None and not isinstance(extended_change_pct, Decimal):
        extended_change_pct = Decimal(str(extended_change_pct))

    market_value = total_shares * current_price
    unrealized_pnl = market_value - total_cost_basis
    unrealized_pnl_pct = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > Decimal('0') else Decimal('0')

    # Dual-Currency conversion (THB <-> USD)
    if usd_to_thb_rate is None or usd_to_thb_rate <= Decimal('0'):
        usd_to_thb_rate = get_usd_to_thb_rate()
    elif not isinstance(usd_to_thb_rate, Decimal):
        usd_to_thb_rate = Decimal(str(usd_to_thb_rate))

    h_currency = (holding.currency or 'THB').upper()

    if h_currency == 'USD':
        mval_usd = market_value
        cost_usd = total_cost_basis
        pnl_usd = unrealized_pnl
        realized_usd = total_realized_pnl
        div_usd = total_dividends
        price_usd = current_price
        avg_cost_usd = avg_cost

        mval_thb = market_value * usd_to_thb_rate
        cost_thb = total_cost_basis * usd_to_thb_rate
        pnl_thb = unrealized_pnl * usd_to_thb_rate
        realized_thb = total_realized_pnl * usd_to_thb_rate
        div_thb = total_dividends * usd_to_thb_rate
        price_thb = current_price * usd_to_thb_rate
        avg_cost_thb = avg_cost * usd_to_thb_rate
    else:
        # THB (or default)
        mval_thb = market_value
        cost_thb = total_cost_basis
        pnl_thb = unrealized_pnl
        realized_thb = total_realized_pnl
        div_thb = total_dividends
        price_thb = current_price
        avg_cost_thb = avg_cost

        rate_inv = (Decimal('1.0') / usd_to_thb_rate) if usd_to_thb_rate > Decimal('0') else Decimal('0')
        mval_usd = market_value * rate_inv
        cost_usd = total_cost_basis * rate_inv
        pnl_usd = unrealized_pnl * rate_inv
        realized_usd = total_realized_pnl * rate_inv
        div_usd = total_dividends * rate_inv
        price_usd = current_price * rate_inv
        avg_cost_usd = avg_cost * rate_inv

    return {
        'shares': total_shares,
        'currency': h_currency,
        'avg_cost': round(avg_cost, 4),
        'total_invested': round(total_cost_basis, 2),
        'current_price': round(current_price, 4),
        'market_value': round(market_value, 2),
        'unrealized_pnl': round(unrealized_pnl, 2),
        'unrealized_pnl_pct': round(unrealized_pnl_pct, 2),
        'total_realized_pnl': round(total_realized_pnl, 2),
        'total_dividends': round(total_dividends, 2),
        'total_realized_return': round(total_realized_pnl + total_dividends, 2),
        'market_session': market_session or 'REGULAR',
        'regular_price': round(regular_price, 4) if regular_price else None,
        'extended_price': round(extended_price, 4) if extended_price else None,
        'extended_change': round(extended_change, 4) if extended_change else None,
        'extended_change_pct': round(extended_change_pct, 4) if extended_change_pct else None,
        'is_active': total_shares > Decimal('0'),
        # Explicit THB values
        'avg_cost_thb': round(avg_cost_thb, 4),
        'current_price_thb': round(price_thb, 4),
        'market_value_thb': round(mval_thb, 2),
        'total_invested_thb': round(cost_thb, 2),
        'unrealized_pnl_thb': round(pnl_thb, 2),
        'total_realized_pnl_thb': round(realized_thb, 2),
        'total_dividends_thb': round(div_thb, 2),
        'total_realized_return_thb': round(realized_thb + div_thb, 2),
        # Explicit USD values
        'avg_cost_usd': round(avg_cost_usd, 4),
        'current_price_usd': round(price_usd, 4),
        'market_value_usd': round(mval_usd, 2),
        'total_invested_usd': round(cost_usd, 2),
        'unrealized_pnl_usd': round(pnl_usd, 2),
        'total_realized_pnl_usd': round(realized_usd, 2),
        'total_dividends_usd': round(div_usd, 2),
        'total_realized_return_usd': round(realized_usd + div_usd, 2),
    }


def get_usd_to_thb_rate() -> Decimal:
    """
    ดึงอัตราแลกเปลี่ยน USD/THB ล่าสุด (เช่น 33.64)
    - แคชใน StockPriceSnapshot เพื่อความรวดเร็วและประหยัดเน็ต
    - Fallback ไปยัง yfinance USDTHB=X หรือค่าเฉลี่ย 34.50 ถ้าออฟไลน์
    """
    snap = StockPriceSnapshot.objects.filter(ticker='USDTHB=X').first()
    if snap and (timezone.now() - snap.fetched_at).total_seconds() < 3600:
        return snap.price

    try:
        import yfinance as yf
        ticker = yf.Ticker('USDTHB=X')
        price = ticker.fast_info.get('lastPrice') or ticker.fast_info.get('regularMarketPrice')
        if price:
            dec_price = Decimal(str(round(price, 4)))
            StockPriceSnapshot.objects.update_or_create(
                ticker='USDTHB=X',
                defaults={'price': dec_price, 'currency': 'THB'}
            )
            return dec_price
    except Exception:
        pass

    if snap:
        return snap.price
    return Decimal('34.50')


def get_portfolio_overview(
    user,
    currency: str = 'THB',
    portfolio_id: Optional[str] = None,
    asset_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    ดึงภาพรวมสรุปมูลค่าพอร์ตและผลตอบแทนทั้งหมดของผู้ใช้ (Optimized Prefetching)
    - รองรับสลับมุมมองสกุลเงินสองทาง (THB <-> USD)
    - รองรับกรองแยกตามประเภทสินทรัพย์ (STOCK, CRYPTO, FUND, OTHER)
    - รองรับการแยกพอร์ตการลงทุนหลายพอร์ต (เหมือน Dime Multi-Portfolio)
    """
    from django.db.models import Prefetch

    # ตรวจสอบและสร้างพอร์ตเริ่มต้นถ้ายังไม่มี
    default_pf, _ = InvestmentPortfolio.objects.get_or_create(
        user=user,
        is_default=True,
        defaults={'name': 'Main Portfolio', 'currency': 'THB'}
    )

    qs = StockHolding.objects.filter(user=user)

    # กรองตามพอร์ตเป้าหมาย
    if portfolio_id and portfolio_id.upper() != 'ALL':
        qs = qs.filter(portfolio_id=portfolio_id)

    # กรองตามประเภทสินทรัพย์
    if asset_type and asset_type.upper() != 'ALL':
        qs = qs.filter(asset_type=asset_type.upper())

    holdings = qs.prefetch_related(
        Prefetch('transactions', queryset=StockTransaction.objects.order_by('executed_at'))
    )

    usd_to_thb_rate = get_usd_to_thb_rate()
    selected_curr = currency.upper() if currency else 'THB'
    if selected_curr not in ('THB', 'USD'):
        selected_curr = 'THB'

    # รวบรวม Tickers เพื่อดึงราคาแคช
    tickers = [h.ticker for h in holdings]
    cached_prices = {
        s.ticker: s.price for s in StockPriceSnapshot.objects.filter(ticker__in=tickers)
    }

    # ตัวสะสมสำหรับ THB และ USD
    thb_market_value = Decimal('0.00')
    thb_cost_basis = Decimal('0.00')
    thb_realized_pnl = Decimal('0.00')
    thb_dividends = Decimal('0.00')

    usd_market_value = Decimal('0.00')
    usd_cost_basis = Decimal('0.00')
    usd_realized_pnl = Decimal('0.00')
    usd_dividends = Decimal('0.00')

    holdings_summary = []

    for h in holdings:
        price = cached_prices.get(h.ticker)
        pos = calculate_detailed_position(h, current_price=price, usd_to_thb_rate=usd_to_thb_rate)

        if pos['is_active']:
            thb_market_value += pos['market_value_thb']
            thb_cost_basis += pos['total_invested_thb']
            usd_market_value += pos['market_value_usd']
            usd_cost_basis += pos['total_invested_usd']

        thb_realized_pnl += pos['total_realized_pnl_thb']
        thb_dividends += pos['total_dividends_thb']
        usd_realized_pnl += pos['total_realized_pnl_usd']
        usd_dividends += pos['total_dividends_usd']

        holdings_summary.append({
            'id': str(h.id),
            'ticker': h.ticker,
            'name': h.name or h.ticker,
            'asset_type': h.asset_type,
            'currency': pos.get('currency', 'THB'),
            'position': pos
        })

    # ฟังก์ชันคำนวณสัดส่วน Asset Allocation ตามสกุลเงินเป้าหมาย
    def calc_allocations(target_curr: str):
        alloc_map = {}
        tot_val = thb_market_value if target_curr == 'THB' else usd_market_value
        for h in holdings_summary:
            if not h['position']['is_active']:
                continue
            atype = h['asset_type']
            mval = h['position']['market_value_thb'] if target_curr == 'THB' else h['position']['market_value_usd']
            if atype not in alloc_map:
                alloc_map[atype] = {'type': atype, 'value': Decimal('0'), 'count': 0}
            alloc_map[atype]['value'] += mval
            alloc_map[atype]['count'] += 1

        alist = []
        for atype, data in alloc_map.items():
            pct = round((data['value'] / tot_val * 100), 2) if tot_val > Decimal('0') else Decimal('0')
            alist.append({
                'type': atype,
                'label': dict(AssetType.choices).get(atype, atype),
                'value': round(data['value'], 2),
                'percentage': float(pct),
                'count': data['count']
            })
        alist.sort(key=lambda x: x['value'], reverse=True)
        return alist

    alloc_thb = calc_allocations('THB')
    alloc_usd = calc_allocations('USD')

    thb_unrealized_pnl = thb_market_value - thb_cost_basis
    thb_unrealized_pnl_pct = (thb_unrealized_pnl / thb_cost_basis * 100) if thb_cost_basis > Decimal('0') else Decimal('0')

    usd_unrealized_pnl = usd_market_value - usd_cost_basis
    usd_unrealized_pnl_pct = (usd_unrealized_pnl / usd_cost_basis * 100) if usd_cost_basis > Decimal('0') else Decimal('0')

    summary_thb = {
        'total_market_value': round(thb_market_value, 2),
        'total_cost_basis': round(thb_cost_basis, 2),
        'total_unrealized_pnl': round(thb_unrealized_pnl, 2),
        'total_unrealized_pnl_pct': round(thb_unrealized_pnl_pct, 2),
        'total_realized_pnl': round(thb_realized_pnl, 2),
        'total_dividends': round(thb_dividends, 2),
        'total_realized_return': round(thb_realized_pnl + thb_dividends, 2),
        'asset_allocation': alloc_thb,
    }

    summary_usd = {
        'total_market_value': round(usd_market_value, 2),
        'total_cost_basis': round(usd_cost_basis, 2),
        'total_unrealized_pnl': round(usd_unrealized_pnl, 2),
        'total_unrealized_pnl_pct': round(usd_unrealized_pnl_pct, 2),
        'total_realized_pnl': round(usd_realized_pnl, 2),
        'total_dividends': round(usd_dividends, 2),
        'total_realized_return': round(usd_realized_pnl + usd_dividends, 2),
        'asset_allocation': alloc_usd,
    }

    active_summary = summary_thb if selected_curr == 'THB' else summary_usd

    # ดึงรายชื่อพอร์ตการลงทุนทั้งหมดของผู้ใช้ (สำหรับ Dime Switcher)
    all_user_portfolios = InvestmentPortfolio.objects.filter(user=user).order_by('-is_default', 'created_at')
    portfolios_data = []
    for p in all_user_portfolios:
        p_holdings_count = p.holdings.count()
        portfolios_data.append({
            'id': str(p.id),
            'name': p.name,
            'description': p.description,
            'currency': p.currency,
            'color': p.color,
            'is_default': p.is_default,
            'holdings_count': p_holdings_count
        })

    return {
        'base_currency': selected_curr,
        'usd_to_thb_rate': float(round(usd_to_thb_rate, 4)),
        'selected_portfolio_id': str(portfolio_id) if portfolio_id and portfolio_id != 'ALL' else 'ALL',
        'selected_asset_type': asset_type if asset_type else 'ALL',
        'available_portfolios': portfolios_data,
        'total_market_value': active_summary['total_market_value'],
        'total_cost_basis': active_summary['total_cost_basis'],
        'total_unrealized_pnl': active_summary['total_unrealized_pnl'],
        'total_unrealized_pnl_pct': active_summary['total_unrealized_pnl_pct'],
        'total_realized_pnl': active_summary['total_realized_pnl'],
        'total_dividends': active_summary['total_dividends'],
        'active_assets_count': len([h for h in holdings_summary if h['position']['is_active']]),
        'asset_allocation': active_summary['asset_allocation'],
        'summary_thb': summary_thb,
        'summary_usd': summary_usd,
        'holdings': holdings_summary
    }
