from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.bot.handlers.start import pair_user_by_token, get_user_by_chat_id, get_user_portfolio_summary
from apps.bot.handlers.callbacks import process_pay_callback, process_cancel_trial_callback
from apps.bot.handlers.messages import parse_quick_text
from apps.finance.models import FinancialObligation, ObligationType, ObligationStatus
from apps.portfolio.models import StockHolding, StockTransaction, TransactionType

User = get_user_model()


class TelegramBotTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bot_tester',
            email='bot@test.com',
            password='Password123!'
        )
        self.user.telegram_connect_token = 'TEST_PAIR_TOKEN_99'
        self.user.save()

    async def test_pairing_by_token(self):
        """Test pairing Chat ID using One-Time Token."""
        paired_user = await pair_user_by_token('TEST_PAIR_TOKEN_99', 123456789)
        self.assertIsNotNone(paired_user)
        self.assertEqual(paired_user.telegram_chat_id, '123456789')
        self.assertIsNone(paired_user.telegram_connect_token)

        # Test lookup by chat_id
        found_user = await get_user_by_chat_id(123456789)
        self.assertEqual(found_user.id, self.user.id)

    def test_parse_quick_text_patterns(self):
        """Test parsing user text for Quick-Capture feature."""
        # 1. Installment
        p1 = parse_quick_text('installment tiktok 450 3 terms')
        self.assertIsNotNone(p1)
        self.assertEqual(p1['type'], ObligationType.INSTALLMENT)
        self.assertEqual(p1['amount'], Decimal('450'))
        self.assertEqual(p1['metadata']['total_terms'], 3)

        # 2. Free Trial
        p2 = parse_quick_text('trial canva 499 email work@gmail.com')
        self.assertIsNotNone(p2)
        self.assertEqual(p2['type'], ObligationType.FREE_TRIAL)
        self.assertEqual(p2['amount'], Decimal('499'))
        self.assertEqual(p2['metadata']['account_email'], 'work@gmail.com')

        # 3. Subscription
        p3 = parse_quick_text('sub netflix 419')
        self.assertIsNotNone(p3)
        self.assertEqual(p3['type'], ObligationType.SUBSCRIPTION)
        self.assertEqual(p3['amount'], Decimal('419'))

        # 4. Debt
        p4 = parse_quick_text('debt John 500')
        self.assertIsNotNone(p4)
        self.assertEqual(p4['type'], ObligationType.DEBT)
        self.assertEqual(p4['amount'], Decimal('500'))
        self.assertEqual(p4['metadata']['counterparty'], 'John')

    async def test_callback_pay_installment(self):
        """Test clicking [Paid] action button from Telegram."""
        self.user.telegram_chat_id = '999888'
        await self.user.asave()

        moto = await FinancialObligation.objects.acreate(
            user=self.user,
            title='Motorcycle Installment',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            metadata={'total_terms': 36, 'current_term': 14}
        )

        res = await process_pay_callback(str(moto.id), 999888)
        self.assertTrue(res['success'])
        self.assertEqual(res['summary']['current_term'], 15)

    async def test_callback_cancel_trial(self):
        """Test clicking [Mark Cancelled] button from Telegram."""
        self.user.telegram_chat_id = '999888'
        await self.user.asave()

        trial = await FinancialObligation.objects.acreate(
            user=self.user,
            title='Adobe Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('600.00'),
            metadata={'auto_renew_cost': 600.0}
        )

        res = await process_cancel_trial_callback(str(trial.id), 999888)
        self.assertTrue(res['success'])
        updated = await FinancialObligation.objects.aget(id=trial.id)
        self.assertEqual(updated.status, ObligationStatus.CANCELLED)

    async def test_portfolio_summary_for_bot(self):
        """Test retrieving portfolio summary for Telegram bot."""
        holding = await StockHolding.objects.acreate(
            user=self.user,
            ticker='PTT.BK',
            name='PTT Public Company Limited'
        )
        await StockTransaction.objects.acreate(
            holding=holding,
            user=self.user,
            transaction_type=TransactionType.BUY,
            shares=Decimal('100'),
            price_per_share=Decimal('35.00'),
            fee=Decimal('0.00'),
            executed_at=timezone.now()
        )

        overview = await get_user_portfolio_summary(self.user)
        self.assertEqual(float(overview['total_market_value']), 3500.0)
        self.assertEqual(overview['active_assets_count'], 1)
        self.assertEqual(overview['holdings'][0]['ticker'], 'PTT.BK')


# ---------------------------------------------------------------------------
# Round 3: Kanban alert coverage, Markdown escaping, duplicate pay lock,
# VPS watchdog evaluation/cooldown, MA expiry notices, probe callback
# ---------------------------------------------------------------------------
from unittest.mock import patch

from apps.bot.dispatcher import (
    get_due_tasks_for_user,
    evaluate_watchdog_breaches,
    scan_watchdog_assets,
    get_expiring_items_for_user,
)
from apps.bot.handlers.callbacks import process_pay_callback, process_probe_vps_callback
from apps.bot.markdown_utils import escape_md
from apps.finance.models import PaymentHistory
from apps.workspace.models import WorkspaceProject, ProjectType, InfrastructureAsset, TaskDocument


async def _amk_asset(user, project, **kwargs):
    defaults = dict(
        user=user, project=project, name='watch-box',
        ip_address='198.51.100.9', ssh_port=22,
        watchdog_enabled=True,
        health_status='UNKNOWN',
    )
    defaults.update(kwargs)
    return await InfrastructureAsset.objects.acreate(**defaults)


def _mk_asset(user, project, **kwargs):
    defaults = dict(
        user=user, project=project, name='watch-box',
        ip_address='198.51.100.9', ssh_port=22,
        watchdog_enabled=True,
        health_status='UNKNOWN',
    )
    defaults.update(kwargs)
    return InfrastructureAsset.objects.create(**defaults)


class KanbanAlertCoverageTests(TelegramBotTestCase):

    async def test_todo_and_doing_tasks_alerted_done_skipped(self):
        project = await WorkspaceProject.objects.acreate(user=self.user, name='Alert Proj')
        base = {
            'user': self.user, 'project': project,
            'deadline': timezone.now(),
        }
        await TaskDocument.objects.acreate(title='Todo task', status='TODO', **base)
        await TaskDocument.objects.acreate(title='Doing task', status='DOING', **base)
        await TaskDocument.objects.acreate(title='Done task', status='DONE', **base)
        # Legacy status string stored in an old row
        await TaskDocument.objects.acreate(title='Legacy drafting', status='DRAFTING', **base)

        tasks = await get_due_tasks_for_user(self.user)
        titles = {t.title for t in tasks}
        self.assertIn('Todo task', titles)
        self.assertIn('Doing task', titles)
        self.assertIn('Legacy drafting', titles)
        self.assertNotIn('Done task', titles)


class MarkdownEscapeTests(TelegramBotTestCase):

    def test_special_characters_escaped(self):
        raw = "hello_world [link] *bold* `code` and_plain"
        escaped = escape_md(raw)
        self.assertNotIn('_world', escaped.replace('\\_world', ''))
        self.assertIn('\\_', escaped)
        self.assertIn('\\*', escaped)
        self.assertIn('\\`', escaped)
        self.assertIn('\\[', escaped)
        # Backslash escapes render back the same text in Telegram
        self.assertEqual(escaped.replace('\\', ''), raw)

    def test_plain_text_untouched_and_none_safe(self):
        self.assertEqual(escape_md('plain text 123'), 'plain text 123')
        self.assertEqual(escape_md(None), '')


class DuplicatePayGuardTests(TelegramBotTestCase):

    async def test_double_click_same_day_rejected(self):
        self.user.telegram_chat_id = '777001'
        await self.user.asave()

        sub = await FinancialObligation.objects.acreate(
            user=self.user,
            title='Netflix',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('419.00'),
            due_date=timezone.localdate(),
            metadata={'billing_cycle': 'MONTHLY'}
        )

        from apps.finance.strategies.subscription import SubscriptionStrategy
        ck = SubscriptionStrategy.get_cycle_key(sub.due_date, 'MONTHLY')
        first = await process_pay_callback(f"{sub.id}:{ck}", 777001)
        self.assertTrue(first['success'])

        # Simulates tapping the button on the OLD Telegram message again
        second = await process_pay_callback(f"{sub.id}:{ck}", 777001)
        self.assertFalse(second['success'])
        self.assertTrue(second.get('duplicate'))
        self.assertEqual(await PaymentHistory.objects.filter(obligation=sub).acount(), 1)


class WatchdogEvaluationTests(TelegramBotTestCase):

    def _asset(self, **kwargs):
        project = WorkspaceProject.objects.create(user=self.user, name='WD Proj')
        return _mk_asset(self.user, project, **kwargs)

    def test_offline_error_maps_to_offline_breach(self):
        asset = self._asset()
        breaches = evaluate_watchdog_breaches(asset, {'error': 'ssh timeout', 'containers': []})
        self.assertEqual(breaches, [{'kind': 'offline'}])

    def test_threshold_breaches_detected(self):
        asset = self._asset(alert_cpu_threshold=90, alert_ram_threshold=85, alert_disk_threshold=80)
        telemetry = {
            'error': None, 'cpu_pct': 95.5, 'ram_pct': 88.0, 'disk_pct': 70.0,
            'containers': [{'Names': 'web', 'State': 'running'}],
        }
        breaches = evaluate_watchdog_breaches(asset, telemetry)
        kinds = {b['kind'] for b in breaches}
        self.assertEqual(kinds, {'cpu', 'ram'})

    def test_exited_container_flagged(self):
        asset = self._asset()
        telemetry = {
            'error': None, 'cpu_pct': 10.0, 'ram_pct': 30.0, 'disk_pct': 40.0,
            'containers': [
                {'Names': 'web', 'State': 'running'},
                {'Names': 'worker', 'State': 'exited', 'Status': 'Exited (0) 3 minutes ago'},
            ],
        }
        breaches = evaluate_watchdog_breaches(asset, telemetry)
        container_breaches = [b for b in breaches if b['kind'] == 'container']
        self.assertEqual(len(container_breaches), 1)
        self.assertEqual(container_breaches[0]['name'], 'worker')

    def test_healthy_server_no_breaches(self):
        asset = self._asset()
        telemetry = {
            'error': None, 'cpu_pct': 5.0, 'ram_pct': 20.0, 'disk_pct': 30.0,
            'containers': [{'Names': 'web', 'State': 'running'}],
        }
        self.assertEqual(evaluate_watchdog_breaches(asset, telemetry), [])


class WatchdogScanCooldownTests(TransactionTestCase):
    """Probe threads need committed fixture rows (no wrapped transaction)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='wd_owner', email='wd_owner@test.com', password='Password123!'
        )


    async def test_alert_fires_once_then_cooldown_then_recovery_bypass(self):
        self.user.telegram_chat_id = '777002'
        await self.user.asave()
        project = await WorkspaceProject.objects.acreate(user=self.user, name='Scan Proj')

        telemetry_seq = [
            # 1st sweep: CPU breach -> alert
            {'error': None, 'cpu_pct': 99.0, 'ram_pct': 40.0, 'disk_pct': 30.0, 'containers': []},
            # 2nd sweep (within cooldown): same breach -> suppressed
            {'error': None, 'cpu_pct': 99.0, 'ram_pct': 40.0, 'disk_pct': 30.0, 'containers': []},
            # 3rd sweep: healthy again (recovered is False - never went OFFLINE) -> no alert
            {'error': None, 'cpu_pct': 10.0, 'ram_pct': 30.0, 'disk_pct': 25.0, 'containers': []},
        ]
        asset = await _amk_asset(self.user, project, name='scan-box', health_status='ONLINE')

        with patch('apps.workspace.ssh_service.probe_server_telemetry') as mock_probe:
            def probe(a):
                telemetry = telemetry_seq.pop(0)
                a.health_status = 'WARNING' if telemetry['cpu_pct'] >= a.alert_cpu_threshold else 'ONLINE'
                a.last_telemetry = telemetry
                a.last_checked_at = timezone.now()
                a.save(update_fields=['health_status', 'last_telemetry', 'last_checked_at', 'updated_at'])
                return telemetry

            mock_probe.side_effect = probe

            first = await scan_watchdog_assets()
            self.assertEqual(len(first), 1)
            self.assertTrue(first[0]['breaches'])
            self.assertFalse(first[0]['recovered'])

            second = await scan_watchdog_assets()
            self.assertEqual(len(second), 0)  # cooldown suppresses repeat

            third = await scan_watchdog_assets()
            self.assertEqual(len(third), 0)  # healthy, no alert

        refreshed = await InfrastructureAsset.objects.aget(id=asset.id)
        self.assertIsNotNone(refreshed.last_alerted_at)

    async def test_offline_to_online_sends_recovery_bypassing_cooldown(self):
        self.user.telegram_chat_id = '777003'
        await self.user.asave()
        project = await WorkspaceProject.objects.acreate(user=self.user, name='Recover Proj')
        asset = await _amk_asset(self.user, project, name='recover-box', health_status='OFFLINE')

        healthy = {'error': None, 'cpu_pct': 8.0, 'ram_pct': 20.0, 'disk_pct': 30.0, 'containers': []}

        with patch('apps.workspace.ssh_service.probe_server_telemetry') as mock_probe:
            def probe(a):
                a.health_status = 'ONLINE'
                a.last_telemetry = healthy
                a.last_checked_at = timezone.now()
                a.save(update_fields=['health_status', 'last_telemetry', 'last_checked_at', 'updated_at'])
                return healthy

            mock_probe.side_effect = probe
            alerts = await scan_watchdog_assets()

        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0]['recovered'])
        self.assertEqual(alerts[0]['breaches'], [])


class MAExpiryNoticeTests(TelegramBotTestCase):

    async def test_notice_day_matching(self):
        today = timezone.localdate()
        await WorkspaceProject.objects.acreate(
            user=self.user, name='Expiring MA',
            project_type=ProjectType.MA_CONTRACT,
            ma_end_date=today + timezone.timedelta(days=7),
        )
        await WorkspaceProject.objects.acreate(
            user=self.user, name='Not Notice Day',
            project_type=ProjectType.MA_CONTRACT,
            ma_end_date=today + timezone.timedelta(days=10),
        )
        await WorkspaceProject.objects.acreate(
            user=self.user, name='Internal Not MA',
            project_type=ProjectType.INTERNAL,
            ma_end_date=today,
        )

        ma_projects, expiring_assets = await get_expiring_items_for_user(self.user)
        names = {p.name for p in ma_projects}
        self.assertEqual(names, {'Expiring MA'})
        self.assertEqual(expiring_assets, [])

    async def test_asset_domain_expiry_notice(self):
        today = timezone.localdate()
        project = await WorkspaceProject.objects.acreate(user=self.user, name='Domain Proj')
        await _amk_asset(self.user, project, name='main-domain', expiry_date=today)

        ma_projects, expiring_assets = await get_expiring_items_for_user(self.user)
        self.assertEqual(len(expiring_assets), 1)
        self.assertEqual(expiring_assets[0].name, 'main-domain')


class ProbeVpsCallbackTests(TelegramBotTestCase):

    async def test_probe_callback_returns_status_text(self):
        self.user.telegram_chat_id = '777004'
        await self.user.asave()
        project = await WorkspaceProject.objects.acreate(user=self.user, name='Probe Proj')
        asset = await _amk_asset(self.user, project, name='probe-box', health_status='UNKNOWN')

        telemetry = {
            'error': None, 'cpu_pct': 12.0, 'ram_pct': 35.0, 'disk_pct': 42.0,
            'ram_used_mb': 560, 'ram_total_mb': 1600,
            'uptime_human': '3d 2h', 'containers': [
                {'Names': 'web', 'State': 'running'},
                {'Names': 'sidecar', 'State': 'exited'},
            ],
        }

        def fake_probe(a):
            a.health_status = 'ONLINE'
            a.last_telemetry = telemetry
            a.last_checked_at = timezone.now()
            a.save(update_fields=['health_status', 'last_telemetry', 'last_checked_at', 'updated_at'])
            return telemetry

        with patch('apps.workspace.ssh_service.probe_server_telemetry', side_effect=fake_probe):
            result = await process_probe_vps_callback(str(asset.id), 777004)

        self.assertTrue(result['success'])
        self.assertIn('probe-box', result['text'])
        self.assertIn('ONLINE', result['text'])
        self.assertIn('1/2 running', result['text'])

    async def test_probe_callback_rejects_foreign_asset(self):
        from django.contrib.auth import get_user_model
        User2 = get_user_model()
        from asgiref.sync import sync_to_async
        other = await sync_to_async(User2.objects.create_user)(
            username='probe_other', email='po@test.com', password='Password123!'
        )
        other.telegram_chat_id = '777005'
        await other.asave()

        project = await WorkspaceProject.objects.acreate(user=other, name='Other Proj')
        asset = await _amk_asset(other, project, name='foreign-box')

        # self.user (different account) tries to probe other's asset
        self.user.telegram_chat_id = '777004'
        await self.user.asave()
        result = await process_probe_vps_callback(str(asset.id), 777004)
        self.assertFalse(result['success'])


# ---------------------------------------------------------------------------
# Deep Audit Round: markdown escaping, language preference, expiry matching,
# idempotent trial cancellation
# ---------------------------------------------------------------------------
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class NewsHandlerRenderingTests(TelegramBotTestCase):
    """Drive news_handler directly with lightweight Update fakes."""

    async def _run_news_handler(self, chat_id, args):
        from apps.bot.handlers.start import news_handler

        captured = []

        async def fake_reply(text, **kwargs):
            captured.append(text)

        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id),
            message=SimpleNamespace(reply_text=fake_reply)
        )
        context = SimpleNamespace(args=args)
        await news_handler(update, context)
        return captured

    async def _make_article(self, **kwargs):
        from apps.portfolio.models import StockNewsArticle
        defaults = dict(
            ticker='ESC_TEST',
            title='Q1_Earnings Report',
            title_th='',
            summary='Margins_beat estimates',
            summary_th='',
            source='Bangkok_Post',
            sentiment='BULLISH',
            url='https://example.com/esc',
            published_at=timezone.now()
        )
        defaults.update(kwargs)
        return await StockNewsArticle.objects.acreate(**defaults)

    async def test_news_handler_escapes_underscores(self):
        self.user.telegram_chat_id = '606001'
        await self.user.asave()
        await self._make_article()

        captured = await self._run_news_handler(606001, args=['ESC_TEST'])
        self.assertTrue(captured)
        text = captured[0]
        self.assertIn('Q1\\_Earnings Report', text)
        self.assertIn('Bangkok\\_Post', text)
        self.assertIn('_Margins\\_beat estimates_', text)
        # No raw unescaped underscore remains
        self.assertNotIn('Q1_Earnings', text)

    async def test_news_handler_prefers_thai_headline(self):
        self.user.preferred_language = 'th'
        self.user.telegram_chat_id = '606002'
        await self.user.asave()
        await self._make_article(
            ticker='TH_TEST',
            title='English headline',
            title_th='Thai headline',
            summary='',
            summary_th='Thai summary'
        )

        captured = await self._run_news_handler(606002, args=['TH_TEST'])
        text = captured[0]
        self.assertIn('Thai headline', text)
        self.assertNotIn('English headline', text)
        self.assertIn('_Thai summary_', text)


class TelegramTestAlertEscapeTests(TelegramBotTestCase):

    def test_test_alert_escapes_underscore_username(self):
        from rest_framework.test import APIClient
        from django.test import override_settings
        from apps.accounts.tokens import generate_access_token

        underscore_user = User.objects.create_user(
            username='under_score_fan',
            email='underscore@test.com',
            password='Password123!'
        )
        underscore_user.telegram_chat_id = '31337'
        underscore_user.save()

        api = APIClient()
        api.cookies['access_token'] = generate_access_token(underscore_user)

        with override_settings(TELEGRAM_BOT_TOKEN='test-token'):
            with patch('telegram.Bot') as mock_bot_cls:
                instance = mock_bot_cls.return_value
                instance.send_message = AsyncMock()
                instance.shutdown = AsyncMock()

                res = api.post('/api/auth/telegram/test/')

        self.assertEqual(res.status_code, 200)
        sent_text = instance.send_message.call_args.kwargs['text']
        self.assertIn('under\\_score\\_fan', sent_text)
        self.assertNotIn('under_score_fan', sent_text.replace('\\_', ''))


class ExpiryIncludesAnyProjectWithFeeTests(TelegramBotTestCase):

    async def test_client_dev_with_fee_gets_expiry_notice(self):
        today = timezone.localdate()
        await WorkspaceProject.objects.acreate(
            user=self.user,
            name='Client Dev With Fee',
            project_type=ProjectType.CLIENT_DEV,
            ma_amount=Decimal('1500.00'),
            ma_end_date=today + timezone.timedelta(days=14)
        )
        # Internal project without any fee stays excluded
        await WorkspaceProject.objects.acreate(
            user=self.user,
            name='Internal No Fee',
            project_type=ProjectType.INTERNAL,
            ma_end_date=today
        )

        ma_projects, expiring_assets = await get_expiring_items_for_user(self.user)
        names = {p.name for p in ma_projects}
        self.assertIn('Client Dev With Fee', names)
        self.assertNotIn('Internal No Fee', names)


class CancelTrialIdempotentTests(TelegramBotTestCase):

    async def test_second_cancel_is_idempotent(self):
        self.user.telegram_chat_id = '999666'
        await self.user.asave()

        trial = await FinancialObligation.objects.acreate(
            user=self.user,
            title='Idempotent Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('300.00'),
            metadata={'auto_renew_cost': 300.0}
        )

        first = await process_cancel_trial_callback(str(trial.id), 999666)
        self.assertTrue(first['success'])
        self.assertFalse(first.get('already_cancelled', False))

        # Tapping the same button on the old message again must not error
        second = await process_cancel_trial_callback(str(trial.id), 999666)
        self.assertTrue(second['success'])
        self.assertTrue(second.get('already_cancelled'))

        await trial.arefresh_from_db()
        self.assertEqual(trial.status, ObligationStatus.CANCELLED)


# ---------------------------------------------------------------------------
# Stage 2: bilingual rendering (/status /help /brief quick-capture),
# briefing infra snapshot, due-today + USD currency rendering
# ---------------------------------------------------------------------------
class StatusLanguageTests(TelegramBotTestCase):

    async def _run_status(self, chat_id):
        from apps.bot.handlers.start import status_handler

        captured = []

        async def fake_reply(text, **kwargs):
            captured.append(text)

        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id),
            message=SimpleNamespace(reply_text=fake_reply)
        )
        await status_handler(update, SimpleNamespace(args=None))
        return captured[0]

    async def test_status_due_today_and_usd_symbol(self):
        self.user.telegram_chat_id = '707001'
        await self.user.asave()

        overview = {
            'confirmed_burn_rate': 1200,
            'potential_risk_amount': 0,
            'active_trials_count': 0,
            'upcoming_7_days_count': 1,
            'target_month': 'Oct 2026',
            'upcoming_7_days': [
                {'title': 'USD Cloud Bill', 'amount': '9.99', 'days_left': 0, 'currency': 'USD'},
                {'title': 'Local Hosting', 'amount': '450', 'days_left': 3, 'currency': 'THB'},
            ],
        }
        with patch('apps.bot.handlers.start.get_financial_overview', return_value=overview):
            text = await self._run_status(707001)

        self.assertIn('$9.99', text)
        self.assertIn('due today!', text)
        self.assertIn('(in 3 days)', text)
        self.assertIn('Financial Summary (Oct 2026)', text)

    async def test_status_thai_rendering(self):
        self.user.preferred_language = 'th'
        self.user.telegram_chat_id = '707002'
        await self.user.asave()

        overview = {
            'confirmed_burn_rate': 5000,
            'potential_risk_amount': 300,
            'active_trials_count': 1,
            'upcoming_7_days_count': 1,
            'target_month': 'Oct 2026',
            'upcoming_7_days': [
                {'title': 'Local Hosting', 'amount': '450', 'days_left': 3, 'currency': 'THB'},
            ],
        }
        with patch('apps.bot.handlers.start.get_financial_overview', return_value=overview):
            text = await self._run_status(707002)

        self.assertIn('\u0e2a\u0e23\u0e38\u0e1b\u0e01\u0e32\u0e23\u0e40\u0e07\u0e34\u0e19', text)  # "\u0e2a\u0e23\u0e38\u0e1b\u0e01\u0e32\u0e23\u0e40\u0e07\u0e34\u0e19"
        self.assertIn('\u0e2d\u0e35\u0e01 3 \u0e27\u0e31\u0e19', text)  # "\u0e2d\u0e35\u0e01 3 \u0e27\u0e31\u0e19"
        self.assertIn('\u0e2d\u0e31\u0e15\u0e23\u0e32\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22\u0e15\u0e48\u0e2d\u0e40\u0e14\u0e37\u0e2d\u0e19', text)


class HelpLanguageTests(TelegramBotTestCase):

    async def _run_help(self, chat_id):
        from apps.bot.handlers.start import help_handler

        captured = []

        async def fake_reply(text, **kwargs):
            captured.append(text)

        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id),
            message=SimpleNamespace(reply_text=fake_reply)
        )
        await help_handler(update, SimpleNamespace())
        return captured[0]

    async def test_help_english_and_thai(self):
        self.user.telegram_chat_id = '707010'
        await self.user.asave()
        en_text = await self._run_help(707010)
        self.assertIn('Life OS Assistant', en_text)
        self.assertIn('/servers', en_text)

        self.user.preferred_language = 'th'
        await self.user.asave()
        th_text = await self._run_help(707010)
        self.assertIn('\u0e1c\u0e39\u0e49\u0e0a\u0e48\u0e27\u0e22 Life OS', th_text)  # "\u0e1c\u0e39\u0e49\u0e0a\u0e48\u0e27\u0e22 Life OS"
        self.assertIn('\u0e04\u0e33\u0e2a\u0e31\u0e48\u0e07\u0e17\u0e35\u0e48\u0e43\u0e0a\u0e49\u0e44\u0e14\u0e49', th_text)  # "\u0e04\u0e33\u0e2a\u0e31\u0e48\u0e07\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14"


class MorningBriefingStage2Tests(TelegramBotTestCase):

    def _brief_data(self):
        return {
            'today': '25/10/2026',
            'tasks': [],
            'bills': [],
            'events': [],
            'infra': {
                'total': 3,
                'online': 2,
                'unhealthy': [{'name': 'prod_web', 'health_status': 'OFFLINE'}],
                'expiring_soon_count': 2,
            },
            'portfolio_val': 150000.0,
            'unrealized_pnl': 2500.0,
            'unrealized_pct': 1.69,
            'news': [],
        }

    async def test_brief_includes_infra_section_english(self):
        from apps.bot.dispatcher import send_morning_briefing

        self.user.telegram_chat_id = '707020'
        await self.user.asave()

        fake_bot = SimpleNamespace(send_message=AsyncMock())

        async def fake_data(user):
            return self._brief_data()

        with patch('apps.bot.dispatcher.get_morning_briefing_data', new=fake_data):
            await send_morning_briefing(fake_bot, '707020', self.user)

        text = fake_bot.send_message.call_args.kwargs['text']
        self.assertIn('Infrastructure & MA:', text)
        self.assertIn('2/3 ONLINE', text)
        self.assertIn('prod\\_web [OFFLINE]', text)
        self.assertIn('Expiring within 7 days: 2', text)

    async def test_brief_thai_rendering(self):
        from apps.bot.dispatcher import send_morning_briefing

        self.user.preferred_language = 'th'
        self.user.telegram_chat_id = '707021'
        await self.user.asave()

        fake_bot = SimpleNamespace(send_message=AsyncMock())

        async def fake_data(user):
            return self._brief_data()

        with patch('apps.bot.dispatcher.get_morning_briefing_data', new=fake_data):
            await send_morning_briefing(fake_bot, '707021', self.user)

        text = fake_bot.send_message.call_args.kwargs['text']
        self.assertIn('\u0e2a\u0e23\u0e38\u0e1b\u0e20\u0e32\u0e1e\u0e40\u0e0a\u0e49\u0e32', text)  # "\u0e2a\u0e23\u0e38\u0e1b\u0e20\u0e32\u0e1e\u0e40\u0e0a\u0e49\u0e32"
        self.assertIn('\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c & MA', text)  # "\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c & MA"
        self.assertIn('2/3 \u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c', text)  # "2/3 \u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c"

    async def test_briefing_data_infra_counts_from_db(self):
        from apps.bot.dispatcher import get_morning_briefing_data

        project = await WorkspaceProject.objects.acreate(user=self.user, name='Brief Proj')
        await _amk_asset(self.user, project, name='up-server', health_status='ONLINE')
        await _amk_asset(self.user, project, name='down-server', health_status='OFFLINE')

        data = await get_morning_briefing_data(self.user)
        infra = data['infra']
        self.assertEqual(infra['total'], 2)
        self.assertEqual(infra['online'], 1)
        self.assertEqual(
            [u['name'] for u in infra['unhealthy']], ['down-server']
        )


class QuickCaptureLanguageTests(TelegramBotTestCase):

    async def _run_quick(self, chat_id, message_text):
        from apps.bot.handlers.messages import text_message_handler

        captured = []

        async def fake_reply(text, **kwargs):
            captured.append(text)

        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=chat_id),
            message=SimpleNamespace(text=message_text, reply_text=fake_reply)
        )
        await text_message_handler(update, SimpleNamespace())
        return captured

    async def test_quick_capture_confirmation_bilingual(self):
        self.user.telegram_chat_id = '707030'
        await self.user.asave()

        captured = await self._run_quick(707030, 'sub Netflix 419')
        self.assertTrue(captured)
        self.assertIn('Quick Obligation Recorded!', captured[0])
        self.assertIn('Netflix', captured[0])

        self.user.preferred_language = 'th'
        await self.user.asave()
        captured_th = await self._run_quick(707030, 'sub Disney 299')
        self.assertIn('\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e14\u0e48\u0e27\u0e19\u0e2a\u0e33\u0e40\u0e23\u0e47\u0e08', captured_th[0])

        # Invalid syntax renders the localized help fallback
        fallback = await self._run_quick(707030, 'hello there')
        self.assertIn('\u0e15\u0e31\u0e27\u0e2d\u0e22\u0e48\u0e32\u0e07\u0e23\u0e39\u0e1b\u0e41\u0e1a\u0e1a\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e14\u0e48\u0e27\u0e19', fallback[0])


# ---------------------------------------------------------------------------
# Stage 3: single-shot batched SSH probe + concurrent watchdog scanning
# ---------------------------------------------------------------------------
import threading
import time as _time


class WatchdogConcurrentScanTests(TransactionTestCase):
    """Threads probe servers in parallel; fixtures must be committed rows."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='concurrent_wd', email='cwd@test.com', password='Password123!'
        )
        self.user.telegram_chat_id = '808001'
        self.user.save()
        self.project = WorkspaceProject.objects.create(user=self.user, name='Concurrent Proj')

    async def test_parallel_probing_and_accurate_alerts(self):
        assets = []
        for i in range(4):
            assets.append(await _amk_asset(
                self.user, self.project, name=f'node-{i}', health_status='ONLINE'
            ))

        breaching = {'node-0', 'node-1'}
        lock = threading.Lock()
        state = {'active': 0, 'max_active': 0}

        def fake_probe(asset):
            with lock:
                state['active'] += 1
                state['max_active'] = max(state['max_active'], state['active'])
            _time.sleep(0.25)
            with lock:
                state['active'] -= 1
            telemetry = {
                'error': None,
                'cpu_pct': 99.0 if asset.name in breaching else 10.0,
                'ram_pct': 30.0,
                'disk_pct': 40.0,
                'containers': [],
            }
            asset.health_status = 'WARNING' if asset.name in breaching else 'ONLINE'
            asset.last_telemetry = telemetry
            asset.last_checked_at = timezone.now()
            asset.save(update_fields=['health_status', 'last_telemetry', 'last_checked_at', 'updated_at'])
            return telemetry

        with patch('apps.workspace.ssh_service.probe_server_telemetry', side_effect=fake_probe):
            alerts = await scan_watchdog_assets()

        # All four probes overlapped (semaphore cap is 5)
        self.assertEqual(state['max_active'], 4)

        # Only the two breaching servers produce alerts, with correct payloads
        alerted = {a['name'] for a in alerts}
        self.assertEqual(alerted, breaching)
        for item in alerts:
            self.assertTrue(item['breaches'])
            self.assertEqual(item['chat_id'], '808001')
            self.assertFalse(item['recovered'])

        for asset in assets:
            await asset.arefresh_from_db()
            if asset.name in breaching:
                self.assertEqual(asset.last_alerted_at is not None, True)


class DispatcherSubscriptionCycleKeyButtonTests(TelegramBotTestCase):

    async def test_ma_and_infra_buttons_include_cycle_key_and_pay(self):
        """MA and Infra alerts build inline button with pay:<id>:<cycle_key> and settle cleanly."""
        from datetime import date
        from decimal import Decimal
        from apps.finance.models import FinancialObligation, ObligationType, FlowDirection, PaymentHistory
        from apps.bot.dispatcher import send_alert_for_obligation
        from apps.bot.handlers.callbacks import process_pay_callback

        self.user.telegram_chat_id = '909001'
        await self.user.asave()

        today = date.today()
        # 1. MA Obligation (INFLOW)
        ma_ob = await FinancialObligation.objects.acreate(
            user=self.user,
            title='MA Project Beta',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('5000.00'),
            due_date=today,
            metadata={'source_type': 'MA_CONTRACT', 'billing_cycle': 'MONTHLY', 'client_name': 'Client Beta'}
        )

        sent_messages = []
        fake_bot = SimpleNamespace()
        async def fake_send_message(chat_id, text, reply_markup=None, **kwargs):
            sent_messages.append({'chat_id': chat_id, 'text': text, 'reply_markup': reply_markup})
        fake_bot.send_message = fake_send_message

        await send_alert_for_obligation(fake_bot, '909001', ma_ob)
        self.assertEqual(len(sent_messages), 1)
        kb = sent_messages[0]['reply_markup'].inline_keyboard
        cb_data = kb[0][0].callback_data
        self.assertTrue(cb_data.startswith(f"pay:{ma_ob.id}:"))
        # Settle via callback
        pay_res = await process_pay_callback(cb_data.replace('pay:', ''), 909001)
        self.assertTrue(pay_res['success'])
        ma_count = await PaymentHistory.objects.filter(obligation=ma_ob).acount()
        self.assertEqual(ma_count, 1)

        # 2. Infra Obligation (OUTFLOW)
        infra_ob = await FinancialObligation.objects.acreate(
            user=self.user,
            title='VPS Prod Hosting',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('1200.00'),
            due_date=today,
            metadata={'source_type': 'INFRA_ASSET', 'billing_cycle': 'MONTHLY'}
        )
        sent_messages.clear()
        await send_alert_for_obligation(fake_bot, '909001', infra_ob)
        self.assertEqual(len(sent_messages), 1)
        kb2 = sent_messages[0]['reply_markup'].inline_keyboard
        cb_data2 = kb2[0][0].callback_data
        self.assertTrue(cb_data2.startswith(f"pay:{infra_ob.id}:"))
        # Settle via callback
        pay_res2 = await process_pay_callback(cb_data2.replace('pay:', ''), 909001)
        self.assertTrue(pay_res2['success'])
        infra_count = await PaymentHistory.objects.filter(obligation=infra_ob).acount()
        self.assertEqual(infra_count, 1)
