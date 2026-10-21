import re
from typing import List, Dict, Any, Optional
from .models import AssetType


# ฐานข้อมูลสินทรัพย์อ้างอิงเริ่มต้น (Instant Sub-millisecond Lookup)
MASTER_ASSET_CATALOG: List[Dict[str, Any]] = [
    # --- หุ้นไทย SET50 / SET100 ยอดนิยม ---
    {'ticker': 'PTT.BK', 'name': 'PTT Public Company Limited (ปตท.)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'DELTA.BK', 'name': 'Delta Electronics (Thailand) (เดลต้า อีเลคโทรนิคส์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'AOT.BK', 'name': 'Airports of Thailand (ท่าอากาศยานไทย)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CPALL.BK', 'name': 'CP ALL Public Company Limited (ซีพี ออลล์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'ADVANC.BK', 'name': 'Advanced Info Service (แอดวานซ์ อินโฟร์ เซอร์วิส - AIS)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'GULF.BK', 'name': 'Gulf Energy Development (กัลฟ์ เอ็นเนอร์จี)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SCB.BK', 'name': 'SCB X Public Company Limited (เอสซีบี เอกซ์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KBANK.BK', 'name': 'Kasikornbank (ธนาคารกสิกรไทย)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BBL.BK', 'name': 'Bangkok Bank (ธนาคารกรุงเทพ)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KTB.BK', 'name': 'Krungthai Bank (ธนาคารกรุงไทย)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BDMS.BK', 'name': 'Bangkok Dusit Medical Services (กรุงเทพดุสิตเวชการ)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BH.BK', 'name': 'Bumrungrad Hospital (โรงพยาบาลบำรุงราษฎร์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SCC.BK', 'name': 'Siam Cement (ปูนซิเมนต์ไทย)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CPN.BK', 'name': 'Central Pattana (เซ็นทรัลพัฒนา)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CRC.BK', 'name': 'Central Retail Corporation (เซ็นทรัล รีเทล)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'MINT.BK', 'name': 'Minor International (ไมเนอร์ อินเตอร์เนชั่นแนล)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TRUE.BK', 'name': 'True Corporation (ทรู คอร์ปอเรชั่น)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'INTUCH.BK', 'name': 'Intouch Holdings (อินทัช โฮลดิ้งส์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'HMPRO.BK', 'name': 'Home Product Center (โฮม โปรดักส์ เซ็นเตอร์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'WHA.BK', 'name': 'WHA Corporation (ดับบลิวเอชเอ คอร์ปอเรชั่น)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BEM.BK', 'name': 'Bangkok Expressway and Metro (ทางด่วนและรถไฟฟ้ากรุงเทพ)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BTS.BK', 'name': 'BTS Group Holdings (บีทีเอส กรุ๊ป)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BANPU.BK', 'name': 'Banpu Public Company Limited (บ้านปู)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'IVL.BK', 'name': 'Indorama Ventures (อินโดรามา เวนเจอร์ส)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'KTC.BK', 'name': 'Krungthai Card (บัตรกรุงไทย)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'MTC.BK', 'name': 'Muangthai Capital (เมืองไทย แคปปิตอล)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'SAWAD.BK', 'name': 'Srisawad Corporation (ศรีสวัสดิ์ คอร์ปอเรชั่น)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'OSP.BK', 'name': 'Osotspa (โอสถสภา)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'CBG.BK', 'name': 'Carabao Group (คาราบาวกรุ๊ป)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'BGRIM.BK', 'name': 'B.Grimm Power (บี.กริม เพาเวอร์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'GPSC.BK', 'name': 'Global Power Synergy (โกลบอล เพาเวอร์ ซินเนอร์ยี่)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TOP.BK', 'name': 'Thai Oil (ไทยออยล์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'IRPC.BK', 'name': 'IRPC Public Company Limited (ไออาร์พีซี)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'PTTEP.BK', 'name': 'PTT Exploration and Production (ปตท.สผ.)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'TU.BK', 'name': 'Thai Union Group (ไทยยูเนี่ยน กรุ๊ป)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'LH.BK', 'name': 'Land and Houses (แลนด์แอนด์เฮ้าส์)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},
    {'ticker': 'OR.BK', 'name': 'PTT Oil and Retail Business (ปตท. น้ำมันและการค้าปลีก)', 'asset_type': AssetType.STOCK, 'currency': 'THB', 'exchange': 'SET'},

    # --- หุ้นสหรัฐฯ US Mega Tech & Blue Chips ---
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

    # --- Cryptocurrencies (เหรียญคริปโต) ---
    {'ticker': 'BTC-USD', 'name': 'Bitcoin (บิตคอยน์)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'ETH-USD', 'name': 'Ethereum (อีเธอเรียม)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SOL-USD', 'name': 'Solana (โซลานา)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'BNB-USD', 'name': 'Binance Coin (ไบแนนซ์คอยน์)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'XRP-USD', 'name': 'XRP (ริปเปิล)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'DOGE-USD', 'name': 'Dogecoin (โดชคอยน์)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'ADA-USD', 'name': 'Cardano (คาร์ดาโน)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'AVAX-USD', 'name': 'Avalanche (อะวาแลนช์)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SUI-USD', 'name': 'Sui Network (ซุย)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'LINK-USD', 'name': 'Chainlink (เชนลิงก์)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'PEPE-USD', 'name': 'Pepe (เปเป้)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'SHIB-USD', 'name': 'Shiba Inu (ชิบะอินุ)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'NEAR-USD', 'name': 'NEAR Protocol', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},
    {'ticker': 'DOT-USD', 'name': 'Polkadot (โพลคาด็อต)', 'asset_type': AssetType.CRYPTO, 'currency': 'USD', 'exchange': 'Crypto'},

    # --- กองทุนรวมไทย (Mutual Funds) ---
    {'ticker': 'B-INNOTECH', 'name': 'กองทุนเปิดบัวหลวงอินโนเวชั่น (B-INNOTECH)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'BBLAM'},
    {'ticker': 'SCBDV', 'name': 'กองทุนเปิดไทยพาณิชย์ปันผลหุ้นระยะยาว (SCBDV)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'SCBAM'},
    {'ticker': 'KF-GTECH', 'name': 'กองทุนเปิดกรุงศรีโกลบอลเทคโนโลยีอิควิตี้ (KF-GTECH)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'KSAM'},
    {'ticker': 'ONE-UGG-RA', 'name': 'วรรณ อัลติเมท โกลบอล โกรว์ธ (ONE-UGG-RA)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'ONEAM'},
    {'ticker': 'KT-ENERGY', 'name': 'กองทุนเปิดเคแทม เอนเนอร์จี แอนด์ โครงสร้างพื้นฐาน (KT-ENERGY)', 'asset_type': AssetType.FUND, 'currency': 'THB', 'exchange': 'KTAM'}
]


def search_market_assets(query: str, asset_type: Optional[str] = None, limit: int = 12) -> List[Dict[str, Any]]:
    """
    ฟังก์ชันค้นหาสินทรัพย์สำหรับการกรอกข้อมูลแบบ Autocomplete
    - ค้นหาจาก Master Catalog ท้องถิ่นก่อนเพื่อความเร็วในระดับมิลลิวินาที
    - หากค้นหาไม่พบ หรือผลลัพธ์น้อย ให้เชื่อมโยง yfinance Search สดจากตลาดโลก
    - กรองแยกประเภทสินทรัพย์ (STOCK, CRYPTO, FUND, OTHER) ตามที่ระบุ
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

    # 1. ค้นหาในแคตาล็อกท้องถิ่นก่อน
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

    # 2. หากผลลัพธ์ยังน้อย ให้ถาม yfinance Search สด
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

                # เดาสกุลเงิน
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

    # ดึงราคาตลาดล่าสุดจาก StockPriceSnapshot มาเติมในผลการค้นหา
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
    ตรวจสอบอย่างเข้มงวดว่า Ticker มีอยู่จริงในตลาดหรือไม่
    หากไม่มีอยู่จริง คืนค่า None เพื่อป้องกันการกรอกมั่ว
    """
    from .models import StockPriceSnapshot, StockHolding
    clean = ticker_str.strip().upper()
    if not clean:
        return None

    # 1. ตรวจใน Master Catalog
    for item in MASTER_ASSET_CATALOG:
        if item['ticker'].upper() == clean:
            return item

    # 2. ตรวจใน StockPriceSnapshot หรือ StockHolding
    if StockPriceSnapshot.objects.filter(ticker__iexact=clean).exists():
        snap = StockPriceSnapshot.objects.filter(ticker__iexact=clean).first()
        return {
            'ticker': snap.ticker,
            'name': snap.ticker,
            'asset_type': AssetType.CRYPTO if '-USD' in clean else AssetType.STOCK,
            'currency': snap.currency,
            'exchange': 'Market'
        }

    # 3. ลองเช็กสดผ่าน yfinance
    try:
        import yfinance as yf
        stock = yf.Ticker(clean)

        # 3.1 ตรวจสอบผ่าน fast_info
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

        # 3.2 Fallback ตรวจสอบผ่าน history ถ้า fast_info โหลดไม่ได้
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
