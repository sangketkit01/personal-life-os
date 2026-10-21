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
        """ทดสอบการจับคู่ Chat ID ด้วย One-Time Token"""
        paired_user = await pair_user_by_token('TEST_PAIR_TOKEN_99', 123456789)
        self.assertIsNotNone(paired_user)
        self.assertEqual(paired_user.telegram_chat_id, '123456789')
        self.assertIsNone(paired_user.telegram_connect_token)

        # ทดสอบค้นหาด้วย chat_id
        found_user = await get_user_by_chat_id(123456789)
        self.assertEqual(found_user.id, self.user.id)

    def test_parse_quick_text_patterns(self):
        """ทดสอบการวิเคราะห์ข้อความภาษาคน (Quick-Capture)"""
        # 1. ผ่อน tiktok
        p1 = parse_quick_text('ผ่อน tiktok 450 3 งวด')
        self.assertIsNotNone(p1)
        self.assertEqual(p1['type'], ObligationType.INSTALLMENT)
        self.assertEqual(p1['amount'], Decimal('450'))
        self.assertEqual(p1['metadata']['total_terms'], 3)

        # 2. Free Trial
        p2 = parse_quick_text('trial canva 499 เมล work@gmail.com')
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
        p4 = parse_quick_text('หนี้ ตั้ม 500')
        self.assertIsNotNone(p4)
        self.assertEqual(p4['type'], ObligationType.DEBT)
        self.assertEqual(p4['amount'], Decimal('500'))
        self.assertEqual(p4['metadata']['counterparty'], 'ตั้ม')

    async def test_callback_pay_installment(self):
        """ทดสอบกดปุ่ม [จ่ายแล้ว] จาก Telegram"""
        self.user.telegram_chat_id = '999888'
        await self.user.asave()

        moto = await FinancialObligation.objects.acreate(
            user=self.user,
            title='ผ่อนมอไซค์',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            metadata={'total_terms': 36, 'current_term': 14}
        )

        res = await process_pay_callback(str(moto.id), 999888)
        self.assertTrue(res['success'])
        self.assertEqual(res['summary']['current_term'], 15)

    async def test_callback_cancel_trial(self):
        """ทดสอบกดปุ่ม [กดยกเลิกแล้ว] จาก Telegram"""
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
        """ทดสอบการดึงข้อมูลพอร์ตส่งให้บอทแสดงผล"""
        holding = await StockHolding.objects.acreate(
            user=self.user,
            ticker='PTT.BK',
            name='ปตท.'
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
