import re
from typing import List, Dict, Any, Optional
from .models import AssetType


# Default Reference Asset Database (Instant Sub-millisecond Lookup)
MASTER_ASSET_CATALOG: List[Dict[str, Any]] = [
    # --- Popular Thai Equities (SET50 / SET100) ---
    {'ticker': 'PTT.BK', 'name': 'PTT Public Company Limited', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'DELTA.BK', 'name': 'Delta Electronics (Thailand)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'AOT.BK', 'name': 'Airports of Thailand', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CPALL.BK', 'name': 'CP ALL Public Company Limited', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'ADVANC.BK', 'name': 'Advanced Info Service (AIS)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'GULF.BK', 'name': 'Gulf Energy Development', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SCB.BK', 'name': 'SCB X Public Company Limited', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KBANK.BK', 'name': 'Kasikornbank', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BBL.BK', 'name': 'Bangkok Bank', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KTB.BK', 'name': 'Krungthai Bank', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BDMS.BK', 'name': 'Bangkok Dusit Medical Services', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BH.BK', 'name': 'Bumrungrad Hospital', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SCC.BK', 'name': 'Siam Cement', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CPN.BK', 'name': 'Central Pattana', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CRC.BK', 'name': 'Central Retail Corporation', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'MINT.BK', 'name': 'Minor International', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TRUE.BK', 'name': 'True Corporation', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'INTUCH.BK', 'name': 'Intouch Holdings', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'HMPRO.BK', 'name': 'Home Product Center', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'WHA.BK', 'name': 'WHA Corporation', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BEM.BK', 'name': 'Bangkok Expressway and Metro', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BTS.BK', 'name': 'BTS Group Holdings', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BANPU.BK', 'name': 'Banpu Public Company Limited', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'IVL.BK', 'name': 'Indorama Ventures', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KTC.BK', 'name': 'Krungthai Card', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'MTC.BK', 'name': 'Muangthai Capital', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SAWAD.BK', 'name': 'Srisawad Corporation', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'OSP.BK', 'name': 'Osotspa', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CBG.BK', 'name': 'Carabao Group', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BGRIM.BK', 'name': 'B.Grimm Power', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'GPSC.BK', 'name': 'Global Power Synergy', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TOP.BK', 'name': 'Thai Oil', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'IRPC.BK', 'name': 'IRPC Public Company Limited', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'PTTEP.BK', 'name': 'PTT Exploration and Production', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TU.BK', 'name': 'Thai Union Group', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'LH.BK', 'name': 'Land and Houses', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'OR.BK', 'name': 'PTT Oil and Retail Business', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},

    # --- US Equities: Mega Tech & Blue Chips ---
    {'ticker': 'AAPL', 'name': 'Apple Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'GOOGL', 'name': 'Alphabet Inc. (Google Class A)', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'GOOG', 'name': 'Alphabet Inc. (Google Class C)', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'META', 'name': 'Meta Platforms Inc. (Facebook/Instagram)', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'BRK.B', 'name': 'Berkshire Hathaway Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'AVGO', 'name': 'Broadcom Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'TSM', 'name': 'Taiwan Semiconductor Manufacturing Co.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'BABA', 'name': 'Alibaba Group Holding Limited', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'V', 'name': 'Visa Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'WMT', 'name': 'Walmart Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'UNH', 'name': 'UnitedHealth Group Incorporated', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'MA', 'name': 'Mastercard Incorporated', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'AMD', 'name': 'Advanced Micro Devices Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'INTC', 'name': 'Intel Corporation', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'PLTR', 'name': 'Palantir Technologies Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'COIN', 'name': 'Coinbase Global Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'DIS', 'name': 'The Walt Disney Company', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'SMCI', 'name': 'Super Micro Computer Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'ARM', 'name': 'Arm Holdings plc', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'CRWD', 'name': 'CrowdStrike Holdings Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'UBER', 'name': 'Uber Technologies Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'ABNB', 'name': 'Airbnb Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'CRM', 'name': 'Salesforce Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'ORCL', 'name': 'Oracle Corporation', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'SHOP', 'name': 'Shopify Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'PYPL', 'name': 'PayPal Holdings Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'SQ', 'name': 'Block Inc. (Square)', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'SOFI', 'name': 'SoFi Technologies Inc.', 'asset_type': AssetType.STOCK, 'currency': 'USD', 'exchange': 'NASDAQ'},

    # --- US ETFs & Index Funds ---
    {'ticker': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'QQQ', 'name': 'Invesco QQQ Trust (Nasdaq 100)', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'SCHD', 'name': 'Schwab U.S. Dividend Equity ETF', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NYSE'},
    {'ticker': 'TLT', 'name': 'iShares 20+ Year Treasury Bond ETF', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NASDAQ'},
    {'ticker': 'ARKK', 'name': 'ARK Innovation ETF', 'asset_type': AssetType.FUND, 'currency': 'USD', 'exchange': 'NYSE'},

    # --- Cryptocurrencies ---
    {'ticker': 'BTC-USD', 'name': 'Bitcoin', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'ETH-USD', 'name': 'Ethereum', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SOL-USD', 'name': 'Solana', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'BNB-USD', 'name': 'Binance Coin', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'XRP-USD', 'name': 'XRP', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'DOGE-USD', 'name': 'Dogecoin', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'ADA-USD', 'name': 'Cardano', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'AVAX-USD', 'name': 'Avalanche', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SUI-USD', 'name': 'Sui Network', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'LINK-USD', 'name': 'Chainlink', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'PEPE-USD', 'name': 'Pepe', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SHIB-USD', 'name': 'Shiba Inu', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'NEAR-USD', 'name': 'NEAR Protocol', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'DOT-USD', 'name': 'Polkadot', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},

    # --- Thai Mutual Funds ---
    {'ticker': 'B-INNOTECH', 'name': 'Bualuang Innovation Mutual Fund (B-INNOTECH)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'BBLAM'},
    {'ticker': 'SCBDV', 'name': 'SCB Dividend Stock Long Term Fund (SCBDV)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'SCBAM'},
    {'ticker': 'KF-GTECH', 'name': 'Krungsri Global Technology Equity Fund (KF-GTECH)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'KSAM'},
    {'ticker': 'ONE-UGG-RA', 'name': 'One Ultimate Global Growth Fund (ONE-UGG-RA)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'ONEAM'},
    {'ticker': 'KT-ENERGY', 'name': 'KTAM Energy and Infrastructure Fund (KT-ENERGY)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'KTAM'}
]


def search_market_assets(query: str, asset_type: Optional[str] = None, limit: int = 12) -> List[Dict[str, Any]]:
    """
    Asset search function for autocomplete input
    - Searches local Master Catalog first for sub-millisecond response
    - If not found or low results, queries live global market via yfinance Search
    - Filters asset categories (STOCK, CRYPTO, FUND, OTHER) as specified
    """
    clean_q = query.strip()
    if not clean_q:
        results = MASTER_ASSET_CATALOG[:limit]
        if asset_type and asset_type.upper() != 'ALL':
            results = [r for r in results if r['asset_type'] == asset_type.upper()]
        return results

    clean_upper = clean_q.upper()
    matched_results: List[Dict[str, Any]] = []
    seen_tickers = set()

    # 1. Search in local catalog first
    for item in MASTER_ASSET_CATALOG:
        t_clean = item['ticker'].upper()
        n_clean = item['name'].upper()
        if (clean_upper in t_clean or clean_upper in n_clean or
            t_clean.replace('.BK', '').startswith(clean_upper) or
            t_clean.replace('-USD', '').startswith(clean_upper)):
            if asset_type and asset_type.upper() != 'ALL' and item['asset_type'] != asset_type.upper():
                continue
            matched_results.append(item)
            seen_tickers.add(item['ticker'])
            if len(matched_results) >= limit:
                return matched_results

    # 2. If results are few, query live yfinance Search
    if len(matched_results) < limit:
        try:
            import yfinance as yf
            search_obj = yf.Search(clean_q, max_results=10)
            raw_quotes = getattr(search_obj, 'quotes', []) or []

            for q in raw_quotes:
                sym = q.get('symbol', '').strip().upper()
                if not sym or sym in seen_tickers:
                    continue

                qtype = (q.get('quoteType') or '').upper()
                if qtype == 'EQUITY':
                    atype = AssetType.STOCK
                elif qtype in ('CRYPTOCURRENCY', 'COIN'):
                    atype = AssetType.CRYPTO
                elif qtype in ('ETF', 'MUTUALFUND'):
                    atype = AssetType.FUND
                else:
                    atype = AssetType.OTHER

                if asset_type and asset_type.upper() != 'ALL' and atype != asset_type.upper():
                    continue

                # Infer currency
                is_thb = sym.endswith('.BK') or (q.get('exchange') or '').upper() == 'SET'
                curr = 'THB' if is_thb else 'USD'
                name_str = q.get('shortname') or q.get('longname') or sym

                item = {
                    'ticker': sym,
                    'name': name_str,
                    'asset_type': atype,
                    'currency': curr,
                    'exchange': q.get('exchDisp') or q.get('exchange') or ('SET' if is_thb else 'US')
                }
                matched_results.append(item)
                seen_tickers.add(sym)
                if len(matched_results) >= limit:
                    break
        except Exception:
            pass

    # Fetch latest market price from StockPriceSnapshot to populate search results
    try:
        from .models import StockPriceSnapshot
        tickers_list = [r['ticker'] for r in matched_results]
        snapshots = {s.ticker: s for s in StockPriceSnapshot.objects.filter(ticker__in=tickers_list)}
        enriched = []
        for r in matched_results:
            item = dict(r)
            snap = snapshots.get(item['ticker'])
            if snap and snap.price:
                item['price'] = float(snap.price)
                item['change_amount'] = float(snap.change_amount) if snap.change_amount else 0.0
                item['change_pct'] = float(snap.change_pct) if snap.change_pct else 0.0
            else:
                item['price'] = None
                item['change_amount'] = None
                item['change_pct'] = None
            enriched.append(item)
        return enriched
    except Exception:
        return matched_results


def verify_ticker_exists(ticker_str: str) -> Optional[Dict[str, Any]]:
    """
    Strictly verify whether ticker exists in market
    Returns None if not found to prevent invalid tickers
    """
    from .models import StockPriceSnapshot, StockHolding
    clean = ticker_str.strip().upper()
    if not clean:
        return None

    # 1. Check in Master Catalog
    for item in MASTER_ASSET_CATALOG:
        if item['ticker'].upper() == clean:
            return item

    # 2. Check in StockPriceSnapshot or StockHolding
    if StockPriceSnapshot.objects.filter(ticker__iexact=clean).exists():
        snap = StockPriceSnapshot.objects.filter(ticker__iexact=clean).first()
        return {
            'ticker': snap.ticker,
            'name': snap.ticker,
            'asset_type': AssetType.CRYPTO if '-USD' in clean else AssetType.STOCK,
            'currency': snap.currency,
            'exchange': 'Market'
        }

    # 3. Check live via yfinance
    try:
        import yfinance as yf
        stock = yf.Ticker(clean)

        # 3.1 Verify via fast_info
        fast_info = getattr(stock, 'fast_info', None)
        if fast_info:
            try:
                price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
                if price is not None and float(price) > 0:
                    is_thb = clean.endswith('.BK')
                    return {
                        'ticker': clean,
                        'name': clean,
                        'asset_type': AssetType.CRYPTO if '-USD' in clean else AssetType.STOCK,
                        'currency': 'THB' if is_thb else 'USD',
                        'exchange': 'SET' if is_thb else 'US'
                    }
            except Exception:
                pass

        # 3.2 Fallback check via history if fast_info fails
        try:
            hist = stock.history(period='2d')
            if hist is not None and not hist.empty and len(hist) > 0:
                is_thb = clean.endswith('.BK')
                return {
                    'ticker': clean,
                    'name': clean,
                    'asset_type': AssetType.CRYPTO if '-USD' in clean else AssetType.STOCK,
                    'currency': 'THB' if is_thb else 'USD',
                    'exchange': 'SET' if is_thb else 'US'
                }
        except Exception:
            pass
    except Exception:
        pass

    return None
