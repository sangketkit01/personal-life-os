from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.workspace.models import InfrastructureAsset, InfraAssetType, WorkspaceProject
from .dispatcher import get_morning_briefing_data
from .handlers.start import servers_handler
from .i18n import bot_msg


class ServerScopeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='server-scope', password='test', telegram_chat_id='777',
        )

    def asset(self, name, asset_type, status='ONLINE', **kwargs):
        return InfrastructureAsset.objects.create(
            user=self.user, name=name, asset_type=asset_type,
            health_status=status, **kwargs,
        )

    def briefing(self):
        return async_to_sync(get_morning_briefing_data)(self.user)['infra']

    def test_two_servers_and_three_resources_report_two_of_two_online(self):
        self.asset('vps', InfraAssetType.VPS)
        self.asset('dedicated', InfraAssetType.DEDICATED)
        self.asset('domain', InfraAssetType.DOMAIN, 'UNKNOWN')
        self.asset('api', InfraAssetType.API_SERVICE, 'UNKNOWN')
        self.asset('license', InfraAssetType.LICENSE, 'UNKNOWN')

        infra = self.briefing()
        self.assertEqual((infra['online'], infra['total']), (2, 2))
        self.assertEqual(infra['unhealthy'], [])

    def test_non_server_health_and_other_users_do_not_affect_server_summary(self):
        self.asset('online', InfraAssetType.VPS)
        self.asset('offline', InfraAssetType.DEDICATED, 'OFFLINE')
        self.asset('warning', InfraAssetType.VPS, 'WARNING')
        self.asset('unknown', InfraAssetType.VPS, 'UNKNOWN')
        for index, asset_type in enumerate(InfraAssetType.values):
            if asset_type not in (InfraAssetType.VPS, InfraAssetType.DEDICATED):
                self.asset(f'resource-{index}', asset_type,
                           ('ONLINE', 'WARNING', 'OFFLINE')[index % 3])
        other = get_user_model().objects.create_user(username='other-server-owner')
        InfrastructureAsset.objects.create(
            user=other, name='foreign-server', asset_type=InfraAssetType.VPS,
            health_status='OFFLINE',
        )

        infra = self.briefing()
        self.assertEqual((infra['online'], infra['total']), (1, 4))
        self.assertEqual(
            {row['name']: row['health_status'] for row in infra['unhealthy']},
            {'offline': 'OFFLINE', 'warning': 'WARNING'},
        )

    def test_resource_only_inventory_keeps_resource_and_ma_expiry_reminders(self):
        today = timezone.localdate()
        self.asset('domain', InfraAssetType.DOMAIN, expiry_date=today + timedelta(days=2))
        self.asset('database', InfraAssetType.MANAGED_DB, 'OFFLINE',
                   expiry_date=today + timedelta(days=7))
        self.asset('future', InfraAssetType.SAAS, expiry_date=today + timedelta(days=8))
        self.asset('expired', InfraAssetType.LICENSE, expiry_date=today - timedelta(days=1))
        WorkspaceProject.objects.create(
            user=self.user, name='MA', project_type='MA_CONTRACT',
            ma_end_date=today + timedelta(days=3),
        )

        self.assertEqual(self.briefing(), {
            'online': 0, 'total': 0, 'unhealthy': [], 'expiring_soon_count': 3,
        })

    def run_servers(self):
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=777),
            message=SimpleNamespace(reply_text=AsyncMock()),
        )
        with patch('apps.bot.handlers.start.get_user_by_chat_id',
                   AsyncMock(return_value=self.user)), \
             patch('apps.bot.handlers.start._send_typing', AsyncMock()):
            async_to_sync(servers_handler)(update, SimpleNamespace())
        return update.message.reply_text.call_args

    def test_servers_command_only_displays_server_rows_and_probe_buttons(self):
        vps = self.asset('vps', InfraAssetType.VPS)
        dedicated = self.asset('dedicated', InfraAssetType.DEDICATED, 'OFFLINE')
        self.asset('managed-database', InfraAssetType.MANAGED_DB)
        self.asset('platform', InfraAssetType.PAAS)
        self.asset('domain', InfraAssetType.DOMAIN)
        other = get_user_model().objects.create_user(username='foreign-command-owner')
        InfrastructureAsset.objects.create(user=other, name='foreign-server')

        call = self.run_servers()
        text = call.args[0]
        self.assertIn('*vps* [VPS]', text)
        self.assertIn('*dedicated* [DEDICATED]', text)
        for name in ('managed-database', 'platform', 'domain', 'foreign-server'):
            self.assertNotIn(name, text)
        callbacks = {
            button.callback_data
            for row in call.kwargs['reply_markup'].inline_keyboard for button in row
        }
        self.assertEqual(callbacks, {f'probe_vps:{vps.id}', f'probe_vps:{dedicated.id}'})

    def test_servers_command_with_resources_only_returns_empty_state(self):
        self.asset('database', InfraAssetType.MANAGED_DB)
        self.asset('platform', InfraAssetType.PAAS)

        call = self.run_servers()
        self.assertEqual(call.args[0], bot_msg(self.user, 'servers.empty'))
        self.assertNotIn('reply_markup', call.kwargs)
