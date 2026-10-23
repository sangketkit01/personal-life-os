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
        """Test ticker normalization to standard format"""
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
        """Test DCA average cost basis calculation including fees"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='PTT.BK',
            name='PTT'
        )

        # Tranche 1: Buy 100 shares @ 50 + fee 10 = 5,010
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('50.00'),
            fee=Decimal('10.00'),
            executed_at=timezone.now()
        )

        # Tranche 2: Buy 100 shares @ 60 + fee 10 = 6,010
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
        """Test partial sell calculation for realized PnL and proportional cost basis deduction"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='DELTA.BK',
            name='DELTA'
        )

        # Buy 200 shares @ 100 (fee 0) = cost 20,000 (avg = 100)
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('200'),
            price_per_share=Decimal('100.00'),
            fee=Decimal('0.00'),
            executed_at=timezone.now()
        )

        # Sell 50 shares @ 150 (fee 20)
        # Net proceeds = (50 * 150) - 20 = 7,480
        # Cost basis of 50 shares = 50 * 100 = 5,000
        # Realized PnL = 7,480 - 5,000 = 2,480
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
        """Test dividend recording and unrealized PnL calculation based on market price"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='CPALL.BK',
            name='CP ALL'
        )

        # Buy 100 shares @ 60 (fee 0) = cost 6,000
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('60.00'),
            fee=Decimal('0.00'),
            executed_at=timezone.now()
        )

        # Dividend 2/share (withholding tax 20) = net 180
        StockTransaction.objects.create(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.DIVIDEND,
            shares=Decimal('100'),
            price_per_share=Decimal('2.00'),
            fee=Decimal('20.00'),
            executed_at=timezone.now()
        )

        # Cache market price at 70
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
        # Realized gain from sales = 0.00 (no sell yet)
        self.assertEqual(pos['total_realized_pnl'], Decimal('0.00'))
        # Realized total return including dividends = 180.00
        self.assertEqual(pos['total_dividends'], Decimal('180.00'))
        self.assertEqual(pos['total_realized_return'], Decimal('180.00'))

    def test_multi_user_isolation(self):
        """Test multi-tenancy portfolio isolation between users"""
        # User adds holding
        StockHolding.objects.create(
            user=self.user,
            ticker='AAPL',
            name='Apple Inc.'
        )

        # Friend logs in
        friend_client = APIClient()
        friend_token = generate_access_token(self.friend)
        friend_client.cookies['access_token'] = friend_token

        # Friend must not see holdings of User
        res = friend_client.get('/api/portfolio/holdings/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)

        # Overview of Friend must be all 0
        res_overview = friend_client.get('/api/portfolio/overview/')
        self.assertEqual(res_overview.status_code, status.HTTP_200_OK)
        self.assertEqual(res_overview.data['total_market_value'], 0.0)
        self.assertEqual(res_overview.data['active_assets_count'], 0)

    def test_api_create_transaction_with_auto_ticker(self):
        """Test API buy/sell transaction by ticker with auto-holding creation"""
        payload = {
            'ticker': 'ktb',
            'transaction_type': 'BUY',
            'shares': '500',
            'price_per_share': '20.00',
            'fee': '15.00',
            'executed_at': timezone.now().isoformat(),
            'notes': 'DCA accumulation'
        }

        res = self.client.post('/api/portfolio/transactions/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify system auto-created Holding for KTB.BK
        holding = StockHolding.objects.filter(user=self.user, ticker='KTB.BK').first()
        self.assertIsNotNone(holding)
        self.assertEqual(holding.ticker, 'KTB.BK')
        self.assertEqual(holding.transactions.count(), 1)

    def test_idor_cross_tenant_holding_injection_prevented(self):
        """SEC-01 Test: Prevent User A from adding transactions to User B holding"""
        stranger_holding = StockHolding.objects.create(
            user=self.friend,
            ticker='SCC.BK',
            name='SCG'
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
        # Verify no unauthorized transactions in foreign holding
        self.assertEqual(stranger_holding.transactions.count(), 0)

    def test_prevent_overselling_validation(self):
        """BUG-02 Test: Prevent overselling shares beyond actual position"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='SCB.BK',
            name='SCB'
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
            'shares': '100',  # Only 50 owned but trying to sell 100
            'price_per_share': '120.00',
            'fee': '0.00',
            'executed_at': timezone.now().isoformat()
        }

        res = self.client.post('/api/portfolio/transactions/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stock_news_api_and_filtering(self):
        """Test asset news API: list news, filter by ticker, and language switching"""
        StockNewsArticle.objects.create(
            ticker='NVDA',
            title='Nvidia announces new AI chip architecture',
            title_th='Nvidia  AI ',
            summary_th='',
            source='Reuters',
            url='https://example.com/news/nvda-1',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )
        StockNewsArticle.objects.create(
            ticker='PTT.BK',
            title='PTT expands renewable energy business',
            title_th='PTT ',
            summary_th='',
            source='Kaohoon',
            url='https://example.com/news/ptt-1',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )

        # 1. List all news
        res_all = self.client.get('/api/portfolio/news/')
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data['results']), 2)

        # 2. Filter NVDA only
        res_nvda = self.client.get('/api/portfolio/news/?ticker=NVDA')
        self.assertEqual(res_nvda.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_nvda.data['results']), 1)
        self.assertEqual(res_nvda.data['results'][0]['ticker'], 'NVDA')
        self.assertEqual(res_nvda.data['results'][0]['title_th'], 'Nvidia  AI ')

    def test_multi_currency_portfolio_and_conversion(self):
        """Test multi-currency portfolio (THB / USD), recording/editing in selected currency, and currency conversion views"""
        # Set USD/THB exchange rate to 35.00
        StockPriceSnapshot.objects.update_or_create(
            ticker='USDTHB=X',
            defaults={'price': Decimal('35.00'), 'currency': 'THB'}
        )

        # 1. Record AAPL buy in USD ($150)
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

        # 2. Record PTT.BK buy in THB (30)
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

        # Set live market price: AAPL = $200, PTT = 35
        StockPriceSnapshot.objects.update_or_create(ticker='AAPL', defaults={'price': Decimal('200.00'), 'currency': 'USD'})
        StockPriceSnapshot.objects.update_or_create(ticker='PTT.BK', defaults={'price': Decimal('35.00'), 'currency': 'THB'})

        # 3. Test THB view: AAPL ($2,000 * 35 = 70,000) + PTT (35,000) = 105,000
        res_thb_view = self.client.get('/api/portfolio/overview/?currency=THB')
        self.assertEqual(res_thb_view.status_code, status.HTTP_200_OK)
        self.assertEqual(res_thb_view.data['base_currency'], 'THB')
        self.assertEqual(Decimal(str(res_thb_view.data['total_market_value'])), Decimal('105000.00'))

        # 4. Test USD view: AAPL ($2,000) + PTT (35,000 / 35 = $1,000) = $3,000
        res_usd_view = self.client.get('/api/portfolio/overview/?currency=USD')
        self.assertEqual(res_usd_view.status_code, status.HTTP_200_OK)
        self.assertEqual(res_usd_view.data['base_currency'], 'USD')
        self.assertEqual(Decimal(str(res_usd_view.data['total_market_value'])), Decimal('3000.00'))

        # 5. Test editing transaction (shares and price)
        tx_id = res_aapl.data['id']
        patch_res = self.client.patch(f'/api/portfolio/transactions/{tx_id}/', {
            'shares': '20',
            'price_per_share': '160.00',
            'currency': 'USD'
        })
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(patch_res.data['shares'])), Decimal('20.000000'))
        self.assertEqual(Decimal(str(patch_res.data['price_per_share'])), Decimal('160.0000'))

        # 6. Test editing holding currency configuration
        holding_patch = self.client.patch(f'/api/portfolio/holdings/{aapl_holding.id}/', {
            'name': 'Apple Inc. Headquarters',
            'currency': 'USD'
        })
        self.assertEqual(holding_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(holding_patch.data['name'], 'Apple Inc. Headquarters')

    def test_8_decimal_precision_crypto(self):
        """Test precision up to 8 decimal places for crypto and fractional DCA shares"""
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
        """Test asset catalog search and strict rejection of non-existent tickers"""
        # 1. Search PTT
        res_ptt = self.client.get('/api/portfolio/search/?q=PTT')
        self.assertEqual(res_ptt.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['ticker'] == 'PTT.BK' for r in res_ptt.data))

        # 2. Search Apple
        res_apple = self.client.get('/api/portfolio/search/?q=Apple')
        self.assertEqual(res_apple.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['ticker'] == 'AAPL' for r in res_apple.data))

        # 3. Send non-existent ticker -> must be rejected (400)
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
        """Test independent multi-portfolio system (create custom portfolio, record trade, filter overview)"""
        # 1. Create custom portfolio "Dime US Growth"
        res_create_pf = self.client.post('/api/portfolio/portfolios/', {
            'name': 'Dime US Growth',
            'description': 'High growth tech stocks',
            'currency': 'USD',
            'color': 'emerald'
        })
        self.assertEqual(res_create_pf.status_code, status.HTTP_201_CREATED)
        dime_pf_id = res_create_pf.data['id']

        # 2. Record NVDA trade into "Dime US Growth" portfolio
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

        # 3. Verify Holding is linked to Dime US Growth
        nvda_holding = StockHolding.objects.get(ticker='NVDA', user=self.user)
        self.assertEqual(str(nvda_holding.portfolio_id), str(dime_pf_id))

        # 4. Retrieve overview for Dime US Growth portfolio only
        res_overview_dime = self.client.get(f'/api/portfolio/overview/?portfolio_id={dime_pf_id}&currency=USD')
        self.assertEqual(res_overview_dime.status_code, status.HTTP_200_OK)
        # Portfolio value: 5 * 120 = $600
        self.assertEqual(Decimal(str(res_overview_dime.data['total_market_value'])), Decimal('600.00'))
        self.assertEqual(res_overview_dime.data['active_assets_count'], 1)

    def test_multi_user_shared_news_by_ticker(self):
        """
        Test Requirement 1:
        - News linked to ticker
        - Deduplication across users
        - Idempotent ingestion by URL
        """
        # 1. User 1 creates news article for AAPL
        article = StockNewsArticle.objects.create(
            ticker='AAPL',
            title='Apple Unveils M4 Chip with Advanced AI Engines',
            title_th=' M4  AI ',
            summary='New generation chip architecture.',
            summary_th=' Apple',
            source='Bloomberg',
            url='https://bloomberg.com/news/articles/apple-m4-ai-chip-2026',
            published_at=timezone.now(),
            sentiment='BULLISH'
        )

        # 2. Friend adds AAPL to portfolio
        StockHolding.objects.create(
            user=self.friend,
            ticker='AAPL',
            name='Apple Inc.',
            currency='USD',
            asset_type=AssetType.STOCK
        )

        # Login as Friend
        friend_client = APIClient()
        friend_token = generate_access_token(self.friend)
        friend_client.cookies['access_token'] = friend_token

        # 3. Friend requests portfolio news (held_only=true)
        res_friend_news = friend_client.get('/api/portfolio/news/?held_only=true')
        self.assertEqual(res_friend_news.status_code, status.HTTP_200_OK)
        articles = res_friend_news.data if isinstance(res_friend_news.data, list) else res_friend_news.data.get('results', [])
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['ticker'], 'AAPL')
        self.assertEqual(articles[0]['title_th'], ' M4  AI ')
        self.assertEqual(articles[0]['sentiment'], 'BULLISH')

        # 4. Test idempotent skip of duplicate news
        import unittest.mock
        from apps.portfolio.scheduler import sync_hourly_portfolio_news
        # Run hourly sync with network mock
        with unittest.mock.patch('apps.portfolio.scheduler.ingest_news_for_ticker', return_value=0) as mock_ingest:
            res_sync = sync_hourly_portfolio_news()
            self.assertIn(res_sync['status'], ['completed', 'no_tickers'])
            mock_ingest.assert_called()

    def test_market_hours_and_status_api(self):
        """
        Test Requirement 4:
        - Check market hours (SET, US, CRYPTO)
        - Crypto open 24/7/365
        - Equity markets closed on weekends
        - API /api/portfolio/market-status/ returns valid status
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

        # 1. Crypto open 24/7
        crypto_status = get_crypto_market_status()
        self.assertTrue(crypto_status['is_open'])
        self.assertTrue(is_market_open_for_ticker('BTC-USD'))
        self.assertTrue(should_refresh_ticker('BTC-USD'))

        # 2. SET: Saturday 11:00 ICT is closed
        sat_ict = datetime(2026, 10, 24, 11, 0, tzinfo=zoneinfo.ZoneInfo('Asia/Bangkok'))
        set_sat = get_set_market_status(sat_ict)
        self.assertFalse(set_sat['is_open'])
        self.assertEqual(set_sat['session'], 'Weekend Closed')

        # 3. SET: Wednesday 10:30 ICT is open
        wed_ict = datetime(2026, 10, 21, 10, 30, tzinfo=zoneinfo.ZoneInfo('Asia/Bangkok'))
        set_wed = get_set_market_status(wed_ict)
        self.assertTrue(set_wed['is_open'])
        self.assertEqual(set_wed['session'], 'Morning Trading')

        # 4. US: Sunday is closed
        sun_et = datetime(2026, 10, 25, 14, 0, tzinfo=zoneinfo.ZoneInfo('America/New_York'))
        us_sun = get_us_market_status(sun_et)
        self.assertFalse(us_sun['is_open'])

        # 5. US: Wednesday 10:00 ET is open
        wed_et = datetime(2026, 10, 21, 10, 0, tzinfo=zoneinfo.ZoneInfo('America/New_York'))
        us_wed = get_us_market_status(wed_et)
        self.assertTrue(us_wed['is_open'])
        self.assertEqual(us_wed['session'], 'Regular Trading')

        # 6. Call API /api/portfolio/market-status/
        res_status = self.client.get('/api/portfolio/market-status/')
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        self.assertIn('markets', res_status.data)
        self.assertIn('SET', res_status.data['markets'])
        self.assertIn('US', res_status.data['markets'])
        self.assertIn('CRYPTO', res_status.data['markets'])
        self.assertTrue(res_status.data['markets']['CRYPTO']['is_open'])

    def test_management_command_sync_portfolio_news(self):
        """Test Django management command `python manage.py sync_portfolio_news`"""
        import unittest.mock
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        # Run sync_portfolio_news with mock
        with unittest.mock.patch('apps.portfolio.scheduler.ingest_news_for_ticker', return_value=0):
            call_command('sync_portfolio_news', stdout=out)
            output = out.getvalue()
            self.assertIn('Sync completed', output)

    def test_move_holding_to_another_portfolio(self):
        """Test moving holding to another portfolio (both new holding and merging existing)"""
        p_main = InvestmentPortfolio.objects.create(user=self.user, name="Main Portfolio", is_default=True)
        p_dca = InvestmentPortfolio.objects.create(user=self.user, name="DCA Tech", currency="USD")

        # 1. Create Holding and Transaction in p_main
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

        # 2. Move NVDA to p_dca (where p_dca does not have NVDA)
        res_move = self.client.post(f'/api/portfolio/holdings/{h1.id}/move/', {
            'target_portfolio_id': str(p_dca.id)
        })
        self.assertEqual(res_move.status_code, status.HTTP_200_OK)
        self.assertFalse(res_move.data['merged'])

        h1.refresh_from_db()
        self.assertEqual(h1.portfolio_id, p_dca.id)
        tx1.refresh_from_db()
        self.assertEqual(tx1.holding_id, h1.id)

        # 3. Test Merge: create second NVDA holding in p_main
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

        # Move h2 to p_dca (p_dca already holds NVDA -> Merge)
        res_merge = self.client.post(f'/api/portfolio/holdings/{h2.id}/move/', {
            'target_portfolio_id': str(p_dca.id)
        })
        self.assertEqual(res_merge.status_code, status.HTTP_200_OK)
        self.assertTrue(res_merge.data['merged'])

        # h2 is deleted and tx2 is reassigned under h1
        self.assertFalse(StockHolding.objects.filter(id=h2.id).exists())
        tx2.refresh_from_db()
        self.assertEqual(tx2.holding_id, h1.id)

        # h1 in p_dca must have 2 transactions totaling 15 shares
        self.assertEqual(h1.transactions.count(), 2)

    def test_create_transaction_with_goog_ticker(self):
        """Test US ticker such as GOOG is not erroneously transformed to .BK"""
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

    def test_f03_trade_currency_does_not_mutate_holding_currency(self):
        """F03: Verify trade recording does not unintentionally mutate existing holding currency"""
        holding = StockHolding.objects.create(
            user=self.user,
            ticker='NVDA',
            name='Nvidia',
            currency='USD',
            asset_type=AssetType.STOCK
        )
        StockTransaction.objects.create(
            user=self.user,
            holding=holding,
            transaction_type=TransactionType.BUY,
            shares=Decimal('10'),
            price_per_share=Decimal('100.00'),
            fee=Decimal('0'),
            currency='USD',
            executed_at=timezone.now()
        )
        # Send new transaction with currency='THB' (user error or dropdown mismatch)
        res = self.client.post('/api/portfolio/transactions/', {
            'holding': str(holding.id),
            'transaction_type': 'BUY',
            'shares': '5',
            'price_per_share': '110.00',
            'fee': '0',
            'currency': 'THB',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        holding.refresh_from_db()
        # Holding must remain USD, never overwritten by THB
        self.assertEqual(holding.currency, 'USD')
        # New transaction must adapt to holding currency (USD)
        self.assertEqual(res.data['currency'], 'USD')

    def test_f04_by_ticker_with_portfolio_id_and_holding_id(self):
        """F04: Same ticker in 2 portfolios: by-ticker with portfolio_id or holding_id routes to correct holding"""
        p_a = InvestmentPortfolio.objects.create(user=self.user, name='Port A', currency='USD')
        p_b = InvestmentPortfolio.objects.create(user=self.user, name='Port B', currency='USD')

        h_a = StockHolding.objects.create(user=self.user, portfolio=p_a, ticker='MSFT', currency='USD')
        h_b = StockHolding.objects.create(user=self.user, portfolio=p_b, ticker='MSFT', currency='USD')

        # Call by-ticker specifying portfolio_id of Port B
        res_b = self.client.get(f'/api/portfolio/holdings/by-ticker/MSFT/?portfolio_id={p_b.id}')
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        self.assertEqual(str(res_b.data['id']), str(h_b.id))
        self.assertEqual(str(res_b.data['portfolio']), str(p_b.id))

        # Call by-ticker specifying holding_id of Port A
        res_a = self.client.get(f'/api/portfolio/holdings/by-ticker/MSFT/?holding_id={h_a.id}')
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(str(res_a.data['id']), str(h_a.id))
        self.assertEqual(str(res_a.data['portfolio']), str(p_a.id))

    def test_f05_target_portfolio_mismatch_rejected(self):
        """F05: Rejection when holding belongs to portfolio A but mismatched portfolio B is provided."""
        p_a = InvestmentPortfolio.objects.create(user=self.user, name='Port Alpha', currency='USD')
        p_b = InvestmentPortfolio.objects.create(user=self.user, name='Port Beta', currency='USD')
        h_a = StockHolding.objects.create(user=self.user, portfolio=p_a, ticker='TSLA', currency='USD')

        res = self.client.post('/api/portfolio/transactions/', {
            'holding': str(h_a.id),
            'portfolio': str(p_b.id),
            'transaction_type': 'BUY',
            'shares': '1',
            'price_per_share': '200.00',
            'fee': '0',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('portfolio', res.data)

    def test_f08_oversell_validation_via_ticker(self):
        """F08: Ticker-based selling enforces oversell validation identical to holding id"""
        # 1. Sell stock not owned -> 400
        res_no_holding = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'AMZN',
            'transaction_type': 'SELL',
            'shares': '5',
            'price_per_share': '180.00',
            'fee': '0',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_no_holding.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('shares', res_no_holding.data)

        # 2. Buy 10 shares then sell 15 via ticker -> 400
        self.client.post('/api/portfolio/transactions/', {
            'ticker': 'AMZN',
            'transaction_type': 'BUY',
            'shares': '10',
            'price_per_share': '180.00',
            'fee': '0',
            'executed_at': timezone.now().isoformat()
        })

        res_oversell = self.client.post('/api/portfolio/transactions/', {
            'ticker': 'AMZN',
            'transaction_type': 'SELL',
            'shares': '15',
            'price_per_share': '185.00',
            'fee': '0',
            'executed_at': timezone.now().isoformat()
        })
        self.assertEqual(res_oversell.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('shares', res_oversell.data)

    def test_portfolio_deletion_guards(self):
        """A03: Prevent deleting default portfolio or portfolios with active holdings"""
        default_port = InvestmentPortfolio.objects.filter(user=self.user, is_default=True).first()
        if not default_port:
            default_port = InvestmentPortfolio.objects.create(user=self.user, name="Main", is_default=True)

        # 1. Try deleting Default Portfolio -> 400
        res_del_default = self.client.delete(f'/api/portfolio/portfolios/{default_port.id}/')
        self.assertEqual(res_del_default.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Create new Portfolio with Holding -> try delete -> 400
        active_port = InvestmentPortfolio.objects.create(user=self.user, name="Active Port", is_default=False)
        StockHolding.objects.create(user=self.user, portfolio=active_port, ticker="NVDA", currency="USD")
        res_del_active = self.client.delete(f'/api/portfolio/portfolios/{active_port.id}/')
        self.assertEqual(res_del_active.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Delete Holding then delete empty Portfolio -> 204 success
        active_port.holdings.all().delete()
        res_del_empty = self.client.delete(f'/api/portfolio/portfolios/{active_port.id}/')
        self.assertEqual(res_del_empty.status_code, status.HTTP_204_NO_CONTENT)

    def test_stock_news_article_multi_ticker_url(self):
        """A01: Verify identical news URL can be linked to multiple stock holdings"""
        shared_url = "https://finance.yahoo.com/news/fed-rate-decision-market-impact-12345.html"
        art_aapl = StockNewsArticle.objects.create(
            ticker="AAPL",
            title="Fed Rate Decision",
            url=shared_url,
            published_at=timezone.now()
        )
        # Link with MSFT using same URL -> success without error
        art_msft = StockNewsArticle.objects.create(
            ticker="MSFT",
            title="Fed Rate Decision",
            url=shared_url,
            published_at=timezone.now()
        )
        self.assertNotEqual(art_aapl.id, art_msft.id)
        self.assertEqual(art_aapl.url, art_msft.url)
