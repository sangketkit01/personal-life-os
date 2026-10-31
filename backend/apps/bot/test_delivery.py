from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from asgiref.sync import async_to_sync
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from telegram.error import TimedOut
from .delivery import queue_message, flush_deliveries, preferences, quiet_until
from .models import NotificationDelivery


class NotificationDeliveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='delivery', password='test', telegram_chat_id='777')
        self.bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=42)))

    def test_same_event_is_sent_once(self):
        for _ in range(2):
            async_to_sync(queue_message)(self.bot, self.user, 'bills', 'event:one', text='A bill')
        self.assertEqual(self.bot.send_message.await_count, 1)
        self.assertEqual(NotificationDelivery.objects.get().status, 'SENT')

    def test_disabled_category_does_not_enqueue(self):
        pref = preferences(self.user)
        pref.bills = False
        pref.save()
        async_to_sync(queue_message)(self.bot, self.user, 'bills', 'event:one', text='A bill')
        self.assertFalse(NotificationDelivery.objects.exists())
        self.bot.send_message.assert_not_awaited()

    def test_ambiguous_timeout_is_visible_without_blind_duplicate_retry(self):
        self.bot.send_message.side_effect = TimedOut('Unknown outcome')
        async_to_sync(queue_message)(self.bot, self.user, 'bills', 'event:one', text='A bill')
        async_to_sync(flush_deliveries)(self.bot)
        self.assertEqual(self.bot.send_message.await_count, 1)
        self.assertEqual(NotificationDelivery.objects.get().status, 'UNKNOWN')

    def test_quiet_hours_cross_midnight(self):
        pref = preferences(self.user)
        pref.quiet_start, pref.quiet_end = time(22), time(7)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime(2026, 10, 30, 23, tzinfo=ZoneInfo('Asia/Bangkok'))
        result = quiet_until(pref, now)
        self.assertEqual(result.date(), now.date()+timedelta(days=1))
        self.assertEqual(result.hour, 7)

    def test_settings_validate_timezone_quiet_hours_and_owner(self):
        client = APIClient()
        client.force_authenticate(self.user)
        self.assertEqual(client.patch('/api/bot/notifications/', {'timezone':'Not/AZone'}, format='json').status_code, 400)
        self.assertEqual(client.patch('/api/bot/notifications/', {'quiet_start':'22:00'}, format='json').status_code, 400)
        self.assertEqual(client.patch('/api/bot/notifications/', {'quiet_start':'22:00','quiet_end':'07:00','market_close':True}, format='json').status_code, 200)
        other = get_user_model().objects.create_user(username='delivery-other', password='test')
        client.force_authenticate(other)
        data = client.get('/api/bot/notifications/').data
        self.assertFalse(data['preferences']['market_close'])
        self.assertEqual(data['deliveries'], [])

    def test_completed_bill_is_skipped_after_quiet_hours(self):
        from apps.finance.models import FinancialObligation
        ob = FinancialObligation.objects.create(user=self.user, title='Bill', type='SUBSCRIPTION', amount=100, due_date=timezone.localdate())
        row = NotificationDelivery.objects.create(user=self.user, category='bills', event_key='bill:delayed', payload={'text':'A bill'}, reference={'obligation_id':str(ob.id)}, available_at=timezone.now()-timedelta(seconds=1))
        ob.status = 'CANCELLED'
        ob.save()
        async_to_sync(flush_deliveries)(self.bot)
        row.refresh_from_db()
        self.assertEqual(row.status, 'SKIPPED')
        self.bot.send_message.assert_not_awaited()

    def test_scheduler_lease_blocks_overlapping_workers_and_releases(self):
        from .leases import job_lease
        with job_lease('test-lease') as first:
            self.assertTrue(first)
            with job_lease('test-lease') as second:
                self.assertFalse(second)
        with job_lease('test-lease') as again:
            self.assertTrue(again)

    def test_bnpl_alert_uses_statement_not_credit_limit(self):
        from unittest.mock import patch
        from apps.finance.models import FinancialObligation
        from .dispatcher import send_alert_for_obligation
        ob = FinancialObligation.objects.create(user=self.user, title='BNPL', type='INSTALLMENT', subtype='BNPL_ACCOUNT', amount=50000, due_date=timezone.localdate())
        strategy = SimpleNamespace(get_summary=lambda _: {'current_statement':{'total_due':1234, 'statement_month':'2026-10'}})
        with patch('apps.bot.dispatcher.ObligationStrategyFactory.get_strategy', return_value=strategy):
            async_to_sync(send_alert_for_obligation)(self.bot, '777', ob)
        text = self.bot.send_message.call_args.kwargs['text']
        self.assertIn('1,234.00', text)
        self.assertNotIn('50,000', text)

    def test_delayed_dynamic_bill_is_rendered_with_current_total(self):
        from apps.finance.models import FinancialObligation
        from apps.finance.strategies.subscription import SubscriptionStrategy
        s = SubscriptionStrategy()
        items = [{'id':'f','name':'Fixed','type':'FIXED','amount':100}, {'id':'d','name':'Usage','type':'DYNAMIC'}]
        cycle = s.update_cycle_draft(s.sync_current_cycle(items, None, timezone.localdate(), 'MONTHLY'), [{'id':'d','amount':25}])
        ob = FinancialObligation.objects.create(user=self.user, title='Utility bill', type='SUBSCRIPTION', amount=100, due_date=timezone.localdate(), metadata={'billing_cycle':'MONTHLY','is_itemized':True,'items':items,'current_cycle':cycle})
        async_to_sync(queue_message)(self.bot, self.user, 'bills', 'delayed-bill', reference={'obligation_id':str(ob.id), 'due_date':ob.due_date.isoformat()}, text='old incomplete amount')
        text = self.bot.send_message.call_args.kwargs['text']
        self.assertIn('125.00', text)
        self.assertNotIn('old incomplete amount', text)

    def test_overdue_bills_are_one_digest_and_catch_up_after_worker_restart(self):
        from unittest.mock import patch
        from datetime import datetime, timezone as dtz
        from apps.finance.models import FinancialObligation
        from .automation import scheduled_notifications
        pref = preferences(self.user)
        pref.briefing = pref.calendar = pref.tasks = pref.infrastructure = False
        pref.save()
        now = datetime(2026, 10, 31, 5, tzinfo=dtz.utc)
        for i in range(6):
            FinancialObligation.objects.create(user=self.user, title=f'Overdue {i}', type='SUBSCRIPTION', amount=100, due_date=now.date()-timedelta(days=2))
        with patch('django.utils.timezone.now', return_value=now), patch('apps.bot.automation.prepare_rules_and_reports'):
            for _ in range(2):
                async_to_sync(scheduled_notifications)(SimpleNamespace(bot=self.bot))
        self.assertEqual(self.bot.send_message.await_count, 1)
        self.assertIn('6', self.bot.send_message.call_args.kwargs['text'])
        self.assertEqual(NotificationDelivery.objects.filter(category='bills').count(), 1)

    def test_portfolio_command_keeps_native_price_currency(self):
        from unittest.mock import patch
        from .handlers.start import portfolio_handler
        update = SimpleNamespace(effective_chat=SimpleNamespace(id=777), message=SimpleNamespace(reply_text=AsyncMock()))
        overview = {'holdings':[{'ticker':'V', 'currency':'USD', 'position':{'is_active':True, 'shares':1, 'current_price':100, 'currency':'USD', 'unrealized_pnl':5}}]}
        with patch('apps.bot.handlers.start.get_user_by_chat_id', AsyncMock(return_value=self.user)), patch('apps.bot.handlers.start.get_user_portfolio_summary', AsyncMock(return_value=overview)), patch('apps.bot.handlers.start._send_typing', AsyncMock()):
            async_to_sync(portfolio_handler)(update, SimpleNamespace())
        text = update.message.reply_text.call_args.args[0]
        self.assertIn('$100.00', text)
        self.assertNotIn('\u0e3f100.00', text)

    def test_bnpl_parent_only_in_daily_brief_and_overdue_digest(self):
        from unittest.mock import patch
        from datetime import datetime, timezone as dtz
        from apps.finance.models import FinancialObligation
        from .automation import scheduled_notifications
        from .dispatcher import get_morning_briefing_data, overdue_data
        p = preferences(self.user)
        p.briefing = p.calendar = p.tasks = p.infrastructure = False
        p.save()
        now = datetime(2026,11,10,5,tzinfo=dtz.utc)
        parent = FinancialObligation.objects.create(user=self.user, title='BNPL parent', type='INSTALLMENT', subtype='BNPL_ACCOUNT', due_date=now.date(), amount=0, metadata={'due_day':10, 'credit_limit':'30000'})
        child = FinancialObligation.objects.create(user=self.user, parent=parent, title='BNPL child', type='INSTALLMENT', subtype='BNPL_ORDER', due_date=now.date(), amount=1000, metadata={'total_terms':3, 'current_term':0, 'order_date':'2026-10-01'})
        with patch('django.utils.timezone.now', return_value=now), patch('apps.bot.automation.prepare_rules_and_reports'):
            async_to_sync(scheduled_notifications)(SimpleNamespace(bot=self.bot))
            self.assertEqual(self.bot.send_message.await_count, 1)
            p.briefing = True
            p.save()
            data = async_to_sync(get_morning_briefing_data)(self.user)
            self.assertEqual([b['id'] for b in data['bills']], [str(parent.id)])
            FinancialObligation.objects.filter(pk__in=[parent.pk,child.pk]).update(due_date=now.date()-timedelta(days=1))
            count, rows = async_to_sync(overdue_data)(self.user, 'bills')
            self.assertEqual(count, 1)
            self.assertEqual(rows[0]['id'], str(parent.id))

    def test_delayed_tasks_skip_moved_deadline_and_render_current_title(self):
        from apps.workspace.models import TaskDocument
        task = TaskDocument.objects.create(user=self.user, title='Old title', deadline=timezone.now()+timedelta(hours=1))
        ref = {'task_id':str(task.id), 'deadline':task.deadline.isoformat()}
        row = NotificationDelivery.objects.create(user=self.user, category='tasks', event_key='task:moved', payload={'text':'Old payload'}, reference=ref, available_at=timezone.now())
        task.deadline += timedelta(days=30)
        task.save()
        async_to_sync(flush_deliveries)(self.bot)
        row.refresh_from_db()
        self.assertEqual(row.status, 'SKIPPED')
        self.bot.send_message.assert_not_awaited()
        task.deadline = timezone.now()+timedelta(hours=1)
        task.title = 'Current title'
        task.save()
        ref['deadline'] = task.deadline.isoformat()
        async_to_sync(queue_message)(self.bot, self.user, 'tasks', 'task:renamed', reference=ref, text='Old payload')
        self.assertIn('Current title', self.bot.send_message.call_args.kwargs['text'])
        self.assertNotIn('Old payload', self.bot.send_message.call_args.kwargs['text'])

    def test_watchdog_discards_resolved_alerts_and_coalesces_pending_state(self):
        from apps.workspace.models import InfrastructureAsset
        from .delivery import _enqueue
        asset = InfrastructureAsset.objects.create(user=self.user, name='Server', watchdog_enabled=True, health_status='ONLINE', last_checked_at=timezone.now(), last_telemetry={'containers':[]})
        ref = {'watchdog_asset_id':str(asset.id), 'recovered':False}
        row = NotificationDelivery.objects.create(user=self.user, category='infrastructure', event_key='watchdog:offline', reference=ref, payload={'text':'Offline'}, available_at=timezone.now())
        async_to_sync(flush_deliveries)(self.bot)
        row.refresh_from_db()
        self.assertEqual(row.status, 'SKIPPED')
        self.bot.send_message.assert_not_awaited()
        old = NotificationDelivery.objects.create(user=self.user, category='infrastructure', event_key='watchdog:old', reference=ref, payload={}, available_at=timezone.now()+timedelta(hours=8))
        async_to_sync(_enqueue)(self.user, 'infrastructure', 'watchdog:recovered', {'text':'Recovered'}, {**ref, 'recovered':True})
        old.refresh_from_db()
        self.assertEqual(old.status, 'SKIPPED')
        async_to_sync(flush_deliveries)(self.bot)
        self.assertEqual(self.bot.send_message.await_count, 1)
        self.assertNotIn('Offline', self.bot.send_message.call_args.kwargs['text'])

    def test_infrastructure_opt_out_removes_briefing_section(self):
        from apps.workspace.models import InfrastructureAsset
        from .dispatcher import get_morning_briefing_data
        InfrastructureAsset.objects.create(user=self.user, name='Server', health_status='OFFLINE')
        p = preferences(self.user)
        p.infrastructure = False
        p.save()
        data = async_to_sync(get_morning_briefing_data)(self.user)
        self.assertEqual(data['infra'], {})

    def test_quiet_hours_change_releases_queue_but_keeps_rate_limit_backoff(self):
        client = APIClient()
        client.force_authenticate(self.user)
        now = timezone.now()
        waiting = NotificationDelivery.objects.create(user=self.user, category='bills', event_key='quiet:waiting', payload={'text':'Waiting'}, available_at=now+timedelta(hours=8))
        backoff = NotificationDelivery.objects.create(user=self.user, category='bills', event_key='quiet:backoff', payload={'text':'Backoff'}, available_at=now+timedelta(hours=8), retry_not_before=now+timedelta(minutes=10), attempts=1)
        response = client.patch('/api/bot/notifications/', {'quiet_start':None, 'quiet_end':None}, format='json')
        self.assertEqual(response.status_code, 200)
        waiting.refresh_from_db()
        backoff.refresh_from_db()
        self.assertLessEqual(waiting.available_at, timezone.now())
        self.assertEqual(backoff.available_at, backoff.retry_not_before)
        async_to_sync(flush_deliveries)(self.bot)
        self.assertEqual(self.bot.send_message.await_count, 1)

    def test_long_news_preserves_content_and_markdown_within_telegram_limits(self):
        from unittest.mock import patch
        from apps.portfolio.models import StockNewsArticle
        from .handlers.start import news_handler
        from .message_chunks import telegram_length, split_plain_text
        from .markdown_utils import escape_md
        summary = ('Long_text [with] *markup* \U0001F4B0 '*180)
        self.assertEqual(''.join(split_plain_text(summary)), summary)
        for i in range(4):
            StockNewsArticle.objects.create(ticker='V', title=f'Visa earnings {i}', summary=summary, url=f'https://example.test/news/{i}', source='Proof', published_at=timezone.now(), relevance='ACCEPTED')
        update = SimpleNamespace(effective_chat=SimpleNamespace(id=777), message=SimpleNamespace(reply_text=AsyncMock()))
        with patch('apps.bot.handlers.start.get_user_by_chat_id', AsyncMock(return_value=self.user)), patch('apps.bot.handlers.start._send_typing', AsyncMock()):
            async_to_sync(news_handler)(update, SimpleNamespace(args=['V']))
        texts = [call.args[0] for call in update.message.reply_text.call_args_list]
        self.assertGreater(len(texts), 1)
        self.assertTrue(all(telegram_length(text) <= 4096 for text in texts))
        all_text = '\n'.join(texts)
        for chunk in split_plain_text(summary):
            self.assertEqual(all_text.count('_'+escape_md(chunk)+'_'), 4 * list(split_plain_text(summary)).count(chunk))
