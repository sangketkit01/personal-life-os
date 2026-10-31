from datetime import datetime, timedelta, timezone as dtz
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.bot.models import NotificationDelivery
from .models import InvestmentPortfolio, StockHolding, StockTransaction, StockPriceSnapshot, StockWatchlist, PriceAlert
from .identity import classify_news, revalidate_stored_news
from .quotes import tracked_tickers, quote_metadata
from .services import fetch_and_cache_market_prices
from .exchange_sessions import session, regular_session_open
from .automation import evaluate_price_alerts, build_close_report


class PortfolioAutomationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='automation', password='test')
        self.user.telegram_chat_id = '12345'
        self.user.save()
        self.other = get_user_model().objects.create_user(username='other-automation', password='test')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.portfolio = InvestmentPortfolio.objects.create(user=self.user, name='Main', currency='USD', is_default=True)

    def holding(self, ticker='V'):
        return StockHolding.objects.create(user=self.user, portfolio=self.portfolio, ticker=ticker, name='Visa Inc.', currency='USD')

    def trade(self, holding, kind, shares, price, at, fee=0):
        return StockTransaction.objects.create(user=self.user, holding=holding, transaction_type=kind,
            shares=shares, price_per_share=price, currency='USD', executed_at=at, fee=fee)

    def test_exchange_holidays_early_close_and_dst(self):
        self.assertIsNone(session('US', '2026-07-03'))
        self.assertIsNone(session('SET', '2026-01-01'))
        self.assertEqual(session('US', '2026-11-27')['close'].hour, 18)
        self.assertEqual(session('US', '2026-03-09')['open'].hour, 13)
        self.assertEqual(session('US', '2026-11-02')['open'].hour, 14)
        self.assertFalse(regular_session_open('US', datetime(2026, 7, 3, 15, tzinfo=dtz.utc)))

    def test_shared_ticker_union_excludes_closed_historical_positions(self):
        now = timezone.now()
        active = self.holding()
        self.trade(active, 'BUY', 1, 100, now-timedelta(days=30))
        old = self.holding('OLD')
        self.trade(old, 'BUY', 1, 100, now-timedelta(days=90))
        self.trade(old, 'SELL', 1, 100, now-timedelta(days=60))
        StockWatchlist.objects.create(user=self.user, ticker='NVDA', name='Nvidia', currency='USD')
        StockWatchlist.objects.create(user=self.other, ticker='V', name='Visa', currency='USD')
        self.assertEqual(tracked_tickers(), ['NVDA', 'USDTHB=X', 'V'])

    def test_quote_failure_keeps_good_price_and_does_not_advance_success_time(self):
        row = StockPriceSnapshot.objects.create(ticker='V', price=100, currency='USD', quote_at=timezone.now())
        before = row.fetched_at
        with patch('apps.portfolio.services._fetch_single_yf_quote', return_value=None):
            result = fetch_and_cache_market_prices(['V'], force=True)
        row.refresh_from_db()
        self.assertEqual(result['V'], Decimal('100'))
        self.assertEqual(row.fetched_at, before)
        self.assertTrue(row.last_error)
        self.assertEqual(quote_metadata(row)['state'], 'STALE')

    def test_provider_adapter_reads_real_timestamp_and_company_metadata(self):
        from .services import _fetch_single_yf_quote
        stamp = int(timezone.now().timestamp())
        with patch('yfinance.Ticker', autospec=True) as ticker:
            ticker.return_value.fast_info = {}
            ticker.return_value.get_info.return_value = {'regularMarketPrice':100, 'regularMarketTime':stamp,
                'regularMarketPreviousClose':95, 'currency':'USD', 'longName':'Visa Inc.', 'exchange':'NYQ'}
            result = _fetch_single_yf_quote('V')
            ticker.return_value.get_info.assert_called_once_with()
        self.assertEqual(int(result['quote_at'].timestamp()), stamp)
        self.assertEqual(result['asset_name'], 'Visa Inc.')
        self.assertEqual(result['price'], Decimal('100'))

    def test_ambiguous_news_is_not_visa_and_valid_visa_news_survives(self):
        self.assertNotEqual(classify_news('V', 'Juno V launches an industrial project')[0], 'ACCEPTED')
        self.assertNotEqual(classify_news('V', 'Travel visa application guide')[0], 'ACCEPTED')
        self.assertNotEqual(classify_news('V', 'Travel visa application agency revenue grows')[0], 'ACCEPTED')
        self.assertNotEqual(classify_news('V', 'Juno V revenue grows', related_tickers=['V'])[0], 'ACCEPTED')
        self.assertEqual(classify_news('V', 'Visa earnings rise as card payments grow')[0], 'ACCEPTED')

    def test_company_aliases_preserve_real_news_and_travel_payments_are_not_visa(self):
        for title in ('UK visa application payments boost embassy revenue', 'Tourist visa fees and card payments rise'):
            self.assertNotEqual(classify_news('V', title, related_tickers=['V'])[0], 'ACCEPTED')
        for ticker, title in [('AMD', 'AMD revenue and earnings beat estimates'),
                              ('GOOGL', 'Google revenue and earnings beat estimates'),
                              ('META', 'Meta earnings and revenue rise'), ('AMZN', 'Amazon earnings rise')]:
            self.assertEqual(classify_news(ticker, title, related_tickers=[ticker])[0], 'ACCEPTED')
        self.assertEqual(classify_news('V', 'Visa Inc. reports growth in travel card payments')[0], 'ACCEPTED')

    def test_unknown_news_recovers_with_company_metadata_and_does_not_starve_pending(self):
        from .models import StockNewsArticle
        old = StockNewsArticle.objects.create(ticker='AUDITNEW', title='Example Systems earnings rise',
            url='https://example.test/recovery', published_at=timezone.now(), relevance='UNKNOWN')
        revalidate_stored_news()
        old.refresh_from_db()
        self.assertEqual(old.relevance, 'UNKNOWN')
        StockPriceSnapshot.objects.create(ticker='AUDITNEW', price=100, currency='USD', asset_name='Example Systems Inc.')
        StockNewsArticle.objects.filter(pk=old.pk).update(relevance_checked_at=timezone.now()-timedelta(hours=2))
        revalidate_stored_news()
        old.refresh_from_db()
        self.assertEqual(old.relevance, 'ACCEPTED')

    def test_ingestion_rechecks_existing_unknown_article_without_duplicate(self):
        from .news_service import ingest_news_for_ticker
        from .models import StockNewsArticle
        row = StockNewsArticle.objects.create(ticker='AMD', title='AMD earnings rise', url='https://example.test/amd',
            published_at=timezone.now(), relevance='UNKNOWN', canonical_url='https://example.test/amd')
        raw = {'title':row.title, 'url':row.url, 'source':'Proof', 'published_at':row.published_at, 'related_tickers':['AMD']}
        with patch('apps.portfolio.news_service.fetch_from_yahoo_finance', return_value=[raw]), patch('apps.portfolio.news_service.fetch_from_google_news', return_value=[]), patch('apps.portfolio.news_service.scrape_article_content', return_value={'lead':'AMD earnings rise', 'full_text':''}), patch('apps.portfolio.news_service.translate_and_enrich_article', return_value={'title_th':'Translated'}) as translate:
            self.assertEqual(ingest_news_for_ticker('AMD'), 1)
            self.assertEqual(ingest_news_for_ticker('AMD'), 0)
        row.refresh_from_db()
        self.assertEqual(row.relevance, 'ACCEPTED')
        self.assertEqual(StockNewsArticle.objects.filter(ticker='AMD').count(), 1)
        translate.assert_called_once()

    def test_set_lunch_and_preopen_never_trigger_rule_and_afternoon_resumes(self):
        from .market_hours import get_set_market_status
        from zoneinfo import ZoneInfo
        now = datetime(2026, 10, 30, 5, 31, tzinfo=dtz.utc)
        StockPriceSnapshot.objects.create(ticker='PTT.BK', price=30, currency='THB', quote_at=now-timedelta(minutes=2), regular_quote_at=now-timedelta(minutes=2))
        StockPriceSnapshot.objects.filter(ticker='PTT.BK').update(fetched_at=now)
        rule = PriceAlert.objects.create(user=self.user, ticker='PTT.BK', currency='THB', condition='GTE', target_price=29)
        evaluate_price_alerts(now)
        rule.refresh_from_db()
        self.assertIsNone(rule.triggered_at)
        self.assertEqual(quote_metadata(StockPriceSnapshot.objects.get(ticker='PTT.BK'), now)['state'], 'CLOSED')
        for hour, minute, is_regular, label in [(12,31,False,'Lunch Break'), (13,45,False,'Afternoon Pre-Open'), (14,1,True,'Afternoon Trading')]:
            local = datetime(2026,10,30,hour,minute,tzinfo=ZoneInfo('Asia/Bangkok'))
            self.assertEqual(regular_session_open('SET', local), is_regular)
            self.assertEqual(get_set_market_status(local)['session'], label)

    def test_watchlist_missing_quote_remains_unknown_instead_of_zero(self):
        StockWatchlist.objects.create(user=self.user, ticker='V', name='Visa', currency='USD')
        response = self.client.get('/api/portfolio/watchlist/')
        self.assertEqual(response.status_code, 200)
        rows = response.data.get('results', []) if isinstance(response.data, dict) else response.data
        self.assertIsNone(rows[0]['current_price'])
        self.assertIsNone(rows[0]['change_pct'])
        self.assertEqual(rows[0]['quote']['state'], 'MISSING')

    def test_price_alert_requires_fresh_quote_native_currency_and_is_one_shot(self):
        now = datetime(2026, 10, 30, 15, 0, tzinfo=dtz.utc)
        row = StockPriceSnapshot.objects.create(ticker='V', price=110, currency='USD', quote_at=now, regular_quote_at=now)
        StockPriceSnapshot.objects.filter(pk='V').update(fetched_at=now)
        rule = PriceAlert.objects.create(user=self.user, ticker='V', currency='USD', condition='GTE', target_price=105)
        evaluate_price_alerts(now)
        evaluate_price_alerts(now)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)
        self.assertEqual(NotificationDelivery.objects.filter(user=self.user).count(), 1)
        rule.is_active = True
        rule.revision = __import__('uuid').uuid4()
        rule.save()
        evaluate_price_alerts(now+timedelta(minutes=10))
        self.assertEqual(NotificationDelivery.objects.filter(user=self.user).count(), 1)

    def test_alert_crud_owner_isolation_and_rearm(self):
        created = self.client.post('/api/portfolio/price-alerts/', {'ticker':'V', 'currency':'USD', 'condition':'GTE', 'target_price':'105'}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data['id']
        listed = self.client.get('/api/portfolio/price-alerts/', {'ticker': 'V'})
        self.assertEqual(listed.status_code, 200)
        self.assertIsInstance(listed.data, list)
        self.assertEqual([row['id'] for row in listed.data], [pk])
        rule = PriceAlert.objects.get(pk=pk)
        previous = rule.revision
        self.assertEqual(self.client.patch(f'/api/portfolio/price-alerts/{pk}/', {'target_price':'120'}, format='json').status_code, 200)
        rule.refresh_from_db()
        self.assertNotEqual(rule.revision, previous)
        previous = rule.revision
        self.client.patch(f'/api/portfolio/price-alerts/{pk}/', {'target_price':'120'}, format='json')
        rule.refresh_from_db()
        self.assertEqual(rule.revision, previous)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.patch(f'/api/portfolio/price-alerts/{pk}/', {'is_active':False}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/portfolio/price-alerts/{pk}/').status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f'/api/portfolio/price-alerts/{pk}/').status_code, 204)

    def test_intraday_buy_sell_fees_and_dividend_do_not_fake_daily_gain(self):
        closed = session('US', '2026-10-30')
        holding = self.holding()
        self.trade(holding, 'BUY', 10, 80, closed['previous_close']-timedelta(days=1))
        self.trade(holding, 'BUY', 5, 105, closed['open']+timedelta(minutes=5), fee=1)
        self.trade(holding, 'SELL', 2, 108, closed['open']+timedelta(minutes=10), fee=1)
        self.trade(holding, 'DIVIDEND', 10, 1, closed['open']+timedelta(minutes=15))
        StockPriceSnapshot.objects.create(ticker='V', price=110, regular_price=110, previous_close=100,
            currency='USD', regular_quote_at=closed['close'], quote_at=closed['close'])
        report = build_close_report(self.user, 'US', closed, closed['close']+timedelta(minutes=20))
        # 13*110 - 10*100 - (5*105+1) + (2*108-1) + 10 = 129
        self.assertEqual(Decimal(report['daily_pnl']), Decimal('129'))
        self.assertEqual(Decimal(report['market_value']), Decimal('1430'))

    def test_missing_closing_quote_does_not_fabricate_daily_return(self):
        closed = session('US', '2026-10-30')
        holding = self.holding()
        self.trade(holding, 'BUY', 1, 100, closed['previous_close']-timedelta(days=1))
        StockPriceSnapshot.objects.create(ticker='V', price=100, currency='USD', regular_quote_at=closed['open'])
        self.assertIsNone(build_close_report(self.user, 'US', closed, closed['close']+timedelta(minutes=20)))
        result = build_close_report(self.user, 'US', closed, closed['close']+timedelta(hours=3))
        self.assertIsNone(result['daily_pnl'])
        self.assertEqual(result['missing'], ['V'])

    def test_background_job_updates_shared_assets_without_any_page_request(self):
        from .quotes import sync_tracked_prices
        active = self.holding()
        self.trade(active, 'BUY', 1, 100, timezone.now()-timedelta(days=30))
        StockWatchlist.objects.create(user=self.other, ticker='V', name='Visa', currency='USD')
        StockWatchlist.objects.create(user=self.user, ticker='NVDA', name='Nvidia', currency='USD')
        stamp = timezone.now()
        def quote(ticker):
            return {'ticker':ticker, 'price':Decimal('120'), 'currency':'THB' if ticker == 'USDTHB=X' else 'USD', 'quote_at':stamp, 'regular_quote_at':stamp}
        with patch('apps.portfolio.services._fetch_single_yf_quote', side_effect=quote) as provider:
            result = sync_tracked_prices()
        self.assertEqual(sorted(call.args[0] for call in provider.call_args_list), ['NVDA', 'USDTHB=X', 'V'])
        self.assertEqual(result['failed'], [])
        self.assertEqual(StockPriceSnapshot.objects.get(ticker='V').price, Decimal('120'))

    def test_close_report_and_notification_are_persisted_once(self):
        from apps.bot.delivery import preferences
        from .models import MarketCloseReport
        from .automation import prepare_close_reports
        pref = preferences(self.user)
        pref.market_close = True
        pref.save()
        closed = session('US', '2026-10-30')
        holding = self.holding()
        self.trade(holding, 'BUY', 1, 100, closed['previous_close']-timedelta(days=1))
        StockPriceSnapshot.objects.create(ticker='V', price=110, regular_price=110, previous_close=100, currency='USD', regular_quote_at=closed['close'])
        for _ in range(2):
            prepare_close_reports(closed['close']+timedelta(minutes=20))
        self.assertEqual(MarketCloseReport.objects.filter(user=self.user, market='US').count(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(user=self.user, category='market_close').count(), 1)

    def test_unknown_and_old_mislabeled_news_are_quarantined_before_bot_or_web(self):
        from .models import StockNewsArticle
        article = StockNewsArticle.objects.create(ticker='V', title='Juno V announces a project', url='https://example.test/juno', published_at=timezone.now())
        revalidate_stored_news()
        article.refresh_from_db()
        self.assertNotEqual(article.relevance, 'ACCEPTED')
        response = self.client.get('/api/portfolio/news/')
        self.assertEqual(response.data['count'], 0)

    def test_wrong_company_is_not_translated_or_published_on_ingestion(self):
        from .news_service import ingest_news_for_ticker
        from .models import StockNewsArticle
        raw = {'title':'Juno V announces a project', 'url':'https://example.test/juno', 'source':'Example', 'published_at':timezone.now()}
        with patch('apps.portfolio.news_service.fetch_from_yahoo_finance', return_value=[raw]), patch('apps.portfolio.news_service.fetch_from_google_news', return_value=[]), patch('apps.portfolio.news_service.scrape_article_content', return_value={'lead':'', 'full_text':''}), patch('apps.portfolio.news_service.translate_and_enrich_article') as ai:
            self.assertEqual(ingest_news_for_ticker('V'), 0)
        ai.assert_not_called()
        self.assertFalse(StockNewsArticle.objects.filter(ticker='V', relevance='ACCEPTED').exists())
