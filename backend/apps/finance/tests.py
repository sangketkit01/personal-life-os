from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.finance.models import (
    FinancialObligation,
    ObligationType,
    ObligationSubtype,
    ObligationStatus,
    PaymentHistory,
    ObligationAttachment
)
from apps.finance.strategies import ObligationStrategyFactory, BaseObligationStrategy
from apps.finance.services import get_financial_overview, get_exchange_rate_to_thb

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

    def test_api_partial_update_preserves_metadata(self):
        """ทดสอบว่า PATCH อัปเดตข้อมูลบางส่วนต้องไม่ทำลายหรือล้าง metadata เดิม"""
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='ผ่อนโน้ตบุ๊ก',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('3000.00'),
            metadata={'total_terms': 24, 'current_term': 6, 'lender': 'KTC'}
        )
        url = f'/api/finance/obligations/{ob.id}/'
        # ส่ง PATCH แก้เฉพาะ title และ amount ไม่ส่ง metadata
        res = self.client.patch(url, {'title': 'ผ่อนโน้ตบุ๊กสำหรับทำงาน', 'amount': '3200.00'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], 'ผ่อนโน้ตบุ๊กสำหรับทำงาน')
        self.assertEqual(Decimal(str(res.data['amount'])), Decimal('3200.00'))
        # metadata ต้องยังอยู่ครบถ้วน ไม่ถูกรีเซ็ต
        self.assertEqual(res.data['metadata']['total_terms'], 24)
        self.assertEqual(res.data['metadata']['current_term'], 6)
        self.assertEqual(res.data['metadata']['lender'], 'KTC')

    def test_strategy_summary_aliases_and_inflow_calculation(self):
        """ทดสอบ Aliases ใน summary และการแยก Inflow/Outflow ใน Overview"""
        # สร้างหนี้ที่เพื่อนยืมเราไป (INFLOW) นัดคืนเดือนนี้ 5,000 บาท
        FinancialObligation.objects.create(
            user=self.user,
            title='เพื่อนยืมเงินไปหมุน',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('5000.00'),
            due_date=date(2026, 10, 20),
            metadata={'counterparty': 'นาย ก.'}
        )
        # สร้างสมาชิก USD $20
        FinancialObligation.objects.create(
            user=self.user,
            title='ChatGPT Plus',
            type=ObligationType.SUBSCRIPTION,
            direction='OUTFLOW',
            currency='USD',
            amount=Decimal('20.00'),
            metadata={'billing_cycle': 'MONTHLY'}
        )

        overview = get_financial_overview(self.user, target_date=date(2026, 10, 15))
        # INFLOW ต้องถูกจัดเข้า expected_inflow_amount ไม่ใช่ burn_rate
        self.assertEqual(overview['expected_inflow_amount'], Decimal('5000.00'))
        rate = get_exchange_rate_to_thb('USD')
        expected_burn = (Decimal('20.00') * rate).quantize(Decimal('0.01'))
        self.assertEqual(overview['confirmed_burn_rate'], expected_burn)

    def test_hire_purchase_ocpb_early_payoff_simulator(self):
        """เสาหลักที่ 1: ตรวจสอบการคำนวณส่วนลดปิดบัญชีก่อนกำหนดตามกฎหมาย สคบ. 2566 (60%, 70%, 100%)"""
        hp = FinancialObligation.objects.create(
            user=self.user,
            title='สัญญาเช่าซื้อ Honda ADV160',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.HIRE_PURCHASE,
            amount=Decimal('2800.00'),
            metadata={
                'subtype': 'HIRE_PURCHASE',
                'vehicle_model': 'ADV160',
                'financed_amount': '60000.00',
                'flat_rate_pa': '18.00',
                'vat_pct': '7.00',
                'total_terms': 36,
                'current_term': 10  # 10/36 <= 1/3 -> ส่วนลด 60%
            }
        )
        strategy = ObligationStrategyFactory.get_strategy(hp.type)
        summary = strategy.get_summary(hp)
        self.assertIn('early_payoff', summary)
        self.assertEqual(summary['early_payoff']['discount_pct'], Decimal('60.0'))

        # ทดสอบกรณีผ่อนมาแล้ว 20 งวด (20/36 อยู่ระหว่าง 1/3 ถึง 2/3 -> ส่วนลด 70%)
        hp.metadata['current_term'] = 20
        summary_70 = strategy.get_summary(hp)
        self.assertEqual(summary_70['early_payoff']['discount_pct'], Decimal('70.0'))

        # ทดสอบกรณีผ่อนมาแล้ว 28 งวด (28/36 เกิน 2/3 -> ส่วนลด 100% ยกเว้นดอกเบี้ยที่เหลือ)
        hp.metadata['current_term'] = 28
        summary_100 = strategy.get_summary(hp)
        self.assertEqual(summary_100['early_payoff']['discount_pct'], Decimal('100.0'))
        self.assertEqual(summary_100['early_payoff']['discounted_interest'], Decimal('0.00'))

    def test_bnpl_parent_account_and_child_orders_statement(self):
        """เสาหลักที่ 1: ตรวจสอบวงเงินแม่ BNPL คำนวณยอดบิลรายเดือนรวมจาก Order ลูก และวงเงินคงเหลือถูกต้อง"""
        spaylater = FinancialObligation.objects.create(
            user=self.user,
            title='Shopee SPayLater',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            metadata={
                'subtype': 'BNPL_ACCOUNT',
                'provider': 'Shopee',
                'credit_limit': '30000.00',
                'cutoff_day': 25,
                'due_day': 10
            }
        )

        # Order 1: หูฟัง 1,500 บาท ผ่อน 3 เดือน งวดละ 500 (ผ่อนไปแล้ว 1 งวด เหลือ 2 งวด)
        FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='หูฟัง Sony',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('500.00'),
            metadata={'total_terms': 3, 'current_term': 1}
        )

        # Order 2: เก้าอี้ 4,800 บาท ผ่อน 6 เดือน งวดละ 800 (ผ่อนไปแล้ว 2 งวด เหลือ 4 งวด)
        FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='เก้าอี้เพื่อสุขภาพ',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('800.00'),
            metadata={'total_terms': 6, 'current_term': 2}
        )

        strategy = ObligationStrategyFactory.get_strategy(spaylater.type)
        summary = strategy.get_summary(spaylater)

        # ยอดบิลที่ต้องจ่ายเดือนนี้ = 500 + 800 = 1,300 บาท
        self.assertEqual(summary['current_bill_amount'], Decimal('1300.00'))
        self.assertEqual(summary['active_orders_count'], 2)
        # หนี้คงเหลือรวม = (2 * 500) + (4 * 800) = 1,000 + 3,200 = 4,200 บาท
        self.assertEqual(summary['total_remaining_debt'], Decimal('4200.00'))
        # วงเงินคงเหลือ = 30,000 - 4,200 = 25,800 บาท
        self.assertEqual(summary['available_credit'], Decimal('25800.00'))

    def test_attachment_upload_and_pay_with_slip(self):
        """เสาหลักที่ 3: ตรวจสอบการอัปโหลดไฟล์สัญญา และการแนบสลิปผ่าน Action Pay"""
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='เงินกู้ซื้ออุปกรณ์',
            type=ObligationType.DEBT,
            subtype=ObligationSubtype.FORMAL_LOAN,
            amount=Decimal('10000.00'),
            metadata={'remaining_balance': '10000.00'}
        )

        # 1. ทดสอบอัปโหลดไฟล์สัญญาผ่าน Action upload-attachment
        contract_file = SimpleUploadedFile("contract.pdf", b"Contract PDF file contents", content_type="application/pdf")
        res_upload = self.client.post(
            f'/api/finance/obligations/{ob.id}/upload-attachment/',
            {'file': contract_file, 'file_type': 'CONTRACT'},
            format='multipart'
        )
        self.assertEqual(res_upload.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_upload.data['file_name'], 'contract.pdf')
        self.assertEqual(res_upload.data['file_type'], 'CONTRACT')

        # 2. ทดสอบจ่ายหนี้พร้อมแนบรูปสลิป
        slip_file = SimpleUploadedFile("slip.jpg", b"Image binary data for slip", content_type="image/jpeg")
        res_pay = self.client.post(
            f'/api/finance/obligations/{ob.id}/pay/',
            {'paid_amount': '2000.00', 'note': 'ทยอยจ่ายก้อนแรก', 'slip_file': slip_file},
            format='multipart'
        )
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        # ต้องสร้างประวัติการจ่ายและแนบสลิปสำเร็จ
        history = PaymentHistory.objects.filter(obligation=ob).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.attachments.count(), 1)
        self.assertEqual(history.attachments.first().file_type, 'SLIP')

    def test_debtor_recall_message_template(self):
        """เสาหลักที่ 2: ตรวจสอบการสร้างเทมเพลตข้อความทวงเงินพร้อมเลขพร้อมเพย์สำหรับลูกหนี้ (INFLOW)"""
        debtor_ob = FinancialObligation.objects.create(
            user=self.user,
            title='ลูกหนี้ นายสมชาย ยืมเงิน',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('8000.00'),
            due_date=date(2026, 11, 15),
            metadata={
                'counterparty': 'นายสมชาย',
                'remaining_balance': '6000.00',
                'promptpay': '0812345678'
            }
        )
        strategy = ObligationStrategyFactory.get_strategy(debtor_ob.type)
        summary = strategy.get_summary(debtor_ob)
        template = summary.get('recall_template', '')
        self.assertIn('นายสมชาย', template)
        self.assertIn('6,000.00', template)
        self.assertIn('0812345678', template)

    def test_bnpl_monthly_bill_payment_advances_sub_orders_and_keeps_parent_active(self):
        """ตรวจสอบว่าการจ่ายบิลรอบเดือนของ BNPL จะเลื่อนงวดของรายการย่อย และบัญชีแม่ยังคง ACTIVE เสมอ"""
        spaylater = FinancialObligation.objects.create(
            user=self.user,
            title='Shopee SPayLater Line',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={
                'credit_limit': '30000.00',
                'cutoff_day': 25,
                'due_day': 10
            }
        )
        # รายการย่อย 1: 1 งวด (จ่ายรอบนี้แล้วต้อง COMPLETED)
        sub1 = FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='เสื้อยืด Uniqlo',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('490.00'),
            metadata={'total_terms': 1, 'current_term': 0}
        )
        # รายการย่อย 2: 3 งวด (จ่ายรอบนี้แล้วต้องเป็นงวด 1/3 และยัง ACTIVE)
        sub2 = FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='หูฟัง Sony',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('1000.00'),
            metadata={'total_terms': 3, 'current_term': 0}
        )

        strategy = ObligationStrategyFactory.get_strategy(spaylater.type)
        summary = strategy.on_paid(spaylater, paid_amount=Decimal('1490.00'))

        spaylater.refresh_from_db()
        sub1.refresh_from_db()
        sub2.refresh_from_db()

        # 1. บัญชีแม่ต้องยังคง ACTIVE (ไม่ถูกปิดบัญชี)
        self.assertEqual(spaylater.status, ObligationStatus.ACTIVE)
        # 2. รายการย่อย 1 ผ่อนครบ 1 งวดแล้ว ต้องเปลี่ยนเป็น COMPLETED
        self.assertEqual(sub1.status, ObligationStatus.COMPLETED)
        self.assertEqual(sub1.metadata['current_term'], 1)
        # 3. รายการย่อย 2 เลื่อนเป็นงวด 1 และยังคง ACTIVE
        self.assertEqual(sub2.status, ObligationStatus.ACTIVE)
        self.assertEqual(sub2.metadata['current_term'], 1)

    def test_file_upload_validation_and_cleanup(self):
        """ตรวจสอบการป้องกันไฟล์อันตราย (.exe) และการลบไฟล์จริงออกจาก Storage"""
        import os
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='ทดสอบอัปโหลดไฟล์',
            type=ObligationType.DEBT,
            amount=Decimal('5000.00')
        )

        # 1. อัปโหลดไฟล์ .exe ต้องถูกปฏิเสธ (400 Bad Request)
        bad_file = SimpleUploadedFile("malware.exe", b"MZ binary payload", content_type="application/octet-stream")
        res_bad = self.client.post(
            f'/api/finance/obligations/{ob.id}/upload-attachment/',
            {'file': bad_file},
            format='multipart'
        )
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File extension '.exe' is not allowed", res_bad.data['detail'])

        # 2. อัปโหลดไฟล์ PDF ที่ถูกต้อง
        good_file = SimpleUploadedFile("safe_statement.pdf", b"PDF file data", content_type="application/pdf")
        res_good = self.client.post(
            f'/api/finance/obligations/{ob.id}/upload-attachment/',
            {'file': good_file, 'file_type': 'STATEMENT'},
            format='multipart'
        )
        self.assertEqual(res_good.status_code, status.HTTP_201_CREATED)
        attachment_id = res_good.data['id']
        attachment = ObligationAttachment.objects.get(id=attachment_id)
        file_path = attachment.file.path
        self.assertTrue(os.path.exists(file_path))

        # 3. ลบ Attachment ผ่าน API ต้องลบไฟล์จริงออกจากดิสก์ด้วย
        res_del = self.client.delete(f'/api/finance/attachments/{attachment_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ObligationAttachment.objects.filter(id=attachment_id).exists())
        self.assertFalse(os.path.exists(file_path))

    def test_parent_fk_user_scoping_prevents_idor(self):
        """ตรวจสอบความปลอดภัย BOLA/IDOR: User ไม่สามารถผูก sub-order กับบัญชีของ User คนอื่นได้"""
        other_user_ob = FinancialObligation.objects.create(
            user=self.friend,
            title='SPayLater ของเพื่อน',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00')
        )

        # ผู้ใช้ self.user พยายามส่ง parent_id ของ self.friend
        res = self.client.post(
            '/api/finance/obligations/',
            {
                'parent': str(other_user_ob.id),
                'title': 'แอบผูกของคนอื่น',
                'type': 'INSTALLMENT',
                'subtype': 'BNPL_ORDER',
                'amount': '500.00'
            },
            format='json'
        )
        # ต้องไม่ผ่าน Validation (400 Bad Request) เพราะ parent ไม่อยู่ใน queryset ของ user ตัวเอง
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent', res.data)

    def test_query_filters_direction_search_and_ordering(self):
        """ทดสอบการกรองข้อมูลผ่าน API: direction, search, และ ordering"""
        FinancialObligation.objects.create(
            user=self.user,
            title='เพื่อนยืมเงิน ซื้อของ',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('5000.00'),
            metadata={'counterparty': 'Somchai'}
        )
        FinancialObligation.objects.create(
            user=self.user,
            title='ยืมเงินพี่สาว',
            type=ObligationType.DEBT,
            direction='OUTFLOW',
            amount=Decimal('10000.00'),
            metadata={'counterparty': 'Sister'}
        )

        # 1. กรองเฉพาะ direction=INFLOW
        res_in = self.client.get('/api/finance/obligations/?direction=INFLOW')
        self.assertEqual(res_in.status_code, status.HTTP_200_OK)
        results_in = res_in.data.get('results', res_in.data)
        self.assertEqual(len(results_in), 1)
        self.assertEqual(results_in[0]['title'], 'เพื่อนยืมเงิน ซื้อของ')

        # 2. ค้นหาด้วย search=Somchai
        res_search = self.client.get('/api/finance/obligations/?search=Somchai')
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        results_search = res_search.data.get('results', res_search.data)
        self.assertEqual(len(results_search), 1)

        # 3. เรียงลำดับด้วย ordering=-amount
        res_order = self.client.get('/api/finance/obligations/?ordering=-amount')
        self.assertEqual(res_order.status_code, status.HTTP_200_OK)
        results_order = res_order.data.get('results', res_order.data)
        self.assertEqual(results_order[0]['title'], 'ยืมเงินพี่สาว')

    def test_installment_schedule_and_debtors_actions(self):
        """ทดสอบ Action /schedule/ และ /debtors/"""
        # สร้างรายการผ่อนรถ
        car = FinancialObligation.objects.create(
            user=self.user,
            title='ผ่อนรถยนต์ Honda Civic',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.HIRE_PURCHASE,
            amount=Decimal('12000.00'),
            due_date=date(2026, 11, 10),
            metadata={
                'total_terms': 48,
                'current_term': 12,
                'financed_amount': '500000.00',
                'flat_rate_pa': '2.50'
            }
        )

        res_sched = self.client.get(f'/api/finance/obligations/{car.id}/schedule/')
        self.assertEqual(res_sched.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sched.data['total_terms'], 48)
        self.assertEqual(res_sched.data['current_term'], 12)
        self.assertEqual(len(res_sched.data['schedule']), 48)
        self.assertEqual(res_sched.data['schedule'][0]['status'], 'PAID')
        self.assertEqual(res_sched.data['schedule'][12]['status'], 'DUE')
        self.assertEqual(res_sched.data['schedule'][13]['status'], 'UPCOMING')

        # ทดสอบ Debtors directory
        FinancialObligation.objects.create(
            user=self.user,
            title='เงินกู้ยืม กิตติ',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('15000.00'),
            metadata={'counterparty': 'กิตติ'}
        )
        res_debtors = self.client.get('/api/finance/obligations/debtors/')
        self.assertEqual(res_debtors.status_code, status.HTTP_200_OK)
        debtor_names = [d['debtor_name'] for d in res_debtors.data]
        self.assertIn('กิตติ', debtor_names)
