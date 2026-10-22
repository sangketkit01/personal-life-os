from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from apps.finance.models import FinancialObligation, ObligationStatus, PaymentHistory
from .models import (
    Account,
    AccountType,
    Category,
    CategoryType,
    Transaction,
    TransactionType,
    TransactionSplit,
    CategoryBudget
)
from .services import AccountBalanceService, BillSplitService, CategorySeedService

User = get_user_model()


class LedgerAccountTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testledger', password='password123')
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(
            user=self.user,
            name="KBANK Savings",
            account_type=AccountType.BANK,
            currency="THB",
            initial_balance=Decimal('10000.00'),
            current_balance=Decimal('10000.00')
        )

    def test_account_creation_and_balance_flow(self):
        # 1. Inflow transaction (Deposit)
        inflow = Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.INFLOW,
            gross_amount=Decimal('5000.00'),
            net_amount=Decimal('5000.00'),
            title="Freelance Payment",
            transaction_date=timezone.now().date()
        )
        self.account.current_balance += inflow.gross_amount
        self.account.save()

        self.assertEqual(self.account.current_balance, Decimal('15000.00'))

        # 2. Outflow transaction (Withdrawal)
        outflow = Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.OUTFLOW,
            gross_amount=Decimal('3000.00'),
            net_amount=Decimal('3000.00'),
            title="Groceries",
            transaction_date=timezone.now().date()
        )
        self.account.current_balance -= outflow.gross_amount
        self.account.save()

        self.assertEqual(self.account.current_balance, Decimal('12000.00'))

        # 3. Recalculate balance service
        recalculated = AccountBalanceService.recalculate_account_balance(self.account)
        self.assertEqual(recalculated, Decimal('12000.00'))

    def test_atomic_transfer_between_accounts(self):
        target_account = Account.objects.create(
            user=self.user,
            name="Dime! Cash",
            account_type=AccountType.BROKERAGE_CASH,
            currency="THB",
            initial_balance=Decimal('2000.00'),
            current_balance=Decimal('2000.00')
        )

        out_tx, in_tx = AccountBalanceService.execute_transfer(
            user=self.user,
            source_account=self.account,
            target_account=target_account,
            amount=Decimal('4000.00'),
            transaction_date=timezone.now().date(),
            title="Top up Dime brokerage"
        )

        self.account.refresh_from_db()
        target_account.refresh_from_db()

        self.assertEqual(self.account.current_balance, Decimal('6000.00'))
        self.assertEqual(target_account.current_balance, Decimal('6000.00'))
        self.assertEqual(out_tx.transfer_peer, in_tx)
        self.assertEqual(in_tx.transfer_peer, out_tx)

    def test_transfer_validation(self):
        with self.assertRaises(ValueError):
            AccountBalanceService.execute_transfer(
                user=self.user,
                source_account=self.account,
                target_account=self.account, # same account
                amount=Decimal('500.00'),
                transaction_date=timezone.now().date()
            )

        with self.assertRaises(ValueError):
            AccountBalanceService.execute_transfer(
                user=self.user,
                source_account=self.account,
                target_account=Account.objects.create(user=self.user, name="Cash", initial_balance=0),
                amount=Decimal('-100.00'), # negative amount
                transaction_date=timezone.now().date()
            )


class BillSplitServiceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testsplit', password='password123')
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(
            user=self.user,
            name="KBANK Credit",
            account_type=AccountType.CREDIT_CARD,
            currency="THB",
            initial_balance=Decimal('0.00'),
            current_balance=Decimal('0.00')
        )
        self.category = Category.objects.create(
            name="Dining",
            category_type=CategoryType.EXPENSE,
            user=self.user
        )

    def test_create_split_bill_with_auto_radar_debtors(self):
        # Shabu bill ฿2,400. 4 people (฿600 each). My share = ฿600.
        splits_data = [
            {'counterparty_name': 'Ball', 'counterparty_contact': '0811111111', 'amount': '600.00'},
            {'counterparty_name': 'Earth', 'counterparty_contact': '0822222222', 'amount': '600.00'},
            {'counterparty_name': 'Bank', 'counterparty_contact': '0833333333', 'amount': '600.00'},
        ]

        tx = BillSplitService.create_split_transaction(
            user=self.user,
            account=self.account,
            category=self.category,
            gross_amount=Decimal('2400.00'),
            net_amount=Decimal('600.00'),
            title="Haidilao Shabu CentralWorld",
            transaction_date=timezone.now().date(),
            splits_data=splits_data,
            auto_create_radar_debtors=True
        )

        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('-2400.00')) # credit card charged
        self.assertEqual(tx.gross_amount, Decimal('2400.00'))
        self.assertEqual(tx.net_amount, Decimal('600.00'))
        self.assertEqual(tx.splits.count(), 3)

        # Check Financial Radar Debtors auto-creation
        ball_split = tx.splits.get(counterparty_name='Ball')
        self.assertIsNotNone(ball_split.debtor_obligation)
        self.assertEqual(ball_split.debtor_obligation.amount, Decimal('600.00'))
        self.assertEqual(ball_split.debtor_obligation.direction, 'INFLOW')
        self.assertEqual(ball_split.debtor_obligation.status, ObligationStatus.ACTIVE)

        # Settle Ball's share into KBANK
        settle_account = Account.objects.create(
            user=self.user,
            name="KBANK Savings",
            initial_balance=Decimal('1000.00'),
            current_balance=Decimal('1000.00')
        )

        inflow_tx = BillSplitService.settle_split(
            split=ball_split,
            deposit_account=settle_account
        )

        ball_split.refresh_from_db()
        settle_account.refresh_from_db()

        self.assertTrue(ball_split.is_settled)
        self.assertEqual(settle_account.current_balance, Decimal('1600.00')) # 1000 + 600
        self.assertEqual(ball_split.debtor_obligation.status, ObligationStatus.COMPLETED)
        self.assertTrue(PaymentHistory.objects.filter(obligation=ball_split.debtor_obligation).exists())


class LedgerAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='password123')
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(
            user=self.user,
            name="Main Checking",
            account_type=AccountType.BANK,
            initial_balance=Decimal('50000.00'),
            current_balance=Decimal('50000.00')
        )
        CategorySeedService.seed_defaults()
        self.food_category = Category.objects.filter(name="Food & Dining").first()
        self.salary_category = Category.objects.filter(name="Salary & Wages").first()

    def test_category_api(self):
        response = self.client.get('/api/ledger/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_create_transaction_api(self):
        payload = {
            'account': str(self.account.id),
            'transaction_type': 'OUTFLOW',
            'category': str(self.food_category.id),
            'gross_amount': '350.00',
            'net_amount': '350.00',
            'title': 'Lunch Cafe',
            'transaction_date': timezone.now().date().isoformat()
        }
        response = self.client.post('/api/ledger/transactions/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('49650.00'))

    def test_summary_api(self):
        today = timezone.now().date()
        # Inflow 30,000
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.INFLOW,
            category=self.salary_category,
            gross_amount=Decimal('30000.00'),
            net_amount=Decimal('30000.00'),
            title="Monthly Salary",
            transaction_date=today
        )

        # Split expense 3,000 (net 1,000, 2 friends 2,000)
        BillSplitService.create_split_transaction(
            user=self.user,
            account=self.account,
            category=self.food_category,
            gross_amount=Decimal('3000.00'),
            net_amount=Decimal('1000.00'),
            title="Team Dinner",
            transaction_date=today,
            splits_data=[
                {'counterparty_name': 'Alice', 'amount': '1000.00'},
                {'counterparty_name': 'Bob', 'amount': '1000.00'}
            ]
        )

        current_month = today.strftime('%Y-%m')
        response = self.client.get(f'/api/ledger/transactions/summary/?month={current_month}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(Decimal(data['total_inflow']), Decimal('30000.00'))
        self.assertEqual(Decimal(data['total_gross_outflow']), Decimal('3000.00'))
        self.assertEqual(Decimal(data['total_net_outflow']), Decimal('1000.00'))
        # Net cash flow should be 30,000 - 1,000 (net personal spend) = 29,000
        self.assertEqual(Decimal(data['net_cash_flow']), Decimal('29000.00'))
        self.assertEqual(Decimal(data['pending_splits_amount']), Decimal('2000.00'))
        self.assertEqual(data['pending_splits_count'], 2)

    def test_budget_api(self):
        budget = CategoryBudget.objects.create(
            user=self.user,
            category=self.food_category,
            period_month=timezone.now().strftime('%Y-%m'),
            limit_amount=Decimal('10000.00')
        )

        Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.OUTFLOW,
            category=self.food_category,
            gross_amount=Decimal('2500.00'),
            net_amount=Decimal('2500.00'),
            title="Weekly Meal Prep",
            transaction_date=timezone.now().date()
        )

        response = self.client.get('/api/ledger/budgets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        b_data = response.data[0]
        self.assertEqual(Decimal(b_data['spent_amount']), Decimal('2500.00'))
        self.assertEqual(Decimal(b_data['remaining_amount']), Decimal('7500.00'))
        self.assertEqual(b_data['usage_pct'], 25.0)

    def test_bola_protection_on_foreign_account(self):
        # User B cannot use User A's account in transactions
        other_user = User.objects.create_user(username='otheruser', password='password123')
        other_account = Account.objects.create(
            user=other_user,
            name="Victim Savings",
            initial_balance=Decimal('10000.00'),
            current_balance=Decimal('10000.00')
        )

        payload = {
            'account': str(other_account.id),
            'transaction_type': 'OUTFLOW',
            'gross_amount': '500.00',
            'title': 'Theft Attempt',
            'transaction_date': timezone.now().date().isoformat()
        }
        response = self.client.post('/api/ledger/transactions/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('account', response.data)

        # Ensure victim account was untouched
        other_account.refresh_from_db()
        self.assertEqual(other_account.current_balance, Decimal('10000.00'))

    def test_system_category_cannot_be_deleted_or_modified(self):
        system_cat = Category.objects.filter(is_system=True).first()
        self.assertIsNotNone(system_cat)

        # Attempt DELETE
        del_response = self.client.delete(f'/api/ledger/categories/{system_cat.id}/')
        self.assertEqual(del_response.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt PATCH
        patch_response = self.client.patch(f'/api/ledger/categories/{system_cat.id}/', {'name': 'Hacked'}, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_transfer_cascade_delete(self):
        target_account = Account.objects.create(
            user=self.user,
            name="Vault",
            initial_balance=Decimal('1000.00'),
            current_balance=Decimal('1000.00')
        )

        out_tx, in_tx = AccountBalanceService.execute_transfer(
            user=self.user,
            source_account=self.account,
            target_account=target_account,
            amount=Decimal('500.00'),
            transaction_date=timezone.now().date()
        )

        self.account.refresh_from_db()
        target_account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('49500.00'))
        self.assertEqual(target_account.current_balance, Decimal('1500.00'))

        # Delete the outflow transfer
        del_resp = self.client.delete(f'/api/ledger/transactions/{out_tx.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Both transactions should be gone and both balances reverted
        self.assertFalse(Transaction.objects.filter(id=out_tx.id).exists())
        self.assertFalse(Transaction.objects.filter(id=in_tx.id).exists())

        self.account.refresh_from_db()
        target_account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('50000.00'))
        self.assertEqual(target_account.current_balance, Decimal('1000.00'))

    def test_split_settlement_revert_on_delete(self):
        # 1. Create a split bill
        tx = BillSplitService.create_split_transaction(
            user=self.user,
            account=self.account,
            category=self.food_category,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('500.00'),
            title="Lunch with Somchai",
            transaction_date=timezone.now().date(),
            splits_data=[{'counterparty_name': 'Somchai', 'amount': '500.00'}],
            auto_create_radar_debtors=True
        )
        split = tx.splits.first()
        self.assertFalse(split.is_settled)

        # 2. Settle split
        settle_account = Account.objects.create(
            user=self.user,
            name="Cash Wallet",
            initial_balance=Decimal('100.00'),
            current_balance=Decimal('100.00')
        )
        inflow_tx = BillSplitService.settle_split(split=split, deposit_account=settle_account)
        split.refresh_from_db()
        self.assertTrue(split.is_settled)
        self.assertEqual(split.debtor_obligation.status, ObligationStatus.COMPLETED)

        # 3. Delete the inflow repayment transaction
        del_resp = self.client.delete(f'/api/ledger/transactions/{inflow_tx.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Verify split is reverted back to pending and radar debtor reopened
        split.refresh_from_db()
        self.assertFalse(split.is_settled)
        self.assertIsNone(split.settlement_transaction)
        self.assertEqual(split.debtor_obligation.status, ObligationStatus.ACTIVE)

        settle_account.refresh_from_db()
        self.assertEqual(settle_account.current_balance, Decimal('100.00'))

    def test_transaction_patch_amount_adjusts_balance(self):
        tx = Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.OUTFLOW,
            category=self.food_category,
            gross_amount=Decimal('200.00'),
            net_amount=Decimal('200.00'),
            title="Coffee",
            transaction_date=timezone.now().date()
        )
        self.account.current_balance -= Decimal('200.00')
        self.account.save()
        self.assertEqual(self.account.current_balance, Decimal('49800.00'))

        # PATCH gross_amount to 500 (extra 300 outflow)
        patch_resp = self.client.patch(
            f'/api/ledger/transactions/{tx.id}/',
            {'gross_amount': '500.00'},
            format='json'
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal('49500.00')) # 49800 - 300

    def test_hierarchical_budget_includes_subcategories(self):
        sub_cat = Category.objects.create(
            user=self.user,
            name="Artisan Coffee",
            category_type=CategoryType.EXPENSE,
            parent=self.food_category
        )

        budget = CategoryBudget.objects.create(
            user=self.user,
            category=self.food_category,
            period_month=timezone.now().strftime('%Y-%m'),
            limit_amount=Decimal('1000.00')
        )

        # Spent on subcategory
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.OUTFLOW,
            category=sub_cat,
            gross_amount=Decimal('350.00'),
            net_amount=Decimal('350.00'),
            title="Drip Coffee",
            transaction_date=timezone.now().date()
        )

        resp = self.client.get('/api/ledger/budgets/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        b_item = [b for b in resp.data if b['id'] == str(budget.id)][0]
        self.assertEqual(Decimal(b_item['spent_amount']), Decimal('350.00'))
        self.assertEqual(Decimal(b_item['remaining_amount']), Decimal('650.00'))
        self.assertEqual(b_item['usage_pct'], 35.0)

    def test_account_delete_protection(self):
        # Account has transactions
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            transaction_type=TransactionType.INFLOW,
            gross_amount=Decimal('100.00'),
            net_amount=Decimal('100.00'),
            title="Deposit",
            transaction_date=timezone.now().date()
        )

        del_resp = self.client.delete(f'/api/ledger/accounts/{self.account.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot delete an account', del_resp.data['error'])
