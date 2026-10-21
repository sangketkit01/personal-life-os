from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.finance.models import FinancialObligation, ObligationType, ObligationStatus, PaymentHistory
from apps.finance.strategies import ObligationStrategyFactory, BaseObligationStrategy
from apps.finance.services import get_financial_overview

User = get_user_model()


class FinancialStrategyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='financier',
            email='financier@test.com',
            password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='friend',
            email='friend@test.com',
            password='Password123!'
        )

    def test_installment_progression_and_auto_completion(self):
        """ทดสอบผ่อนมอเตอร์ไซค์: ตัดงวด, เลื่อนวัน, และปิดหนี้อัตโนมัติเมื่องวดสุดท้าย"""
        moto = FinancialObligation.objects.create(
            user=self.user,
            title='ผ่อนมอเตอร์ไซค์ Grand Filano',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            due_date=date(2026, 11, 5),
            billing_day=5,
            metadata={
                'total_terms': 36,
                'current_term': 14,
                'lender': 'กรุงศรี ออโต้'
            }
        )

        strategy = ObligationStrategyFactory.get_strategy(moto.type)
        summary = strategy.get_summary(moto)

        # 1. ตรวจสอบสถานะเริ่มต้น (เหลืองวด 22, ยอดหนี้ 61,600)
        self.assertEqual(summary['remaining_terms'], 22)
        self.assertEqual(summary['remaining_balance'], Decimal('61600.00'))
        self.assertEqual(summary['progress_pct'], 38.9)
        self.assertFalse(summary['is_finished'])

        # 2. จำลองการจ่ายงวดที่ 15
        strategy.on_paid(moto, paid_amount=Decimal('2800.00'), note='โอนผ่าน KBank')
        moto.refresh_from_db()

        self.assertEqual(moto.metadata['current_term'], 15)
        self.assertEqual(moto.due_date, date(2026, 12, 5))
        self.assertEqual(moto.status, ObligationStatus.ACTIVE)
        self.assertEqual(PaymentHistory.objects.filter(obligation=moto).count(), 1)

        # 3. จำลองการจ่ายงวดสุดท้าย (สมมติ current_term = 35 จ่ายงวด 36)
        moto.metadata['current_term'] = 35
        moto.save()

        strategy.on_paid(moto, paid_amount=Decimal('2800.00'))
        moto.refresh_from_db()

        self.assertEqual(moto.metadata['current_term'], 36)
        self.assertEqual(moto.status, ObligationStatus.COMPLETED)
        self.assertIsNone(moto.due_date)  # ผ่อนหมดแล้ว ต้องไม่มีวันครบกำหนด
        self.assertTrue(strategy.get_summary(moto)['is_finished'])

    def test_month_end_date_rolling_edge_case(self):
        """ทดสอบเลื่อนวันสิ้นเดือน: 31 ม.ค. -> 28 ก.พ. -> 31 มี.ค."""
        calc = BaseObligationStrategy.calculate_next_due_date

        start_date = date(2026, 1, 31)
        # เลื่อนจาก 31 ม.ค. ไป 1 เดือน (ก.พ. 2026 มี 28 วัน)
        feb_date = calc(start_date, billing_day=31, months_to_add=1)
        self.assertEqual(feb_date, date(2026, 2, 28))

        # เลื่อนจาก 28 ก.พ. ไป 1 เดือน โดยมี billing_day เดิมคือ 31
        mar_date = calc(feb_date, billing_day=31, months_to_add=1)
        self.assertEqual(mar_date, date(2026, 3, 31))

        # เลื่อนจาก 31 มี.ค. ไป 1 เดือน (เม.ย. มี 30 วัน ต้องได้ 30 เม.ย.)
        apr_date = calc(mar_date, billing_day=31, months_to_add=1)
        self.assertEqual(apr_date, date(2026, 4, 30))

        # เลื่อนจาก 30 เม.ย. ไป 1 เดือน (พ.ค. มี 31 วัน ต้องกลับมา 31 พ.ค. ได้ถูกต้อง)
        may_date = calc(apr_date, billing_day=31, months_to_add=1)
        self.assertEqual(may_date, date(2026, 5, 31))

        # เลื่อนข้าม 2 เดือนจาก 28 ก.พ. ไป เม.ย. (30 วัน)
        apr_skip = calc(feb_date, billing_day=31, months_to_add=2)
        self.assertEqual(apr_skip, date(2026, 4, 30))

    def test_debt_partial_payment_and_settlement(self):
        """ทดสอบหนี้สิน: ยืม 5,000 คืนก่อน 2,000 เหลือ 3,000 แล้วคืนอีก 3,000 ปิดหนี้"""
        debt = FinancialObligation.objects.create(
            user=self.user,
            title='หนี้ไอ้ตั้ม ค่าหมูกระทะ',
            type=ObligationType.DEBT,
            amount=Decimal('5000.00'),
            metadata={'counterparty': 'ตั้ม'}
        )

        strategy = ObligationStrategyFactory.get_strategy(debt.type)
        summary = strategy.get_summary(debt)
        self.assertEqual(summary['remaining_balance'], Decimal('5000.00'))

        # คืนรอบแรก 2,000 บาท
        strategy.on_paid(debt, paid_amount=Decimal('2000.00'), note='คืนรอบแรก')
        debt.refresh_from_db()

        self.assertEqual(debt.metadata['remaining_balance'], 3000.0)
        self.assertEqual(debt.status, ObligationStatus.ACTIVE)

        # คืนรอบสองอีก 3,000 บาท (ครบยอด)
        strategy.on_paid(debt, paid_amount=Decimal('3000.00'), note='ปิดยอดหนี้')
        debt.refresh_from_db()

        self.assertEqual(debt.metadata['remaining_balance'], 0.0)
        self.assertEqual(debt.status, ObligationStatus.COMPLETED)
        self.assertTrue(strategy.get_summary(debt)['is_settled'])

    def test_free_trial_countdown_and_cancellation(self):
        """ทดสอบ Free Trial: นับถอยหลัง และกดยกเลิกเก็บประวัติ CANCELLED"""
        today = timezone.localdate()
        trial = FinancialObligation.objects.create(
            user=self.user,
            title='Canva Pro Free Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('499.00'),
            due_date=today + timezone.timedelta(days=1),  # หมดพรุ่งนี้
            metadata={
                'account_email': 'work@gmail.com',
                'auto_renew_cost': 499.00
            }
        )

        strategy = ObligationStrategyFactory.get_strategy(trial.type)
        summary = strategy.get_summary(trial)

        # ต้องได้ Urgency ระดับ CRITICAL (เหลือ 1 วัน)
        self.assertEqual(summary['days_remaining'], 1)
        self.assertEqual(summary['urgency'], 'CRITICAL')

        # กดยกเลิก Trial
        strategy.cancel(trial)
        trial.refresh_from_db()

        self.assertEqual(trial.status, ObligationStatus.CANCELLED)
        self.assertTrue(strategy.get_summary(trial)['is_cancelled'])

    def test_monthly_burn_rate_calculations(self):
        """ทดสอบสูตร Burn Rate: รวมผ่อน + Sub รายเดือน + Sub รายปีเฉพาะเดือนที่ตก + แยก Potential Trial"""
        target_date = date(2026, 10, 15)

        # 1. ผ่อนมอเตอร์ไซค์ 2,800/เดือน (นับ)
        FinancialObligation.objects.create(
            user=self.user,
            title='มอเตอร์ไซค์',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            metadata={'total_terms': 36, 'current_term': 10}
        )

        # 2. Netflix 419/เดือน (นับ)
        FinancialObligation.objects.create(
            user=self.user,
            title='Netflix',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('419.00'),
            metadata={'billing_cycle': 'MONTHLY'}
        )

        # 3. iCloud 1,190/ปี แต่ตัดเดือน 10 (ต.ค.) พอดี (นับยอดเต็ม)
        FinancialObligation.objects.create(
            user=self.user,
            title='iCloud รายปี',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('1190.00'),
            due_date=date(2026, 10, 28),
            metadata={'billing_cycle': 'YEARLY'}
        )

        # 4. โฮสติ้งรายปี 1,500/ปี แต่ตัดเดือน 12 (ธ.ค.) -> ในเดือน 10 ต้องไม่ถูกนับ!
        FinancialObligation.objects.create(
            user=self.user,
            title='VPS รายปี',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('1500.00'),
            due_date=date(2026, 12, 1),
            metadata={'billing_cycle': 'YEARLY'}
        )

        # 5. Free Trial Adobe 600 หมดเดือน 10 -> ต้องไม่นับใน Confirmed แต่ต้องไปโชว์ใน Potential Risk
        FinancialObligation.objects.create(
            user=self.user,
            title='Adobe Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('600.00'),
            due_date=date(2026, 10, 25),
            metadata={'auto_renew_cost': 600.00}
        )

        overview = get_financial_overview(self.user, target_date=target_date)

        # Confirmed Burn Rate = 2800 (ผ่อน) + 419 (Netflix) + 1190 (iCloud) = 4409.00
        self.assertEqual(overview['confirmed_burn_rate'], Decimal('4409.00'))
        # Potential Risk = 600.00
        self.assertEqual(overview['potential_risk_amount'], Decimal('600.00'))
        self.assertEqual(overview['active_trials_count'], 1)

    def test_multi_user_data_isolation(self):
        """ทดสอบความปลอดภัย: ข้อมูลของ User A ต้องไม่ปนกับ User B 100%"""
        FinancialObligation.objects.create(
            user=self.user,
            title='บิลของ User A',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('10000.00'),
            metadata={'total_terms': 10, 'current_term': 1}
        )

        FinancialObligation.objects.create(
            user=self.friend,
            title='บิลของเพื่อน User B',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('500.00'),
            metadata={'total_terms': 10, 'current_term': 1}
        )

        overview_a = get_financial_overview(self.user)
        overview_b = get_financial_overview(self.friend)

        self.assertEqual(overview_a['confirmed_burn_rate'], Decimal('10000.00'))
        self.assertEqual(overview_b['confirmed_burn_rate'], Decimal('500.00'))



from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.tokens import generate_access_token


class FinancialAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='api_user',
            email='api_user@test.com',
            password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='friend_user',
            email='friend_user@test.com',
            password='Password123!'
        )
        self.client = APIClient()
        # จำลองการส่ง Access Token ใน HttpOnly Cookie
        token = generate_access_token(self.user)
        self.client.cookies['access_token'] = token

    def test_api_get_overview(self):
        """ทดสอบเรียก GET /api/finance/overview/"""
        res = self.client.get('/api/finance/overview/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('confirmed_burn_rate', res.data)
        self.assertIn('potential_risk_amount', res.data)
        self.assertIn('upcoming_7_days', res.data)

    def test_api_create_and_pay_installment(self):
        """ทดสอบสร้างผ่อนของ และทดสอบ Action Pay ผ่าน REST API"""
        # 1. สร้างรายการผ่อนมอเตอร์ไซค์
        payload = {
            'title': 'ผ่อนมอเตอร์ไซค์',
            'type': 'INSTALLMENT',
            'amount': '2800.00',
            'due_date': '2026-11-05',
            'billing_day': 5,
            'metadata': {
                'total_terms': 36,
                'current_term': 14,
                'lender': 'กรุงศรี'
            }
        }
        res_create = self.client.post('/api/finance/obligations/', payload, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        ob_id = res_create.data['id']
        self.assertEqual(res_create.data['summary']['remaining_terms'], 22)

        # 2. ยิง Action ชำระงวดที่ 15
        pay_url = f'/api/finance/obligations/{ob_id}/pay/'
        res_pay = self.client.post(pay_url, {'note': 'จ่ายผ่าน API'}, format='json')
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pay.data['obligation']['metadata']['current_term'], 15)
        self.assertEqual(res_pay.data['obligation']['due_date'], '2026-12-05')

    def test_api_cancel_trial_action(self):
        """ทดสอบ Action cancel-trial ผ่าน REST API"""
        trial = FinancialObligation.objects.create(
            user=self.user,
            title='Spotify Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('139.00'),
            metadata={'account_email': 'me@spotify.com'}
        )
        url = f'/api/finance/obligations/{trial.id}/cancel-trial/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['obligation']['status'], 'CANCELLED')

    def test_api_prevent_cross_user_access(self):
        """ทดสอบว่า User A ไม่สามารถเข้าถึงหรือจ่ายบิลของ User B ได้ (Data Isolation 404)"""
        friend_ob = FinancialObligation.objects.create(
            user=self.friend,
            title='บิลลับของเพื่อน',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('5000.00'),
            metadata={'total_terms': 10, 'current_term': 1}
        )

        # User A พยายามแอบดูบิลของเพื่อน
        res_get = self.client.get(f'/api/finance/obligations/{friend_ob.id}/')
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # User A พยายามแอบกดจ่ายบิลของเพื่อน
        res_pay = self.client.post(f'/api/finance/obligations/{friend_ob.id}/pay/')
        self.assertEqual(res_pay.status_code, status.HTTP_404_NOT_FOUND)
