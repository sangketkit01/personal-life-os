import tempfile
import shutil
from decimal import Decimal
from datetime import date
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.finance.models import (
    FinancialObligation,
    ObligationType,
    ObligationSubtype,
    ObligationStatus,
    FlowDirection,
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
        """Test motorcycle installment: term deduction, date rollover, and auto completion on final term."""
        moto = FinancialObligation.objects.create(
            user=self.user,
            title='Grand Filano Installment',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            due_date=date(2026, 11, 5),
            billing_day=5,
            metadata={
                'total_terms': 36,
                'current_term': 14,
                'lender': 'Krungsri Auto'
            }
        )

        strategy = ObligationStrategyFactory.get_strategy(moto.type)
        summary = strategy.get_summary(moto)

        # 1. Verify initial status (22 terms remaining, debt 61,600)
        self.assertEqual(summary['remaining_terms'], 22)
        self.assertEqual(summary['remaining_balance'], Decimal('61600.00'))
        self.assertEqual(summary['progress_pct'], 38.9)
        self.assertFalse(summary['is_finished'])

        # 2. Simulate paying term 15
        strategy.on_paid(moto, paid_amount=Decimal('2800.00'), note='Transfer via KBank')
        moto.refresh_from_db()

        self.assertEqual(moto.metadata['current_term'], 15)
        self.assertEqual(moto.due_date, date(2026, 12, 5))
        self.assertEqual(moto.status, ObligationStatus.ACTIVE)
        self.assertEqual(PaymentHistory.objects.filter(obligation=moto).count(), 1)

        # 3. Simulate final term payment (current_term = 35 paying term 36)
        moto.metadata['current_term'] = 35
        moto.save()

        strategy.on_paid(moto, paid_amount=Decimal('2800.00'))
        moto.refresh_from_db()

        self.assertEqual(moto.metadata['current_term'], 36)
        self.assertEqual(moto.status, ObligationStatus.COMPLETED)
        self.assertIsNone(moto.due_date)  # Fully paid, no due date
        self.assertTrue(strategy.get_summary(moto)['is_finished'])

    def test_month_end_date_rolling_edge_case(self):
        """Test month-end date rollover: Jan 31 -> Feb 28 -> Mar 31"""
        calc = BaseObligationStrategy.calculate_next_due_date

        start_date = date(2026, 1, 31)
        # Advance from Jan 31 by 1 month (Feb 2026 has 28 days)
        feb_date = calc(start_date, billing_day=31, months_to_add=1)
        self.assertEqual(feb_date, date(2026, 2, 28))

        # Advance from Feb 28 by 1 month preserving billing_day 31
        mar_date = calc(feb_date, billing_day=31, months_to_add=1)
        self.assertEqual(mar_date, date(2026, 3, 31))

        # Advance from Mar 31 by 1 month (Apr has 30 days -> Apr 30)
        apr_date = calc(mar_date, billing_day=31, months_to_add=1)
        self.assertEqual(apr_date, date(2026, 4, 30))

        # Advance from Apr 30 by 1 month (May has 31 days -> restores May 31)
        may_date = calc(apr_date, billing_day=31, months_to_add=1)
        self.assertEqual(may_date, date(2026, 5, 31))

        # Advance 2 months from Feb 28 to Apr (30 days)
        apr_skip = calc(feb_date, billing_day=31, months_to_add=2)
        self.assertEqual(apr_skip, date(2026, 4, 30))

    def test_debt_partial_payment_and_settlement(self):
        """Test debt repayment: borrowed 5000, repay 2000, balance 3000, repay remaining 3000 to settle"""
        debt = FinancialObligation.objects.create(
            user=self.user,
            title='Dinner Debt with Tum',
            type=ObligationType.DEBT,
            amount=Decimal('5000.00'),
            metadata={'counterparty': 'Tum'}
        )

        strategy = ObligationStrategyFactory.get_strategy(debt.type)
        summary = strategy.get_summary(debt)
        self.assertEqual(summary['remaining_balance'], Decimal('5000.00'))

        # Repay first portion 2,000
        strategy.on_paid(debt, paid_amount=Decimal('2000.00'), note='First payment')
        debt.refresh_from_db()

        self.assertEqual(debt.metadata['remaining_balance'], 3000.0)
        self.assertEqual(debt.status, ObligationStatus.ACTIVE)

        # Repay second portion 3,000 (settled)
        strategy.on_paid(debt, paid_amount=Decimal('3000.00'), note='Full settlement')
        debt.refresh_from_db()

        self.assertEqual(debt.metadata['remaining_balance'], 0.0)
        self.assertEqual(debt.status, ObligationStatus.COMPLETED)
        self.assertTrue(strategy.get_summary(debt)['is_settled'])

    def test_free_trial_countdown_and_cancellation(self):
        """Test Free Trial: countdown and cancellation with CANCELLED status"""
        today = timezone.localdate()
        trial = FinancialObligation.objects.create(
            user=self.user,
            title='Canva Pro Free Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('499.00'),
            due_date=today + timezone.timedelta(days=1),  # Expires tomorrow
            metadata={
                'account_email': 'work@gmail.com',
                'auto_renew_cost': 499.00
            }
        )

        strategy = ObligationStrategyFactory.get_strategy(trial.type)
        summary = strategy.get_summary(trial)

        # Urgency must be CRITICAL (1 day left)
        self.assertEqual(summary['days_remaining'], 1)
        self.assertEqual(summary['urgency'], 'CRITICAL')

        # Cancel Trial
        strategy.cancel(trial)
        trial.refresh_from_db()

        self.assertEqual(trial.status, ObligationStatus.CANCELLED)
        self.assertTrue(strategy.get_summary(trial)['is_cancelled'])

    def test_monthly_burn_rate_calculations(self):
        """Test Burn Rate formula: installments + monthly subs + yearly subs in due month + separate potential trial"""
        target_date = date(2026, 10, 15)

        # 1. Motorcycle installment 2,800/mo (counted)
        FinancialObligation.objects.create(
            user=self.user,
            title='Motorcycle',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('2800.00'),
            metadata={'total_terms': 36, 'current_term': 10}
        )

        # 2. Netflix 419/mo (counted)
        FinancialObligation.objects.create(
            user=self.user,
            title='Netflix',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('419.00'),
            metadata={'billing_cycle': 'MONTHLY'}
        )

        # 3. iCloud 1,190/yr due in month 10 (Oct) (counted full)
        FinancialObligation.objects.create(
            user=self.user,
            title='iCloud Yearly',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('1190.00'),
            due_date=date(2026, 10, 28),
            metadata={'billing_cycle': 'YEARLY'}
        )

        # 4. Hosting 1,500/yr due in month 12 (Dec) -> not counted in month 10!
        FinancialObligation.objects.create(
            user=self.user,
            title='VPS Yearly',
            type=ObligationType.SUBSCRIPTION,
            amount=Decimal('1500.00'),
            due_date=date(2026, 12, 1),
            metadata={'billing_cycle': 'YEARLY'}
        )

        # 5. Free Trial Adobe 600 expires month 10 -> excluded from Confirmed, included in Potential Risk
        FinancialObligation.objects.create(
            user=self.user,
            title='Adobe Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('600.00'),
            due_date=date(2026, 10, 25),
            metadata={'auto_renew_cost': 600.00}
        )

        overview = get_financial_overview(self.user, target_date=target_date)

        # Confirmed Burn Rate = 2800 + 419 + 1190 = 4409.00
        self.assertEqual(overview['confirmed_burn_rate'], Decimal('4409.00'))
        # Potential Risk = 600.00
        self.assertEqual(overview['potential_risk_amount'], Decimal('600.00'))
        self.assertEqual(overview['active_trials_count'], 1)

    def test_multi_user_data_isolation(self):
        """Security test: User A data must not leak to User B"""
        FinancialObligation.objects.create(
            user=self.user,
            title='User A Bill',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('10000.00'),
            metadata={'total_terms': 10, 'current_term': 1}
        )

        FinancialObligation.objects.create(
            user=self.friend,
            title='User B Bill',
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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        super().tearDownClass()

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
        # Simulate sending Access Token in HttpOnly Cookie
        token = generate_access_token(self.user)
        self.client.cookies['access_token'] = token

    def test_api_get_overview(self):
        """Test GET /api/finance/overview/"""
        res = self.client.get('/api/finance/overview/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('confirmed_burn_rate', res.data)
        self.assertIn('potential_risk_amount', res.data)
        self.assertIn('upcoming_7_days', res.data)

    def test_api_create_and_pay_installment(self):
        """Test creating installment and Action Pay via REST API"""
        # 1. Create motorcycle installment
        payload = {
            'title': 'Motorcycle Installment',
            'type': 'INSTALLMENT',
            'amount': '2800.00',
            'due_date': '2026-11-05',
            'billing_day': 5,
            'metadata': {
                'total_terms': 36,
                'current_term': 14,
                'lender': 'Krungsri'
            }
        }
        res_create = self.client.post('/api/finance/obligations/', payload, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        ob_id = res_create.data['id']
        self.assertEqual(res_create.data['summary']['remaining_terms'], 22)

        # 2. Trigger Action Pay for term 15
        pay_url = f'/api/finance/obligations/{ob_id}/pay/'
        res_pay = self.client.post(pay_url, {'note': 'Paid via API'}, format='json')
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pay.data['obligation']['metadata']['current_term'], 15)
        self.assertEqual(res_pay.data['obligation']['due_date'], '2026-12-05')

    def test_api_cancel_trial_action(self):
        """Test Action cancel-trial via REST API"""
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
        """Test that User A cannot access or pay User B bills (Data Isolation 404)"""
        friend_ob = FinancialObligation.objects.create(
            user=self.friend,
            title='Friend Secret Bill',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('5000.00'),
            metadata={'total_terms': 10, 'current_term': 1}
        )

        # User A attempts to inspect friend bill
        res_get = self.client.get(f'/api/finance/obligations/{friend_ob.id}/')
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # User A attempts to pay friend bill
        res_pay = self.client.post(f'/api/finance/obligations/{friend_ob.id}/pay/')
        self.assertEqual(res_pay.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_partial_update_preserves_metadata(self):
        """Test that PATCH partial update preserves existing metadata"""
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='Laptop Installment',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('3000.00'),
            metadata={'total_terms': 24, 'current_term': 6, 'lender': 'KTC'}
        )
        url = f'/api/finance/obligations/{ob.id}/'
        # Send PATCH for title and amount without metadata
        res = self.client.patch(url, {'title': 'Work Laptop Installment', 'amount': '3200.00'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], 'Work Laptop Installment')
        self.assertEqual(Decimal(str(res.data['amount'])), Decimal('3200.00'))
        # Metadata must be preserved without reset
        self.assertEqual(res.data['metadata']['total_terms'], 24)
        self.assertEqual(res.data['metadata']['current_term'], 6)
        self.assertEqual(res.data['metadata']['lender'], 'KTC')

    def test_strategy_summary_aliases_and_inflow_calculation(self):
        """Test Aliases in summary and Inflow/Outflow segregation in Overview"""
        # Create debt owed to user (INFLOW) due this month 5,000
        FinancialObligation.objects.create(
            user=self.user,
            title='Friend Loan Inflow',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('5000.00'),
            due_date=date(2026, 10, 20),
            metadata={'counterparty': 'Mr. A'}
        )
        # Create USD subscription $20
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
        # INFLOW must go into expected_inflow_amount not burn_rate
        self.assertEqual(overview['expected_inflow_amount'], Decimal('5000.00'))
        rate = get_exchange_rate_to_thb('USD')
        expected_burn = (Decimal('20.00') * rate).quantize(Decimal('0.01'))
        self.assertEqual(overview['confirmed_burn_rate'], expected_burn)

    def test_hire_purchase_ocpb_early_payoff_simulator(self):
        """Pillar 1: Early payoff rebate calculation under Consumer Protection Act (60%, 70%, 100%)"""
        hp = FinancialObligation.objects.create(
            user=self.user,
            title='Honda ADV160 Hire Purchase',
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
                'current_term': 10  # 10/36 <= 1/3 -> 60% rebate
            }
        )
        strategy = ObligationStrategyFactory.get_strategy(hp.type)
        summary = strategy.get_summary(hp)
        self.assertIn('early_payoff', summary)
        self.assertEqual(summary['early_payoff']['discount_pct'], Decimal('60.0'))

        # Paid 20 terms (between 1/3 and 2/3 -> 70% rebate)
        hp.metadata['current_term'] = 20
        summary_70 = strategy.get_summary(hp)
        self.assertEqual(summary_70['early_payoff']['discount_pct'], Decimal('70.0'))

        # Paid 28 terms (> 2/3 -> 100% rebate on unearned interest)
        hp.metadata['current_term'] = 28
        summary_100 = strategy.get_summary(hp)
        self.assertEqual(summary_100['early_payoff']['discount_pct'], Decimal('100.0'))
        self.assertEqual(summary_100['early_payoff']['discounted_interest'], Decimal('0.00'))

    def test_bnpl_parent_account_and_child_orders_statement(self):
        """Pillar 1: BNPL credit line calculation from sub-orders and available balance"""
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

        # Order 1: Headphones 1,500, 3 terms of 500 (1 paid, 2 remaining)
        FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='Sony Headphones',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('500.00'),
            metadata={'total_terms': 3, 'current_term': 1}
        )

        # Order 2: Chair 4,800, 6 terms of 800 (2 paid, 4 remaining)
        FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='Ergonomic Chair',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('800.00'),
            metadata={'total_terms': 6, 'current_term': 2}
        )

        strategy = ObligationStrategyFactory.get_strategy(spaylater.type)
        summary = strategy.get_summary(spaylater)

        # Monthly bill due = 500 + 800 = 1,300
        self.assertEqual(summary['current_bill_amount'], Decimal('1300.00'))
        self.assertEqual(summary['active_orders_count'], 2)
        # Total remaining debt = 1,000 + 3,200 = 4,200
        self.assertEqual(summary['total_remaining_debt'], Decimal('4200.00'))
        # Available credit limit = 30,000 - 4,200 = 25,800
        self.assertEqual(summary['available_credit'], Decimal('25800.00'))

    def test_bnpl_real_world_monthly_statement_timeline_and_down_payment(self):
        """User Domain Test: Multi-order BNPL monthly statement aggregation & hybrid down payment."""
        from apps.ledger.models import Account, AccountType, Transaction, TransactionType

        # 1. Payer's Cash flow bank account with \u0e3f10,000
        bank = Account.objects.create(
            user=self.user,
            name='Main Bank Account',
            account_type=AccountType.BANK,
            current_balance=Decimal('10000.00'),
            initial_balance=Decimal('10000.00'),
            currency='THB'
        )

        # 2. Revolving BNPL Facility (e.g. SPayLater)
        bnpl = FinancialObligation.objects.create(
            user=self.user,
            title='SPayLater Facility',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={
                'subtype': 'BNPL_ACCOUNT',
                'provider': 'Shopee',
                'credit_limit': '20000.00',
                'cutoff_day': 25,
                'due_day': 10
            }
        )

        # Order A: \u0e3f300, bought in Oct 2026, 3 months pay-later (\u0e3f100/mo)
        res_a = self.client.post('/api/finance/obligations/', {
            'parent': str(bnpl.id),
            'title': 'Product A',
            'type': ObligationType.INSTALLMENT,
            'subtype': ObligationSubtype.BNPL_ORDER,
            'amount': '100.00',
            'metadata': {
                'total_terms': 3,
                'current_term': 0,
                'order_date': '2026-10-15',
                'total_price': '300.00',
                'down_payment': '0.00',
                'financed_amount': '300.00',
                'store': 'Shopee'
            }
        }, format='json')
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)

        # Order B: \u0e3f800, bought in Oct 2026, 2 months pay-later (\u0e3f400/mo)
        res_b = self.client.post('/api/finance/obligations/', {
            'parent': str(bnpl.id),
            'title': 'Product B',
            'type': ObligationType.INSTALLMENT,
            'subtype': ObligationSubtype.BNPL_ORDER,
            'amount': '400.00',
            'metadata': {
                'total_terms': 2,
                'current_term': 0,
                'order_date': '2026-10-20',
                'total_price': '800.00',
                'down_payment': '0.00',
                'financed_amount': '800.00',
                'store': 'Shopee'
            }
        }, format='json')
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)

        # Order C: \u0e3f500, bought in Oct 2026, Down Payment \u0e3f200 + 6 months pay-later (\u0e3f50/mo)
        res_c = self.client.post('/api/finance/obligations/', {
            'parent': str(bnpl.id),
            'title': 'Product C',
            'type': ObligationType.INSTALLMENT,
            'subtype': ObligationSubtype.BNPL_ORDER,
            'amount': '50.00',
            'down_payment_account_id': str(bank.id),
            'metadata': {
                'total_terms': 6,
                'current_term': 0,
                'order_date': '2026-10-22',
                'total_price': '500.00',
                'down_payment': '200.00',
                'financed_amount': '300.00',
                'store': 'Shopee'
            }
        }, format='json')
        self.assertEqual(res_c.status_code, status.HTTP_201_CREATED)

        # Verify down payment deducted from Bank account
        bank.refresh_from_db()
        self.assertEqual(bank.current_balance, Decimal('9800.00'))
        down_tx = Transaction.objects.filter(account=bank, gross_amount=Decimal('200.00')).first()
        self.assertIsNotNone(down_tx)
        self.assertEqual(down_tx.transaction_type, TransactionType.OUTFLOW)

        # Verify Monthly Statement Timeline Matrix
        strategy = ObligationStrategyFactory.get_strategy(bnpl.type)
        summary = strategy.get_summary(bnpl)
        timeline = summary['statement_timeline']

        # Expected months: 2026-11, 2026-12, 2027-01, 2027-02, 2027-03, 2027-04
        self.assertEqual(len(timeline), 6)

        # Month 11 (Nov 2026): A (100) + B (400) + C (50) = 550
        self.assertEqual(timeline[0]['statement_month'], '2026-11')
        self.assertEqual(timeline[0]['total_due'], Decimal('550.00'))
        self.assertEqual(timeline[0]['orders_count'], 3)

        # Month 12 (Dec 2026): A (100) + B (400) + C (50) = 550
        self.assertEqual(timeline[1]['statement_month'], '2026-12')
        self.assertEqual(timeline[1]['total_due'], Decimal('550.00'))
        self.assertEqual(timeline[1]['orders_count'], 3)

        # Month 01 (Jan 2027): A (100) + C (50) = 150
        self.assertEqual(timeline[2]['statement_month'], '2027-01')
        self.assertEqual(timeline[2]['total_due'], Decimal('150.00'))
        self.assertEqual(timeline[2]['orders_count'], 2)

        # Months 02, 03, 04 (Feb, Mar, Apr 2027): C (50)
        for i in [3, 4, 5]:
            self.assertEqual(timeline[i]['total_due'], Decimal('50.00'))
            self.assertEqual(timeline[i]['orders_count'], 1)

        # Settle first statement month (Nov 2026) using Bank account
        res_pay = self.client.post(f'/api/finance/obligations/{bnpl.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '550.00',
            'statement_month': '2026-11'
        }, format='json')
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)

        # Verify bank balance after statement settlement
        bank.refresh_from_db()
        self.assertEqual(bank.current_balance, Decimal('9250.00'))

        # Verify next statement month is now Dec 2026
        summary_after = strategy.get_summary(bnpl)
        self.assertEqual(summary_after['current_statement']['statement_month'], '2026-12')
        self.assertEqual(summary_after['current_statement']['total_due'], Decimal('550.00'))

    def test_attachment_upload_and_pay_with_slip(self):
        """Pillar 3: Contract file upload and slip attachment via Action Pay"""
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='Equipment Loan',
            type=ObligationType.DEBT,
            subtype=ObligationSubtype.FORMAL_LOAN,
            amount=Decimal('10000.00'),
            metadata={'remaining_balance': '10000.00'}
        )

        # 1. Upload contract file via upload-attachment action
        contract_file = SimpleUploadedFile("contract.pdf", b"Contract PDF file contents", content_type="application/pdf")
        res_upload = self.client.post(
            f'/api/finance/obligations/{ob.id}/upload-attachment/',
            {'file': contract_file, 'file_type': 'CONTRACT'},
            format='multipart'
        )
        self.assertEqual(res_upload.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_upload.data['file_name'], 'contract.pdf')
        self.assertEqual(res_upload.data['file_type'], 'CONTRACT')

        # 2. Repay debt with slip attachment
        slip_file = SimpleUploadedFile("slip.jpg", b"Image binary data for slip", content_type="image/jpeg")
        res_pay = self.client.post(
            f'/api/finance/obligations/{ob.id}/pay/',
            {'paid_amount': '2000.00', 'note': 'First installment payment', 'slip_file': slip_file},
            format='multipart'
        )
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        # Payment history and slip attachment created successfully
        history = PaymentHistory.objects.filter(obligation=ob).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.attachments.count(), 1)
        self.assertEqual(history.attachments.first().file_type, 'SLIP')

    def test_debtor_recall_message_template(self):
        """Pillar 2: Debtor recall message template with PromptPay for receivables (INFLOW)"""
        debtor_ob = FinancialObligation.objects.create(
            user=self.user,
            title='Debtor: Somchai Loan',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('8000.00'),
            due_date=date(2026, 11, 15),
            metadata={
                'counterparty': 'Somchai',
                'remaining_balance': '6000.00',
                'promptpay': '0812345678'
            }
        )
        strategy = ObligationStrategyFactory.get_strategy(debtor_ob.type)
        summary = strategy.get_summary(debtor_ob)
        template = summary.get('recall_template', '')
        self.assertIn('Somchai', template)
        self.assertIn('6,000.00', template)
        self.assertIn('0812345678', template)

    def test_bnpl_monthly_bill_payment_advances_sub_orders_and_keeps_parent_active(self):
        """Verify that BNPL bill payment advances sub-orders and keeps parent line ACTIVE"""
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
        # Sub-order 1: 1 term (paying finishes as COMPLETED)
        sub1 = FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='Uniqlo T-Shirt',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('490.00'),
            metadata={'total_terms': 1, 'current_term': 0}
        )
        # Sub-order 2: 3 terms (paying advances to 1/3 and remains ACTIVE)
        sub2 = FinancialObligation.objects.create(
            user=self.user,
            parent=spaylater,
            title='Sony Headphones',
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

        # 1. Parent line must remain ACTIVE
        self.assertEqual(spaylater.status, ObligationStatus.ACTIVE)
        # 2. Sub-order 1 fully paid -> COMPLETED
        self.assertEqual(sub1.status, ObligationStatus.COMPLETED)
        self.assertEqual(sub1.metadata['current_term'], 1)
        # 3. Sub-order 2 advances to term 1 and remains ACTIVE
        self.assertEqual(sub2.status, ObligationStatus.ACTIVE)
        self.assertEqual(sub2.metadata['current_term'], 1)

    def test_file_upload_validation_and_cleanup(self):
        """Check blocked file extensions (.exe) and actual storage file cleanup"""
        import os
        ob = FinancialObligation.objects.create(
            user=self.user,
            title='Test Upload File',
            type=ObligationType.DEBT,
            amount=Decimal('5000.00')
        )

        # 1. Uploading .exe must be rejected (400 Bad Request)
        bad_file = SimpleUploadedFile("malware.exe", b"MZ binary payload", content_type="application/octet-stream")
        res_bad = self.client.post(
            f'/api/finance/obligations/{ob.id}/upload-attachment/',
            {'file': bad_file},
            format='multipart'
        )
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File extension '.exe' is not allowed", res_bad.data['detail'])

        # 2. Upload valid PDF file
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

        # 3. Deleting attachment via API cleans up file
        res_del = self.client.delete(f'/api/finance/attachments/{attachment_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ObligationAttachment.objects.filter(id=attachment_id).exists())
        self.assertFalse(os.path.exists(file_path))

    def test_parent_fk_user_scoping_prevents_idor(self):
        """Security check BOLA/IDOR: User cannot link sub-order to another user account"""
        other_user_ob = FinancialObligation.objects.create(
            user=self.friend,
            title='Friend SPayLater',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00')
        )

        # User attempts to pass parent_id belonging to another user
        res = self.client.post(
            '/api/finance/obligations/',
            {
                'parent': str(other_user_ob.id),
                'title': 'Unauthorized Sub-order',
                'type': 'INSTALLMENT',
                'subtype': 'BNPL_ORDER',
                'amount': '500.00'
            },
            format='json'
        )
        # Validation error (400 Bad Request) because parent belongs to another user
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent', res.data)

    def test_query_filters_direction_search_and_ordering(self):
        """Test API filters: direction, search, and ordering"""
        FinancialObligation.objects.create(
            user=self.user,
            title='Friend Borrowed Money',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('5000.00'),
            metadata={'counterparty': 'Somchai'}
        )
        FinancialObligation.objects.create(
            user=self.user,
            title='Borrowed from Sister',
            type=ObligationType.DEBT,
            direction='OUTFLOW',
            amount=Decimal('10000.00'),
            metadata={'counterparty': 'Sister'}
        )

        # 1. Filter direction=INFLOW
        res_in = self.client.get('/api/finance/obligations/?direction=INFLOW')
        self.assertEqual(res_in.status_code, status.HTTP_200_OK)
        results_in = res_in.data.get('results', res_in.data)
        self.assertEqual(len(results_in), 1)
        self.assertEqual(results_in[0]['title'], 'Friend Borrowed Money')

        # 2. Search search=Somchai
        res_search = self.client.get('/api/finance/obligations/?search=Somchai')
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        results_search = res_search.data.get('results', res_search.data)
        self.assertEqual(len(results_search), 1)

        # 3. Order ordering=-amount
        res_order = self.client.get('/api/finance/obligations/?ordering=-amount')
        self.assertEqual(res_order.status_code, status.HTTP_200_OK)
        results_order = res_order.data.get('results', res_order.data)
        self.assertEqual(results_order[0]['title'], 'Borrowed from Sister')

    def test_installment_schedule_and_debtors_actions(self):
        """Test Action /schedule/ and /debtors/"""
        # Create vehicle installment
        car = FinancialObligation.objects.create(
            user=self.user,
            title='Honda Civic Installment',
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

        # Test Debtors directory
        FinancialObligation.objects.create(
            user=self.user,
            title='Loan: Kitti',
            type=ObligationType.DEBT,
            direction='INFLOW',
            amount=Decimal('15000.00'),
            metadata={'counterparty': 'Kitti'}
        )
        res_debtors = self.client.get('/api/finance/obligations/debtors/')
        self.assertEqual(res_debtors.status_code, status.HTTP_200_OK)
        debtor_names = [d['debtor_name'] for d in res_debtors.data]
        self.assertIn('Kitti', debtor_names)

    def test_audit_split_double_settlement_prevention(self):
        """Audit P1: Settling a split via Finance marks the split settled, preventing double settlement in Ledger."""
        from apps.ledger.models import Account, AccountType, Category, CategoryType
        from apps.ledger.services import BillSplitService

        bank = Account.objects.create(
            user=self.user,
            name='Settlement Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='THB'
        )
        cat = Category.objects.create(
            user=self.user,
            name='Dining Out',
            category_type=CategoryType.EXPENSE
        )
        tx = BillSplitService.create_split_transaction(
            user=self.user,
            account=bank,
            category=cat,
            gross_amount=Decimal('1200.00'),
            net_amount=Decimal('800.00'),
            title="Team Lunch",
            transaction_date=timezone.now().date(),
            splits_data=[{'counterparty_name': 'Friend A', 'amount': '400.00'}],
            auto_create_radar_debtors=True
        )
        split = tx.splits.first()
        debtor = split.debtor_obligation
        self.assertIsNotNone(debtor)
        self.assertFalse(split.is_settled)

        # 1. Settle via Finance pay action
        res = self.client.post(f'/api/finance/obligations/{debtor.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '400.00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify split is marked settled
        split.refresh_from_db()
        self.assertTrue(split.is_settled)
        self.assertIsNotNone(split.settlement_transaction)

        # 2. Attempting to settle again via Ledger settle endpoint must fail
        settle_res = self.client.post(f'/api/ledger/splits/{split.id}/settle/', {
            'deposit_account_id': str(bank.id)
        }, format='json')
        self.assertEqual(settle_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already settled', settle_res.data['error'])

    def test_audit_bnpl_partial_payment_rejection(self):
        """Audit P1: Partial payment on BNPL statement must be rejected with 400."""
        from apps.ledger.models import Account, AccountType

        bank = Account.objects.create(
            user=self.user,
            name='BNPL Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='THB'
        )
        bnpl = FinancialObligation.objects.create(
            user=self.user,
            title='Lazada PayLater',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={'subtype': 'BNPL_ACCOUNT', 'credit_limit': '20000.00'}
        )
        order = FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Monitor',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('1300.00'),
            metadata={'total_terms': 3, 'current_term': 0, 'order_date': '2026-10-01'}
        )
        # Attempt to pay partial 100 on a 1300 statement bill
        res = self.client.post(f'/api/finance/obligations/{bnpl.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '100.00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Partial payment is not supported', res.data['detail'])

        # Verify order term was NOT advanced
        order.refresh_from_db()
        self.assertEqual(order.metadata['current_term'], 0)

    def test_audit_bnpl_ledger_and_history_amount_parity(self):
        """Audit P1: BNPL statement bill payment records identical amount across history and ledger."""
        from apps.ledger.models import Account, AccountType, Transaction

        bank = Account.objects.create(
            user=self.user,
            name='Parity Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='THB'
        )
        bnpl = FinancialObligation.objects.create(
            user=self.user,
            title='Shopee Line',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={'subtype': 'BNPL_ACCOUNT', 'credit_limit': '20000.00'}
        )
        FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Shoes',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('600.00'),
            metadata={'total_terms': 2, 'current_term': 0, 'order_date': '2026-10-01'}
        )

        # Pay without passing paid_amount -> resolves 600.00
        res = self.client.post(f'/api/finance/obligations/{bnpl.id}/pay/', {
            'account_id': str(bank.id)
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify PaymentHistory has 600.00
        hist = PaymentHistory.objects.filter(obligation=bnpl).first()
        self.assertEqual(hist.paid_amount, Decimal('600.00'))

        # Verify Ledger transaction has 600.00 and bank balance reduced by 600.00
        tx = Transaction.objects.filter(obligation=bnpl).first()
        self.assertEqual(tx.gross_amount, Decimal('600.00'))
        bank.refresh_from_db()
        self.assertEqual(bank.current_balance, Decimal('4400.00'))

    def test_audit_installment_partial_and_skip_term_rejection(self):
        """Audit P1: Installment partial payment or skipping terms must be rejected."""
        inst = FinancialObligation.objects.create(
            user=self.user,
            title='iPhone Installment',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('3500.00'),
            metadata={'total_terms': 10, 'current_term': 0}
        )
        # 1. Partial payment rejected
        res1 = self.client.post(f'/api/finance/obligations/{inst.id}/pay/', {
            'paid_amount': '100.00'
        }, format='json')
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Partial payment is not supported', res1.data['detail'])

        # 2. Skipping term (term 3 instead of 1) rejected
        res2 = self.client.post(f'/api/finance/obligations/{inst.id}/pay/', {
            'paid_amount': '3500.00',
            'term_number': 3
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot skip terms', res2.data['detail'])

    def test_audit_debt_overpayment_prevention(self):
        """Audit P1: Paying more than remaining debt balance must be rejected."""
        debt = FinancialObligation.objects.create(
            user=self.user,
            title='Friend Loan',
            type=ObligationType.DEBT,
            direction='OUTFLOW',
            amount=Decimal('1000.00'),
            metadata={'remaining_balance': '500.00'}
        )
        res = self.client.post(f'/api/finance/obligations/{debt.id}/pay/', {
            'paid_amount': '600.00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceeds remaining debt balance', res.data['detail'])

    def test_audit_schedule_amortization_math(self):
        """Audit P1: Zero-interest loan schedule principal sum equals financed amount."""
        loan = FinancialObligation.objects.create(
            user=self.user,
            title='0% Interest Loan',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('5000.00'),
            metadata={
                'total_terms': 10,
                'current_term': 0,
                'financed_amount': '50000.00',
                'flat_rate_pa': '0.00'
            }
        )
        res = self.client.get(f'/api/finance/obligations/{loan.id}/schedule/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        schedule = res.data['schedule']
        self.assertEqual(len(schedule), 10)
        # Principal for each term should be 5000, not 500
        for s in schedule:
            self.assertEqual(Decimal(str(s['principal'])), Decimal('5000.00'))
        self.assertEqual(Decimal(str(schedule[-1]['remaining_principal'])), Decimal('0.00'))

    def test_audit_currency_mismatch_rejection_on_payment(self):
        """Audit P1: Paying obligation with account in different currency must be rejected."""
        from apps.ledger.models import Account, AccountType

        usd_bank = Account.objects.create(
            user=self.user,
            name='USD Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='USD'
        )
        thb_ob = FinancialObligation.objects.create(
            user=self.user,
            title='THB Bill',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('1000.00'),
            currency='THB',
            metadata={'total_terms': 5, 'current_term': 0}
        )
        res = self.client.post(f'/api/finance/obligations/{thb_ob.id}/pay/', {
            'account_id': str(usd_bank.id),
            'paid_amount': '1000.00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Currency mismatch', res.data['detail'])

    def test_audit_bnpl_statement_month_target_matching(self):
        """Audit P1: Paying with target statement_month enforces the exact bill for that month."""
        from apps.ledger.models import Account, AccountType

        bank = Account.objects.create(
            user=self.user,
            name='Target Month Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('10000.00'),
            initial_balance=Decimal('10000.00'),
            currency='THB'
        )
        bnpl = FinancialObligation.objects.create(
            user=self.user,
            title='Shopee Line Multi Month',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={'subtype': 'BNPL_ACCOUNT', 'credit_limit': '20000.00'}
        )
        # Order 1: bought Sep 2026, 1 month -> due Oct 2026 (500)
        FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Sep Order',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('500.00'),
            metadata={'total_terms': 1, 'current_term': 0, 'order_date': '2026-09-15'}
        )
        # Order 2: bought Oct 2026, 1 month -> due Nov 2026 (1300)
        FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Oct Order',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('1300.00'),
            metadata={'total_terms': 1, 'current_term': 0, 'order_date': '2026-10-15'}
        )

        # Attempt to pay 500 with statement_month=2026-11 (which requires 1300)
        res_mismatch = self.client.post(f'/api/finance/obligations/{bnpl.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '500.00',
            'statement_month': '2026-11'
        }, format='json')
        self.assertEqual(res_mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Full statement amount of \u0e3f1,300.00 is required for 2026-11', res_mismatch.data['detail'])

    def test_audit_partial_debt_repayment_keeps_split_unsettled(self):
        """Audit P1: Partial debt repayment keeps linked Split unsettled until paid in full."""
        from apps.ledger.models import Account, AccountType, Category, CategoryType
        from apps.ledger.services import BillSplitService

        bank = Account.objects.create(
            user=self.user,
            name='Partial Repay Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='THB'
        )
        cat = Category.objects.create(
            user=self.user,
            name='Dining Part',
            category_type=CategoryType.EXPENSE
        )
        tx = BillSplitService.create_split_transaction(
            user=self.user,
            account=bank,
            category=cat,
            gross_amount=Decimal('800.00'),
            net_amount=Decimal('400.00'),
            title="Shared Meal Part",
            transaction_date=timezone.now().date(),
            splits_data=[{'counterparty_name': 'Friend P', 'amount': '400.00'}],
            auto_create_radar_debtors=True
        )
        split = tx.splits.first()
        debtor = split.debtor_obligation
        self.assertIsNotNone(debtor)

        # 1. Partial payment 100 out of 400
        res1 = self.client.post(f'/api/finance/obligations/{debtor.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '100.00'
        }, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        debtor.refresh_from_db()
        split.refresh_from_db()
        self.assertEqual(debtor.status, ObligationStatus.ACTIVE)
        self.assertEqual(Decimal(str(debtor.metadata['remaining_balance'])), Decimal('300.00'))
        # Split MUST remain unsettled
        self.assertFalse(split.is_settled)

        # 2. Final payment of remaining 300
        res2 = self.client.post(f'/api/finance/obligations/{debtor.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '300.00'
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        debtor.refresh_from_db()
        split.refresh_from_db()
        self.assertEqual(debtor.status, ObligationStatus.COMPLETED)
        # Split is now settled
        self.assertTrue(split.is_settled)

    def test_audit_reversal_targets_exact_payment_not_latest(self):
        """Audit P1: Deleting a transaction targets the exact linked payment, not the latest one."""
        from apps.ledger.models import Account, AccountType, Transaction

        bank = Account.objects.create(
            user=self.user,
            name='Multi Pay Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('5000.00'),
            initial_balance=Decimal('5000.00'),
            currency='THB'
        )
        debt = FinancialObligation.objects.create(
            user=self.user,
            title='1000 Baht Loan',
            type=ObligationType.DEBT,
            direction='OUTFLOW',
            amount=Decimal('1000.00'),
            metadata={'remaining_balance': '1000.00'}
        )

        # First payment: 100
        res1 = self.client.post(f'/api/finance/obligations/{debt.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '100.00'
        }, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        tx1 = Transaction.objects.filter(obligation=debt, gross_amount=Decimal('100.00')).first()
        self.assertIsNotNone(tx1)

        # Second payment: 200
        res2 = self.client.post(f'/api/finance/obligations/{debt.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '200.00'
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        tx2 = Transaction.objects.filter(obligation=debt, gross_amount=Decimal('200.00')).first()
        self.assertIsNotNone(tx2)

        # Before deletion: 2 payment histories (100 and 200)
        self.assertEqual(debt.payment_histories.count(), 2)
        debt.refresh_from_db()
        self.assertEqual(Decimal(str(debt.metadata['remaining_balance'])), Decimal('700.00'))

        # Delete tx1 (the 100 payment)
        del_res = self.client.delete(f'/api/ledger/transactions/{tx1.id}/')
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        # Remaining payment history must be the 200 payment (NOT the 100 payment)
        self.assertEqual(debt.payment_histories.count(), 1)
        remaining_hist = debt.payment_histories.first()
        self.assertEqual(remaining_hist.paid_amount, Decimal('200.00'))

        # Remaining debt balance should be 800 (1000 - 200)
        debt.refresh_from_db()
        self.assertEqual(Decimal(str(debt.metadata['remaining_balance'])), Decimal('800.00'))

    def test_audit_bnpl_cascade_reversal_restores_sub_orders(self):
        """Audit P1: Reversing BNPL payment restores sub-orders terms and total remaining debt."""
        from apps.ledger.models import Account, AccountType, Transaction

        bank = Account.objects.create(
            user=self.user,
            name='BNPL Reversal Bank',
            account_type=AccountType.BANK,
            current_balance=Decimal('10000.00'),
            initial_balance=Decimal('10000.00'),
            currency='THB'
        )
        bnpl = FinancialObligation.objects.create(
            user=self.user,
            title='Lazada Line Reversal',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ACCOUNT,
            amount=Decimal('0.00'),
            billing_day=10,
            metadata={'subtype': 'BNPL_ACCOUNT', 'credit_limit': '20000.00'}
        )
        order1 = FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Order 1',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('500.00'),
            metadata={'total_terms': 2, 'current_term': 0, 'order_date': '2026-10-01'}
        )
        order2 = FinancialObligation.objects.create(
            user=self.user,
            parent=bnpl,
            title='Order 2',
            type=ObligationType.INSTALLMENT,
            subtype=ObligationSubtype.BNPL_ORDER,
            amount=Decimal('800.00'),
            metadata={'total_terms': 2, 'current_term': 0, 'order_date': '2026-10-01'}
        )

        strategy = ObligationStrategyFactory.get_strategy(bnpl.type)
        summary_before = strategy.get_summary(bnpl)
        self.assertEqual(summary_before['total_remaining_debt'], Decimal('2600.00'))

        # Pay statement bill (1300)
        pay_res = self.client.post(f'/api/finance/obligations/{bnpl.id}/pay/', {
            'account_id': str(bank.id),
            'paid_amount': '1300.00',
            'statement_month': '2026-11'
        }, format='json')
        self.assertEqual(pay_res.status_code, status.HTTP_200_OK)

        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(order1.metadata['current_term'], 1)
        self.assertEqual(order2.metadata['current_term'], 1)

        summary_after_pay = strategy.get_summary(bnpl)
        self.assertEqual(summary_after_pay['total_remaining_debt'], Decimal('1300.00'))

        # Now delete the ledger payment transaction
        tx = Transaction.objects.filter(obligation=bnpl).first()
        self.assertIsNotNone(tx)

        del_res = self.client.delete(f'/api/ledger/transactions/{tx.id}/')
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        # Verify sub-orders are reverted to term 0
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(order1.metadata['current_term'], 0)
        self.assertEqual(order2.metadata['current_term'], 0)

        # Verify total debt restored to 2600
        summary_after_del = strategy.get_summary(bnpl)
        self.assertEqual(summary_after_del['total_remaining_debt'], Decimal('2600.00'))

    def test_audit_schedule_dates_contract_start(self):
        """Audit P1: Schedule term dates remain anchored to contract start after paying term 1."""
        inst = FinancialObligation.objects.create(
            user=self.user,
            title='Phone Contract',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('1000.00'),
            due_date=date(2026, 11, 15),
            metadata={
                'total_terms': 10,
                'current_term': 1,
                'financed_amount': '10000.00'
            }
        )
        res = self.client.get(f'/api/finance/obligations/{inst.id}/schedule/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        schedule = res.data['schedule']
        # Term 1 should be 2026-10-15 (base_date 2026-11-15 minus 1 month)
        self.assertEqual(schedule[0]['due_date'], '2026-10-15')
        # Term 2 should be 2026-11-15
        self.assertEqual(schedule[1]['due_date'], '2026-11-15')

    def test_audit_schedule_zero_financed_amount_fallback(self):
        """Audit P1: Installment schedule with no financed_amount falls back to amount * terms."""
        inst = FinancialObligation.objects.create(
            user=self.user,
            title='Simple Plan',
            type=ObligationType.INSTALLMENT,
            amount=Decimal('100.00'),
            due_date=date(2026, 11, 10),
            metadata={'total_terms': 3, 'current_term': 0}
        )
        res = self.client.get(f'/api/finance/obligations/{inst.id}/schedule/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        schedule = res.data['schedule']
        self.assertEqual(len(schedule), 3)
        for s in schedule:
            self.assertEqual(Decimal(str(s['installment_amount'])), Decimal('100.00'))

    def test_audit_free_trial_on_paid_with_statement_month(self):
        """Audit P1: Free trial on_paid accepts statement_month keyword without TypeError."""
        trial = FinancialObligation.objects.create(
            user=self.user,
            title='Netflix Trial',
            type=ObligationType.FREE_TRIAL,
            amount=Decimal('0.00'),
            metadata={'auto_renew_cost': '299.00'}
        )
        strategy = ObligationStrategyFactory.get_strategy(trial.type)
        summary = strategy.on_paid(trial, paid_amount=Decimal('299.00'), statement_month='2026-11')
        self.assertIsNotNone(summary.get('payment_id'))

    def test_debtor_separation_and_expected_inflow_breakdown_regression(self):
        """
        Regression tests:
        1. MA A (6,000 THB) + MA B (6,000 THB) recurring in-scope, no DEBT:
           - active_debtor_records_count == 0
           - debtors directory is empty
           - expected_inflow_amount == 12,000.00 THB
           - breakdown has MA A 6,000 + MA B 6,000, and sum equals 12,000.00 THB
        2. Inflow DEBT with partial payment:
           - uses remaining balance
           - counted as 1 active debtor
        3. Outflow DEBT:
           - not counted in debtors or expected inflow
        4. Zero remaining / cancelled DEBT:
           - not counted as active debtor
        5. Multi-user isolation:
           - User 2's data does not bleed into User 1
        """
        target_date = date(2026, 10, 15)

        # Clear existing active obligations for this user for a pristine test scenario
        FinancialObligation.objects.filter(user=self.user).delete()

        # Step 1: Create MA A = 6,000 THB, MA B = 6,000 THB
        ma_a = FinancialObligation.objects.create(
            user=self.user,
            title='MA: Project Alpha',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('6000.00'),
            currency='THB',
            due_date=date(2026, 10, 25),
            metadata={'source_type': 'MA_CONTRACT', 'billing_cycle': 'MONTHLY', 'client_name': 'Client Alpha'}
        )
        ma_b = FinancialObligation.objects.create(
            user=self.user,
            title='MA: Project Beta',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('6000.00'),
            currency='THB',
            due_date=date(2026, 10, 28),
            metadata={'source_type': 'MA_CONTRACT', 'billing_cycle': 'MONTHLY', 'client_name': 'Client Beta'}
        )

        overview = get_financial_overview(self.user, target_date=target_date)

        # DEBT debtors count must be 0
        self.assertEqual(overview['active_debtor_records_count'], 0)
        self.assertEqual(overview['debt_total_count'], 0)

        # Debtors directory API endpoint must be empty
        res_debtors = self.client.get('/api/finance/obligations/debtors/')
        self.assertEqual(res_debtors.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_debtors.data), 0)

        # Expected inflow must be 12,000.00 THB
        self.assertEqual(overview['expected_inflow_amount'], Decimal('12000.00'))
        breakdown = overview['expected_inflow_breakdown']
        self.assertEqual(breakdown['ma_amount'], Decimal('12000.00'))
        self.assertEqual(breakdown['debt_amount'], Decimal('0.00'))
        self.assertEqual(len(breakdown['items']), 2)
        items_sum = sum((item['amount_thb'] for item in breakdown['items']), Decimal('0.00'))
        self.assertEqual(items_sum, overview['expected_inflow_amount'])

        # Step 2: Add DEBT (INFLOW) 10,000 THB with partial payment of 4,000 THB -> remaining 6,000 THB
        debt_in = FinancialObligation.objects.create(
            user=self.user,
            title='Lent to Friend Bob',
            type=ObligationType.DEBT,
            direction=FlowDirection.INFLOW,
            amount=Decimal('10000.00'),
            currency='THB',
            due_date=date(2026, 10, 30),
            metadata={'counterparty': 'Bob', 'remaining_balance': '6000.00'}
        )
        overview2 = get_financial_overview(self.user, target_date=target_date)
        self.assertEqual(overview2['active_debtor_records_count'], 1)
        self.assertEqual(overview2['debt_total_count'], 1)
        self.assertEqual(overview2['total_debtors_outstanding_amount'], Decimal('6000.00'))
        # Expected inflow is now 12,000 (MA) + 6,000 (DEBT remaining) = 18,000.00
        self.assertEqual(overview2['expected_inflow_amount'], Decimal('18000.00'))
        self.assertEqual(overview2['expected_inflow_breakdown']['debt_amount'], Decimal('6000.00'))
        self.assertEqual(overview2['expected_inflow_breakdown']['ma_amount'], Decimal('12000.00'))
        self.assertEqual(len(overview2['expected_inflow_breakdown']['items']), 3)

        # Step 3: Add OUTFLOW debt (user owes someone)
        debt_out = FinancialObligation.objects.create(
            user=self.user,
            title='Borrowed from Alice',
            type=ObligationType.DEBT,
            direction=FlowDirection.OUTFLOW,
            amount=Decimal('5000.00'),
            currency='THB',
            due_date=date(2026, 10, 20),
            metadata={'counterparty': 'Alice', 'remaining_balance': '5000.00'}
        )
        overview3 = get_financial_overview(self.user, target_date=target_date)
        # OUTFLOW must NOT increase active_debtor_records_count or expected_inflow_amount
        self.assertEqual(overview3['active_debtor_records_count'], 1)
        self.assertEqual(overview3['expected_inflow_amount'], Decimal('18000.00'))
        self.assertEqual(overview3['debt_total_count'], 2)

        # Step 4: Add completed/zero-balance DEBT
        debt_completed = FinancialObligation.objects.create(
            user=self.user,
            title='Lent to Charlie (Paid)',
            type=ObligationType.DEBT,
            direction=FlowDirection.INFLOW,
            status=ObligationStatus.COMPLETED,
            amount=Decimal('3000.00'),
            currency='THB',
            due_date=date(2026, 10, 10),
            metadata={'counterparty': 'Charlie', 'remaining_balance': '0.00'}
        )
        overview4 = get_financial_overview(self.user, target_date=target_date)
        self.assertEqual(overview4['active_debtor_records_count'], 1)
        self.assertEqual(overview4['expected_inflow_amount'], Decimal('18000.00'))

        # Step 5: Multi-currency - Add USD MA subscription $200
        usd_rate = get_exchange_rate_to_thb('USD')
        ma_usd = FinancialObligation.objects.create(
            user=self.user,
            title='MA: Global Client',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('200.00'),
            currency='USD',
            due_date=date(2026, 10, 20),
            metadata={'source_type': 'MA_CONTRACT', 'billing_cycle': 'MONTHLY', 'client_name': 'Global Client'}
        )
        overview5 = get_financial_overview(self.user, target_date=target_date)
        usd_thb = (Decimal('200.00') * usd_rate).quantize(Decimal('0.01'))
        expected_total = Decimal('18000.00') + usd_thb
        self.assertEqual(overview5['expected_inflow_amount'], expected_total)
        # Breakdown sum matches expected total
        items_sum5 = sum((item['amount_thb'] for item in overview5['expected_inflow_breakdown']['items']), Decimal('0.00'))
        self.assertEqual(items_sum5, expected_total)

        # Step 6: Pagination test - add 25 more DEBT INFLOW records
        for i in range(25):
            FinancialObligation.objects.create(
                user=self.user,
                title=f'Debtor #{i+1}',
                type=ObligationType.DEBT,
                direction=FlowDirection.INFLOW,
                amount=Decimal('100.00'),
                currency='THB',
                due_date=date(2026, 10, 25),
                metadata={'counterparty': f'Debtor #{i+1}', 'remaining_balance': '100.00'}
            )
        overview6 = get_financial_overview(self.user, target_date=target_date)
        # 1 existing debtor + 25 new debtors = 26 active debtor records
        self.assertEqual(overview6['active_debtor_records_count'], 26)
        # Breakdown item count = 3 MA + 1 original debt + 25 new debts = 29 items
        self.assertEqual(len(overview6['expected_inflow_breakdown']['items']), 29)
        items_sum6 = sum((item['amount_thb'] for item in overview6['expected_inflow_breakdown']['items']), Decimal('0.00'))
        self.assertEqual(items_sum6, overview6['expected_inflow_amount'])

        # Step 7: Multi-user isolation
        friend_overview = get_financial_overview(self.friend, target_date=target_date)
        self.assertEqual(friend_overview['active_debtor_records_count'], 0)
        self.assertEqual(friend_overview['expected_inflow_amount'], Decimal('0.00'))
        self.assertEqual(len(friend_overview['expected_inflow_breakdown']['items']), 0)

    def test_monthly_due_date_weekly_actual_occurrences_and_project_ma_separation(self):
        """
        Verify:
        1. Monthly subscription scheduled next month is excluded this month.
        2. Recording payment advances due date to next month, excluding it from this month's pending inflow.
        3. Weekly subscription calculates actual calendar occurrences in the target month (e.g. 5 dates * 1,000 = 5,000).
        4. When a weekly installment is paid, remaining occurrences reflect paid status (e.g. 4 * 1,000 = 4,000).
        5. Inflow subscription linked to CLIENT_DEV project without source_type=MA_CONTRACT is categorized as RECURRING, not MA.
        6. Inflow installment respects due_date month matching.
        """
        from apps.workspace.models import WorkspaceProject, ProjectType

        october = date(2026, 10, 15)
        FinancialObligation.objects.filter(user=self.user).delete()

        # 1. Monthly subscription starting in November (2026-11-20)
        sub_nov = FinancialObligation.objects.create(
            user=self.user,
            title='Contract Nov Start',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('6000.00'),
            currency='THB',
            due_date=date(2026, 11, 20),
            metadata={'billing_cycle': 'MONTHLY'}
        )
        overview_oct = get_financial_overview(self.user, target_date=october)
        # In October, should be 0 because due date is in November!
        self.assertEqual(overview_oct['expected_inflow_amount'], Decimal('0.00'))

        # In November, should be 6,000.00
        november = date(2026, 11, 15)
        overview_nov = get_financial_overview(self.user, target_date=november)
        self.assertEqual(overview_nov['expected_inflow_amount'], Decimal('6000.00'))

        # 2. Monthly subscription due in October (2026-10-20), recorded payment shifts to November
        sub_oct = FinancialObligation.objects.create(
            user=self.user,
            title='Contract Oct Due',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('3000.00'),
            currency='THB',
            due_date=date(2026, 10, 20),
            metadata={'billing_cycle': 'MONTHLY'}
        )
        overview_oct2 = get_financial_overview(self.user, target_date=october)
        self.assertEqual(overview_oct2['expected_inflow_amount'], Decimal('3000.00'))

        # Record payment for October -> due_date moves to 2026-11-20
        strategy = ObligationStrategyFactory.get_strategy(sub_oct.type)
        strategy.on_paid(sub_oct, paid_amount=Decimal('3000.00'))
        sub_oct.refresh_from_db()
        self.assertEqual(sub_oct.due_date, date(2026, 11, 20))

        # After payment, October pending inflow no longer includes it
        overview_oct3 = get_financial_overview(self.user, target_date=october)
        self.assertEqual(overview_oct3['expected_inflow_amount'], Decimal('0.00'))

        # Clean up for next test
        FinancialObligation.objects.filter(user=self.user).delete()

        # 3. Weekly subscription: 1,000 THB/week with due date 2026-10-02
        # In October 2026: Fridays are 2, 9, 16, 23, 30 -> exactly 5 occurrences
        sub_weekly = FinancialObligation.objects.create(
            user=self.user,
            title='Weekly Consulting Inflow',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('1000.00'),
            currency='THB',
            due_date=date(2026, 10, 2),
            metadata={'billing_cycle': 'WEEKLY'}
        )
        overview_weekly = get_financial_overview(self.user, target_date=october)
        # 5 occurrences * 1,000 THB = 5,000.00 THB (NOT 4,333.30)
        self.assertEqual(overview_weekly['expected_inflow_amount'], Decimal('5000.00'))
        self.assertEqual(overview_weekly['expected_inflow_breakdown']['recurring_amount'], Decimal('5000.00'))

        # 4. Record 1 week payment -> due date moves to 2026-10-09
        strategy_weekly = ObligationStrategyFactory.get_strategy(sub_weekly.type)
        strategy_weekly.on_paid(sub_weekly, paid_amount=Decimal('1000.00'))
        sub_weekly.refresh_from_db()
        self.assertEqual(sub_weekly.due_date, date(2026, 10, 9))

        # Remaining in October: 9, 16, 23, 30 -> 4 occurrences = 4,000.00 THB
        overview_weekly2 = get_financial_overview(self.user, target_date=october)
        self.assertEqual(overview_weekly2['expected_inflow_amount'], Decimal('4000.00'))

        # 5. Project CLIENT_DEV subscription (linked to project, but NOT MA_CONTRACT)
        project_dev = WorkspaceProject.objects.create(
            user=self.user,
            name='Client Dev Portal',
            project_type=ProjectType.CLIENT_DEV
        )
        sub_dev = FinancialObligation.objects.create(
            user=self.user,
            title='Dev Retainer',
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=Decimal('8000.00'),
            currency='THB',
            due_date=date(2026, 10, 25),
            project=project_dev,
            metadata={'project_id': str(project_dev.id), 'billing_cycle': 'MONTHLY'}
        )
        overview_dev = get_financial_overview(self.user, target_date=october)
        # sub_weekly (4,000) + sub_dev (8,000) = 12,000
        self.assertEqual(overview_dev['expected_inflow_amount'], Decimal('12000.00'))
        # sub_dev must be categorized as RECURRING, NOT MA!
        self.assertEqual(overview_dev['expected_inflow_breakdown']['ma_amount'], Decimal('0.00'))
        self.assertEqual(overview_dev['expected_inflow_breakdown']['recurring_amount'], Decimal('12000.00'))
        dev_item = next(i for i in overview_dev['expected_inflow_breakdown']['items'] if i['id'] == str(sub_dev.id))
        self.assertEqual(dev_item['category'], 'RECURRING')

        # 6. Inflow installment: due in Oct vs due in Nov
        inst_oct = FinancialObligation.objects.create(
            user=self.user,
            title='Sold Laptop Installment Oct',
            type=ObligationType.INSTALLMENT,
            direction=FlowDirection.INFLOW,
            amount=Decimal('2500.00'),
            currency='THB',
            due_date=date(2026, 10, 28),
            metadata={'total_terms': 4, 'current_term': 1}
        )
        inst_nov = FinancialObligation.objects.create(
            user=self.user,
            title='Sold Laptop Installment Nov',
            type=ObligationType.INSTALLMENT,
            direction=FlowDirection.INFLOW,
            amount=Decimal('2500.00'),
            currency='THB',
            due_date=date(2026, 11, 28),
            metadata={'total_terms': 4, 'current_term': 2}
        )
        overview_inst = get_financial_overview(self.user, target_date=october)
        # inst_oct is included (+2,500), inst_nov is excluded
        self.assertEqual(overview_inst['expected_inflow_amount'], Decimal('14500.00'))
        inst_item = next(i for i in overview_inst['expected_inflow_breakdown']['items'] if i['id'] == str(inst_oct.id))
        self.assertEqual(inst_item['type'], ObligationType.INSTALLMENT)
        self.assertFalse(any(i['id'] == str(inst_nov.id) for i in overview_inst['expected_inflow_breakdown']['items']))
