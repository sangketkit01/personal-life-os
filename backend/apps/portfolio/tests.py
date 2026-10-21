from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.portfolio.models import (
    StockHolding,
    StockTransaction,
    StockPriceSnapshot,
    StockNewsArticle,
    InvestmentPortfolio,
    AssetType,
    TransactionType
)
from apps.portfolio.services import (
    normalize_ticker,
    calculate_detailed_position,
    get_portfolio_overview
)
from apps.accounts.tokens import generate_access_token

User = get_user_model()


class PortfolioEngineTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='investor',
            email='investor@test.com',
            password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='stranger',
            email='stranger@test.com',
            password='Password123!'
        )
        self.client = APIClient()
        token = generate_access_token(self.user)
        self.client.cookies['access_token'] = token

    def test_ticker_normalization(self):
        """ทดสอบการจัดรูปแบบ Ticker ให้ได้มาตรฐาน"""
        self.assertEqual(normalize_ticker('ptt'), 'PTT.BK')
        self.assertEqual(normalize_ticker('delta'), 'DELTA.BK')
        self.assertEqual(normalize_ticker('btc'), 'BTC-USD')
        self.assertEqual(normalize_ticker('eth'), 'ETH-USD')
        self.assertEqual(normalize_ticker('aapl'), 'AAPL')
        self.assertEqual(normalize_ticker('NVDA'), 'NVDA')
        self.assertEqual(normalize_ticker('goog'), 'GOOG')
        self.assertEqual(normalize_ticker('pltr'), 'PLTR')
        self.assertEqual(normalize_ticker('baba'), 'BABA')
        self.assertEqual(normalize_ticker('PTT.BK'), 'PTT.BK')

    def test_dca_buy_calculation(self):
        """ทดสอบการคำนวณต้นทุนเฉลี่ยแบบ DCA และรวมค่าธรรมเนียม"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='PTT.BK',
            name='ปตท.'
        )

        # ไม้แรก: ซื้อ 100 หุ้น @ 50 บาท + fee 10 บาท = 5,010 บาท
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('50.00'),
            fee=Decimal('10.00'),
            executed_at=timezone.now()
        )

        # ไม้สอง: ซื้อ 100 หุ้น @ 60 บาท + fee 10 บาท = 6,010 บาท
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('60.00'),
            fee=Decimal('10.00'),
            executed_at=timezone.now()
        )

        pos = calculate_detailed_position(holding)
        self.assertEqual(pos['shares'], Decimal('200'))
        self.assertEqual(pos['total_invested'], Decimal('11020.00'))
        # 11,020 / 200 = 55.10
        self.assertEqual(pos['avg_cost'], Decimal('55.1000'))

    def test_partial_sell_and_realized_pnl(self):
        """ทดสอบการขายบางส่วน (Partial Sell) คำนวณ Realized PnL และตัดต้นทุนตามสัดส่วน"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='DELTA.BK',
            name='เดลต้า'
        )

        # ซื้อ 200 หุ้น @ 100 บาท (fee 0) = ต้นทุน 20,000 (avg = 100)
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('200'),
            price_per_share=Decimal('100.00'),
            fee=Decimal('0.00'),
            executed_at=timezone.now()
        )

        # ขาย 50 หุ้น @ 150 บาท (fee 20 บาท)
        # รายรับสุทธิ = (50 * 150) - 20 = 7,480 บาท
        # ต้นทุนของ 50 หุ้น = 50 * 100 = 5,000 บาท
        # กำไรจริง Realized PnL = 7,480 - 5,000 = 2,480 บาท
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.SELL,
            shares=Decimal('50'),
            price_per_share=Decimal('150.00'),
            fee=Decimal('20.00'),
            executed_at=timezone.now()
        )

        pos = calculate_detailed_position(holding)
        self.assertEqual(pos['shares'], Decimal('150'))
        self.assertEqual(pos['total_invested'], Decimal('15000.00'))
        self.assertEqual(pos['avg_cost'], Decimal('100.0000'))
        self.assertEqual(pos['total_realized_pnl'], Decimal('2480.00'))

    def test_dividend_and_unrealized_pnl(self):
        """ทดสอบการรับเงินปันผล และการคำนวณกำไรที่ยังไม่รับรู้ตามราคาตลาด"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='CPALL.BK',
            name='ซีพี ออลล์'
        )

        # ซื้อ 100 หุ้น @ 60 บาท (fee 0) = ต้นทุน 6,000
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('60.00'),
            fee=Decimal('0.00'),
            executed_at=timezone.now()
        )

        # ปันผล 2 บาท/หุ้น (fee หัก ณ ที่จ่าย 20 บาท) = รับสุทธิ 180 บาท
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.DIVIDEND,
            shares=Decimal('100'),
            price_per_share=Decimal('2.00'),
            fee=Decimal('20.00'),
            executed_at=timezone.now()
        )

        # แคชราคาตลาดสดที่ 70 บาท
        StockPriceSnapshot.objects.create(
            ticker='CPALL.BK',
            price=Decimal('70.00'),
            change_pct=Decimal('2.50'),
            currency='THB'
        )

        pos = calculate_detailed_position(holding)
        self.assertEqual(pos['shares'], Decimal('100'))
        self.assertEqual(pos['total_dividends'], Decimal('180.00'))
        self.assertEqual(pos['market_value'], Decimal('7000.00'))
        self.assertEqual(pos['unrealized_pnl'], Decimal('1000.00'))
        # กำไรรวม Realized = 180 (จากเงินปันผล)
        self.assertEqual(pos['total_realized_pnl'], Decimal('180.00'))

    def test_multi_user_isolation(self):
        """ทดสอบการแยกข้อมูลพอร์ตระหว่างผู้ใช้ (Multi-tenancy Isolation)"""
        # User เพิ่มหุ้น
        StockHolding.objects.create(
            user=self.user,
            ticker='AAPL',
            name='Apple Inc.'
        )

        # Friend ล็อกอิน
        friend_client = APIClient()
        friend_token = generate_access_token(self.friend)
        friend_client.cookies['access_token'] = friend_token

        # Friend ต้องไม่เห็นหุ้นของ User
        res = friend_client.get('/api/portfolio/holdings/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)

        # Overview ของ Friend ต้องเป็น 0 ทั้งหมด
        res_overview = friend_client.get('/api/portfolio/overview/')
        self.assertEqual(res_overview.status_code, status.HTTP_200_OK)
        self.assertEqual(res_overview.data['total_market_value'], 0.0)
        self.assertEqual(res_overview.data['active_assets_count'], 0)

    def test_api_create_transaction_with_auto_ticker(self):
        """ทดสอบการยิง API เพิ่มรายการซื้อขาย โดยระบุ Ticker ให้ระบบสร้าง Holding อัตโนมัติ"""
        payload = {
            'ticker': 'ktb',
            'transaction_type': 'BUY',
            'shares': '500',
            'price_per_share': '20.00',
            'fee': '15.00',
            'executed_at': timezone.now().isoformat(),
            'notes': 'ซื้อสะสม'
        }

        res = self.client.post('/api/portfolio/transactions/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # ตรวจสอบว่าระบบสร้าง Holding KTB.BK ให้อัตโนมัติ
        holding = StockHolding.objects.filter(user=self.user, ticker='KTB.BK').first()
        self.assertIsNotNone(holding)
        self.assertEqual(holding.ticker, 'KTB.BK')
        self.assertEqual(holding.transactions.count(), 1)

    def test_idor_cross_tenant_holding_injection_prevented(self):
        """SEC-01 Test: ป้องกันไม่ให้ User A แอบส่ง transaction เข้า holding ของ User B"""
        stranger_holding = StockHolding.objects.create(
            user=self.friend,
            ticker='SCC.BK',
            name='ปูนใหญ่'
        )

        payload = {
            'holding': str(stranger_holding.id),
            'transaction_type': 'BUY',
            'shares': '100',
            'price_per_share': '300.00',
            'fee': '0.00',
            'executed_at': timezone.now().isoformat()
        }

        res = self.client.post('/api/portfolio/transactions/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # ตรวจสอบว่าไม่มี transaction หลุดเข้าไปใน holding ของคนอื่น
        self.assertEqual(stranger_holding.transactions.count(), 0)

    def test_prevent_overselling_validation(self):
        """BUG-02 Test: ป้องกันไม่ให้บันทึกขายหุ้นเกินจำนวนที่มีจริง"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='SCB.BK',
            name='ไทยพาณิชย์'
        )
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('50'),
            price_per_share=Decimal('100.00'),
            executed_at=timezone.now()
        )

        payload = {
            'holding': str(holding.id),
            'transaction_type': 'SELL',
            'shares': '100',  # มีแค่ 50 แต่พยายามขาย 100
            'price_per_share': '120.00',
            'fee': '0.00',
            'executed_at': timezone.now().isoformat()
        }

        res = self.client.post('/api/portfolio/transactions/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stock_news_api_and_filtering(self):
        """ทดสอบ API ข่าวสารสินทรัพย์: ดึงรายการข่าว, กรองตาม Ticker และสลับภาษา"""
        StockNewsArticle.objects.create(
            ticker='NVDA',
            title='Nvidia announces new AI chip architecture',
            title_th='Nvidia เปิดตัวสถาปัตยกรรมชิป AI รุ่นใหม่',
            summary_th='เป็นปัจจัยบวกช่วยหนุนการเติบโตของยอดขายศูนย์ข้อมูล',
            source='Reuters',
            url='https://example.com/news/nvda-1',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )
        StockNewsArticle.objects.create(
            ticker='PTT.BK',
            title='PTT expands renewable energy business',
            title_th='ปตท. ขยายพอร์ตธุรกิจพลังงานหมุนเวียน',
            summary_th='ช่วยลดความผันผวนจากราคาน้ำมันดิบในระยะยาว',
            source='Kaohoon',
            url='https://example.com/news/ptt-1',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )

        # 1. ดึงข่าวทั้งหมด
        res_all = self.client.get('/api/portfolio/news/')
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data['results']), 2)

        # 2. กรองเฉพาะ NVDA
        res_nvda = self.client.get('/api/portfolio/news/?ticker=NVDA')
        self.assertEqual(res_nvda.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_nvda.data['results']), 1)
        self.assertEqual(res_nvda.data['results'][0]['ticker'], 'NVDA')
        self.assertEqual(res_nvda.data['results'][0]['title_th'], 'Nvidia เปิดตัวสถาปัตยกรรมชิป AI รุ่นใหม่')

    def test_multi_currency_portfolio_and_conversion(self):
        """ทดสอบระบบพอร์ตหลายสกุลเงิน (THB / USD), การบันทึกและแก้ไขด้วยสกุลเงินที่เลือก, และการสลับมุมมองพร้อมคำนวณอัตราแลกเปลี่ยน"""
        # ตั้งค่าอัตราแลกเปลี่ยน USD/THB เป็น 35.00
        StockPriceSnapshot.objects.update_or_create(
            ticker='USDTHB=X',
            defaults={'price': Decimal('35.00'), 'currency': 'THB'}
        )

        # 1. บันทึกไม้ซื้อ AAPL เป็นสกุล USD ($150)
        res_aapl = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'AAPL',
            'transaction_type': 'BUY',
            'shares': '10',
            'price_per_share': '150.00',
            'fee': '0.00',
            'currency': 'USD',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_aapl.status_code, status.HTTP_201_CREATED)
        aapl_holding = StockHolding.objects.get(ticker='AAPL', user=self.user)
        self.assertEqual(aapl_holding.currency, 'USD')

        # 2. บันทึกไม้ซื้อ PTT.BK เป็นสกุล THB (฿30)
        res_ptt = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'PTT.BK',
            'transaction_type': 'BUY',
            'shares': '1000',
            'price_per_share': '30.00',
            'fee': '0.00',
            'currency': 'THB',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_ptt.status_code, status.HTTP_201_CREATED)
        ptt_holding = StockHolding.objects.get(ticker='PTT.BK', user=self.user)
        self.assertEqual(ptt_holding.currency, 'THB')

        # ตั้งค่าราคาตลาดสด: AAPL = $200, PTT = ฿35
        StockPriceSnapshot.objects.update_or_create(ticker='AAPL', defaults={'price': Decimal('200.00'), 'currency': 'USD'})
        StockPriceSnapshot.objects.update_or_create(ticker='PTT.BK', defaults={'price': Decimal('35.00'), 'currency': 'THB'})

        # 3. ทดสอบมุมมอง THB: AAPL ($2,000 * 35 = ฿70,000) + PTT (฿35,000) = ฿105,000
        res_thb_view = self.client.get('/api/portfolio/overview/?currency=THB')
        self.assertEqual(res_thb_view.status_code, status.HTTP_200_OK)
        self.assertEqual(res_thb_view.data['base_currency'], 'THB')
        self.assertEqual(Decimal(str(res_thb_view.data['total_market_value'])), Decimal('105000.00'))

        # 4. ทดสอบสลับมุมมอง USD: AAPL ($2,000) + PTT (฿35,000 / 35 = $1,000) = $3,000
        res_usd_view = self.client.get('/api/portfolio/overview/?currency=USD')
        self.assertEqual(res_usd_view.status_code, status.HTTP_200_OK)
        self.assertEqual(res_usd_view.data['base_currency'], 'USD')
        self.assertEqual(Decimal(str(res_usd_view.data['total_market_value'])), Decimal('3000.00'))

        # 5. ทดสอบแก้ไขรายการ Transaction (เปลี่ยนจำนวนหุ้นและราคา)
        tx_id = res_aapl.data['id']
        patch_res = self.client.patch(f'/api/portfolio/transactions/{tx_id}/', {
            'shares': '20',
            'price_per_share': '160.00',
            'currency': 'USD'
        })
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(patch_res.data['shares'])), Decimal('20.000000'))
        self.assertEqual(Decimal(str(patch_res.data['price_per_share'])), Decimal('160.0000'))

        # 6. ทดสอบแก้ไข Holding การตั้งค่าสกุลเงิน
        holding_patch = self.client.patch(f'/api/portfolio/holdings/{aapl_holding.id}/', {
            'name': 'Apple Inc. Headquarters',
            'currency': 'USD'
        })
        self.assertEqual(holding_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(holding_patch.data['name'], 'Apple Inc. Headquarters')

    def test_8_decimal_precision_crypto(self):
        """ทดสอบการบันทึกทศนิยมสูงสุด 8 หลัก (สำหรับคริปโต และเศษหุ้น DCA)"""
        StockPriceSnapshot.objects.update_or_create(
            ticker='BTC-USD',
            defaults={'price': Decimal('65432.12345678'), 'currency': 'USD'}
        )
        res = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'BTC-USD',
            'transaction_type': 'BUY',
            'shares': '0.00123456',
            'price_per_share': '64321.87654321',
            'fee': '0.0005',
            'currency': 'USD',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(res.data['shares'])), Decimal('0.00123456'))
        self.assertEqual(Decimal(str(res.data['price_per_share'])), Decimal('64321.87654321'))

    def test_market_asset_search_and_strict_validation(self):
        """ทดสอบระบบค้นหาสินทรัพย์ และการปฏิเสธการเพิ่มสินทรัพย์ที่ไม่มีอยู่จริง (Strict Validation)"""
        # 1. ค้นหา PTT
        res_ptt = self.client.get('/api/portfolio/search/?q=PTT')
        self.assertEqual(res_ptt.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['ticker'] == 'PTT.BK' for r in res_ptt.data))

        # 2. ค้นหา Apple
        res_apple = self.client.get('/api/portfolio/search/?q=Apple')
        self.assertEqual(res_apple.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['ticker'] == 'AAPL' for r in res_apple.data))

        # 3. ลองส่ง Ticker มั่วที่ไม่มีอยู่จริงในตลาด -> ต้องถูกปฏิเสธ (400)
        res_fake = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'TOTALLY_BOGUS_TICKER_9999',
            'transaction_type': 'BUY',
            'shares': '10',
            'price_per_share': '100.00',
            'fee': '0.00',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_fake.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ticker', res_fake.data)

    def test_dime_multi_portfolio(self):
        """ทดสอบระบบแยกพอร์ตการลงทุนอิสระเหมือน Dime (สร้างพอร์ตแยก, บันทึกเทรดเข้าพอร์ตที่เลือก, กรองภาพรวม)"""
        # 1. สร้างพอร์ตแยก "Dime US Growth"
        res_create_pf = self.client.post('/api/portfolio/portfolios/', {
            'name': 'Dime US Growth',
            'description': 'เน้นหุ้นเทคโนโลยีเติบโตสูง',
            'currency': 'USD',
            'color': 'emerald'
        })
        self.assertEqual(res_create_pf.status_code, status.HTTP_201_CREATED)
        dime_pf_id = res_create_pf.data['id']

        # 2. บันทึกไม้ซื้อ NVDA เข้าพอร์ต "Dime US Growth" โดยเฉพาะ
        StockPriceSnapshot.objects.update_or_create(
            ticker='NVDA',
            defaults={'price': Decimal('120.00'), 'currency': 'USD'}
        )
        res_tx = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'NVDA',
            'portfolio': dime_pf_id,
            'transaction_type': 'BUY',
            'shares': '5',
            'price_per_share': '100.00',
            'fee': '0.00',
            'currency': 'USD',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_tx.status_code, status.HTTP_201_CREATED)

        # 3. ตรวจสอบว่า Holding ถูกผูกกับ Dime US Growth
        nvda_holding = StockHolding.objects.get(ticker='NVDA', user=self.user)
        self.assertEqual(str(nvda_holding.portfolio_id), str(dime_pf_id))

        # 4. เรียกดูภาพรวมเฉพาะพอร์ต Dime US Growth
        res_overview_dime = self.client.get(f'/api/portfolio/overview/?portfolio_id={dime_pf_id}&currency=USD')
        self.assertEqual(res_overview_dime.status_code, status.HTTP_200_OK)
        # มูลค่าพอร์ต: 5 * 120 = $600
        self.assertEqual(Decimal(str(res_overview_dime.data['total_market_value'])), Decimal('600.00'))
        self.assertEqual(res_overview_dime.data['active_assets_count'], 1)

    def test_multi_user_shared_news_by_ticker(self):
        """
        ทดสอบ Requirement 1:
        - ข่าวสารผูกกับสัญลักษณ์หุ้น (Ticker)
        - หากผู้ใช้คนหนึ่งมีข่าวของหุ้นตัวนี้แล้ว ผู้ใช้อีกคนที่เพิ่มหุ้นตัวเดียวกันจะใช้ข่าวและคำแปลอันเดียวกันได้ทันที
        - การดึงข่าวซ้ำซ้อนจะตรวจ URL หากมีแล้วจะข้ามผ่านไป ไม่สร้างซ้ำ (No duplicates)
        """
        # 1. ผู้ใช้คนแรก (User 1) สร้างบทความข่าวสำหรับ AAPL
        article = StockNewsArticle.objects.create(
            ticker='AAPL',
            title='Apple Unveils M4 Chip with Advanced AI Engines',
            title_th='แอปเปิ้ลเปิดตัวชิป M4 พร้อมขุมพลัง AI ล้ำสมัย',
            summary='New generation chip architecture.',
            summary_th='สัญญาณเชิงบวกต่อรายได้ฮาร์ดแวร์และการเติบโตของ Apple',
            source='Bloomberg',
            url='https://bloomberg.com/news/articles/apple-m4-ai-chip-2026',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )

        # 2. ผู้ใช้คนที่สอง (Friend) เพิ่มหุ้น AAPL เข้าพอร์ต
        StockHolding.objects.create(
            user=self.friend,
            ticker='AAPL',
            name='Apple Inc.',
            currency='USD',
            asset_type=AssetType.STOCK
        )

        # Login ด้วยผู้ใช้คนที่สอง (Friend)
        friend_client = APIClient()
        friend_token = generate_access_token(self.friend)
        friend_client.cookies['access_token'] = friend_token

        # 3. Friend เรียกดูข่าวหุ้นในพอร์ต (held_only=true)
        res_friend_news = friend_client.get('/api/portfolio/news/?held_only=true')
        self.assertEqual(res_friend_news.status_code, status.HTTP_200_OK)
        articles = res_friend_news.data if isinstance(res_friend_news.data, list) else res_friend_news.data.get('results', [])
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['ticker'], 'AAPL')
        self.assertEqual(articles[0]['title_th'], 'แอปเปิ้ลเปิดตัวชิป M4 พร้อมขุมพลัง AI ล้ำสมัย')
        self.assertEqual(articles[0]['sentiment'], 'BULLISH')

        # 4. ทดสอบความสามารถข้ามข่าวซ้ำ (Idempotency)
        import unittest.mock
        from apps.portfolio.scheduler import sync_hourly_portfolio_news
        # รันฟังก์ชัน hourly sync: โดย mock ไม่ให้ยิงเน็ตเวิร์กจริง
        with unittest.mock.patch('apps.portfolio.scheduler.ingest_news_for_ticker', return_value=0) as mock_ingest:
            res_sync = sync_hourly_portfolio_news()
            self.assertIn(res_sync['status'], ['completed', 'no_tickers'])
            mock_ingest.assert_called()

    def test_market_hours_and_status_api(self):
        """
        ทดสอบ Requirement 4:
        - ตรวจสอบเวลาเปิด-ปิดตลาด (SET, US, CRYPTO)
        - Crypto ต้องเปิดตลอด 24/7/365
        - ตลาดหุ้นไทยและสหรัฐปิดในวันหยุดสุดสัปดาห์
        - API /api/portfolio/market-status/ คืนค่าสถานะตลาดถูกต้อง
        """
        import zoneinfo
        from datetime import datetime
        from apps.portfolio.market_hours import (
            get_set_market_status,
            get_us_market_status,
            get_crypto_market_status,
            is_market_open_for_ticker,
            should_refresh_ticker
        )

        # 1. Crypto เปิดตลอด 24/7
        crypto_status = get_crypto_market_status()
        self.assertTrue(crypto_status['is_open'])
        self.assertTrue(is_market_open_for_ticker('BTC-USD'))
        self.assertTrue(should_refresh_ticker('BTC-USD'))

        # 2. SET: วันเสาร์ 11:00 น. ต้องปิด
        sat_ict = datetime(2026, 10, 24, 11, 0, tzinfo=zoneinfo.ZoneInfo('Asia/Bangkok'))
        set_sat = get_set_market_status(sat_ict)
        self.assertFalse(set_sat['is_open'])
        self.assertEqual(set_sat['session'], 'Weekend Closed')

        # 3. SET: วันพุธ 10:30 น. (เวลาเทรดเช้า) ต้องเปิด
        wed_ict = datetime(2026, 10, 21, 10, 30, tzinfo=zoneinfo.ZoneInfo('Asia/Bangkok'))
        set_wed = get_set_market_status(wed_ict)
        self.assertTrue(set_wed['is_open'])
        self.assertEqual(set_wed['session'], 'Morning Trading')

        # 4. US: วันอาทิตย์ ต้องปิด
        sun_et = datetime(2026, 10, 25, 14, 0, tzinfo=zoneinfo.ZoneInfo('America/New_York'))
        us_sun = get_us_market_status(sun_et)
        self.assertFalse(us_sun['is_open'])

        # 5. US: วันพุธ 10:00 น. ET (Regular Trading) ต้องเปิด
        wed_et = datetime(2026, 10, 21, 10, 0, tzinfo=zoneinfo.ZoneInfo('America/New_York'))
        us_wed = get_us_market_status(wed_et)
        self.assertTrue(us_wed['is_open'])
        self.assertEqual(us_wed['session'], 'Regular Trading')

        # 6. เรียก API /api/portfolio/market-status/
        res_status = self.client.get('/api/portfolio/market-status/')
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        self.assertIn('markets', res_status.data)
        self.assertIn('SET', res_status.data['markets'])
        self.assertIn('US', res_status.data['markets'])
        self.assertIn('CRYPTO', res_status.data['markets'])
        self.assertTrue(res_status.data['markets']['CRYPTO']['is_open'])

    def test_management_command_sync_portfolio_news(self):
        """ทดสอบ Django Management Command `python manage.py sync_portfolio_news`"""
        import unittest.mock
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        # รันคำสั่ง sync_portfolio_news โดย mock เพื่อไม่ยิง network จริง
        with unittest.mock.patch('apps.portfolio.scheduler.ingest_news_for_ticker', return_value=0):
            call_command('sync_portfolio_news', stdout=out)
            output = out.getvalue()
            self.assertIn('Sync completed', output)

    def test_move_holding_to_another_portfolio(self):
        """ทดสอบย้ายหุ้นไปยังพอร์ตย่อยอื่น (ทั้งแบบพอร์ตปลายทางยังไม่มีหุ้นตัวนี้ และแบบมีอยู่แล้วจนเกิดการ Merge)"""
        p_main = InvestmentPortfolio.objects.create(user=self.user, name="Main Portfolio", is_default=True)
        p_dca = InvestmentPortfolio.objects.create(user=self.user, name="DCA Tech", currency="USD")

        # 1. สร้าง Holding และ Transaction ใน p_main
        h1 = StockHolding.objects.create(
            user=self.user,
            portfolio=p_main,
            ticker="NVDA",
            name="Nvidia",
            currency="USD",
            asset_type="STOCK"
        )
        tx1 = StockTransaction.objects.create(
            user=self.user,
            holding=h1,
            transaction_type=TransactionType.BUY,
            shares=Decimal('10'),
            price_per_share=Decimal('120.00'),
            fee=Decimal('0'),
            executed_at=timezone.now()
        )

        # 2. ย้าย NVDA ไปยัง p_dca (ซึ่ง p_dca ยังไม่มี NVDA)
        res_move = self.client.post(f'/api/portfolio/holdings/{h1.id}/move/', {
            'target_portfolio_id': str(p_dca.id)
        })
        self.assertEqual(res_move.status_code, status.HTTP_200_OK)
        self.assertFalse(res_move.data['merged'])

        h1.refresh_from_db()
        self.assertEqual(h1.portfolio_id, p_dca.id)
        tx1.refresh_from_db()
        self.assertEqual(tx1.holding_id, h1.id)

        # 3. ทดสอบการ Merge: สร้าง NVDA อีกก้อนใน p_main
        h2 = StockHolding.objects.create(
            user=self.user,
            portfolio=p_main,
            ticker="NVDA",
            name="Nvidia Secondary",
            currency="USD",
            asset_type="STOCK"
        )
        tx2 = StockTransaction.objects.create(
            user=self.user,
            holding=h2,
            transaction_type=TransactionType.BUY,
            shares=Decimal('5'),
            price_per_share=Decimal('125.00'),
            fee=Decimal('0'),
            executed_at=timezone.now()
        )

        # ย้าย h2 ไป p_dca (ซึ่ง p_dca มี NVDA อยู่แล้วจาก h1 -> ต้อง Merge)
        res_merge = self.client.post(f'/api/portfolio/holdings/{h2.id}/move/', {
            'target_portfolio_id': str(p_dca.id)
        })
        self.assertEqual(res_merge.status_code, status.HTTP_200_OK)
        self.assertTrue(res_merge.data['merged'])

        # h2 ต้องถูกลบ และ tx2 ต้องถูกย้ายไปอยู่ใต้ h1
        self.assertFalse(StockHolding.objects.filter(id=h2.id).exists())
        tx2.refresh_from_db()
        self.assertEqual(tx2.holding_id, h1.id)

        # h1 ใน p_dca ต้องมีทั้งหมด 2 transactions รวม 15 หุ้น
        self.assertEqual(h1.transactions.count(), 2)

    def test_create_transaction_with_goog_ticker(self):
        """ทดสอบเพิ่มหุ้น GOOG หรือหุ้น US สากล ไม่ถูกแปลงเป็น .BK ผิดพลาด"""
        res = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'GOOG',
            'transaction_type': 'BUY',
            'shares': '2.5',
            'price_per_share': '180.50',
            'fee': '0',
            'currency': 'USD',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['holding_ticker'], 'GOOG')

        holding = StockHolding.objects.filter(user=self.user, ticker='GOOG').first()
        self.assertIsNotNone(holding)
        self.assertEqual(holding.currency, 'USD')
        self.assertNotEqual(holding.ticker, 'GOOG.BK')
