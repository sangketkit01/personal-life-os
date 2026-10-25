from decimal import Decimal
from django.test import TestCase
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

        first = await process_pay_callback(str(sub.id), 777001)
        self.assertTrue(first['success'])

        # Simulates tapping the button on the OLD Telegram message again
        second = await process_pay_callback(str(sub.id), 777001)
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


class WatchdogScanCooldownTests(TelegramBotTestCase):

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
