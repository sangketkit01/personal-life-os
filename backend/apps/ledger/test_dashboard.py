from datetime import date, datetime, timezone as dtz, timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Account, Category, CategoryBudget, Transaction, TransactionSplit
from apps.finance.models import FinancialObligation


class DashboardTests(TestCase):
    def setUp(self):
        self.clock = patch('django.utils.timezone.now', return_value=datetime(2026,10,15,5,tzinfo=dtz.utc))
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.user = get_user_model().objects.create_user(username='dashboard', password='test')
        self.other = get_user_model().objects.create_user(username='dashboard-other', password='test')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.bank = self.account('Bank','BANK',50000)
        self.wallet = self.account('Cash','CASH',10000)
        self.card = self.account('Card','CREDIT_CARD',-400)
        self.broker = self.account('Broker','BROKERAGE_CASH',1000)
        self.usd = self.account('USD','BANK',500,'USD')
        self.category = Category.objects.create(user=self.user, name='Living', category_type='EXPENSE')
        self.child = Category.objects.create(user=self.user, name='Food', category_type='EXPENSE', parent=self.category)

    def account(self,name,kind,balance,currency='THB'):
        return Account.objects.create(user=self.user,name=name,account_type=kind,currency=currency,initial_balance=balance,current_balance=balance)

    def tx(self, amount, direction='OUTFLOW', account=None, day='2026-10-10', **extra):
        response = self.client.post('/api/ledger/transactions/', {'account':str((account or self.bank).id),
            'transaction_type':direction, 'gross_amount':str(amount), 'net_amount':str(amount), 'title':'Recorded', 'transaction_date':day, **extra},format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def transfer(self,destination,amount):
        response = self.client.post('/api/ledger/accounts/transfer/', {'source_account_id':str(self.bank.id),
            'target_account_id':str(destination.id),'amount':str(amount),'transaction_date':'2026-10-10'},format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def report(self, currency='THB', month='2026-10'):
        response = self.client.get('/api/ledger/transactions/dashboard/', {'month':month,'currency':currency})
        self.assertEqual(response.status_code,200,response.data)
        return response.data

    def test_personal_expenses_and_available_cash_are_distinct_and_reconcile(self):
        self.tx(10000,'INFLOW')
        shared = self.tx(1200, category=str(self.child.id), net_amount='400', auto_create_radar_debtors=False,
            splits_payload=[{'counterparty_name':'Friend','amount':'800'}])
        split = TransactionSplit.objects.get(transaction_id=shared['id'])
        response = self.client.post(f'/api/ledger/splits/{split.id}/settle/',{'deposit_account_id':str(self.bank.id),'settlement_date':'2026-10-12'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.transfer(self.wallet,1000)
        self.transfer(self.card,300)
        self.transfer(self.broker,700)
        self.tx(2000,'INFLOW',reporting_kind='LOAN')
        self.tx(500,reporting_kind='INVESTMENT')
        self.tx(200,'INFLOW',reporting_kind='REIMBURSEMENT')
        self.tx(400,account=self.card)
        self.tx(100,reporting_kind='LOAN')
        self.tx(100,reporting_kind='CARD_PAYMENT')
        result = self.report()
        self.assertEqual(Decimal(result['metrics']['income']),Decimal('10000'))
        self.assertEqual(Decimal(result['metrics']['expense']),Decimal('800'))
        self.assertEqual(Decimal(result['metrics']['cash_in']),Decimal('13000'))
        self.assertEqual(Decimal(result['metrics']['cash_out']),Decimal('2900'))
        self.assertEqual(Decimal(result['liquid_balance']),Decimal('70100'))
        self.assertEqual(Decimal(result['credit_debt']),Decimal('500'))
        self.assertEqual(Decimal(result['expense_categories'][0]['amount']),Decimal('400'))
        for kind,key in [('INCOME','income'),('EXPENSE','expense')]:
            response = self.client.get('/api/ledger/transactions/',{'currency':'THB','report_kind':kind,'start_date':'2026-10-01','end_date':'2026-10-15'})
            self.assertEqual(response.status_code,200,response.data)
            amount = sum((Decimal(str(tx['net_amount'] if kind=='EXPENSE' else tx['gross_amount'])) for tx in response.data['results']),Decimal('0'))
            self.assertEqual(amount,Decimal(result['metrics'][key]))

    def test_reimbursement_in_later_month_does_not_become_income(self):
        self.tx(1200, day='2026-09-12', net_amount='400', auto_create_radar_debtors=False,
            splits_payload=[{'counterparty_name':'Friend','amount':'800'}])
        split=TransactionSplit.objects.get()
        self.client.post(f'/api/ledger/splits/{split.id}/settle/', {'deposit_account_id':str(self.bank.id),'settlement_date':'2026-10-10'},format='json')
        result=self.report()
        self.assertEqual(Decimal(result['metrics']['income']),0)
        self.assertEqual(Decimal(result['metrics']['cash_in']),800)
        self.assertEqual(Decimal(self.report(month='2026-09')['metrics']['expense']),400)

    def test_future_postings_do_not_change_current_available_cash_or_actual_metrics(self):
        self.tx(1000,day='2026-11-01')
        self.tx(2000,'INFLOW',day='2026-11-02')
        result=self.report()
        self.assertEqual(Decimal(result['liquid_balance']),60000)
        self.assertEqual(Decimal(result['metrics']['income']),0)
        self.assertEqual(Decimal(result['metrics']['expense']),0)
        self.assertEqual(self.report(month='2026-11')['recent'],[])

    def test_currency_and_owner_isolation_in_metrics_drilldown_and_accounts(self):
        self.tx(700,'INFLOW',account=self.usd)
        foreign=Account.objects.create(user=self.other,name='Private',account_type='BANK',currency='THB',current_balance=999999)
        Transaction.objects.create(user=self.other,account=foreign,transaction_type='INFLOW',gross_amount=999999,net_amount=999999,title='Private',transaction_date=date(2026,10,10))
        self.assertEqual(Decimal(self.report()['metrics']['income']),0)
        self.assertEqual(Decimal(self.report('USD')['metrics']['income']),700)
        response=self.client.get('/api/ledger/transactions/',{'currency':'THB','report_kind':'INCOME'})
        self.assertEqual(response.data['count'],0)
        self.assertNotIn(str(foreign.id),[a['id'] for a in self.report()['accounts']])

    def test_archived_accounts_still_contribute_historical_activity(self):
        self.tx(300,'INFLOW')
        self.bank.is_archived=True
        self.bank.save()
        result=self.report()
        self.assertEqual(Decimal(result['metrics']['income']),300)
        self.assertEqual(Decimal(result['liquid_balance']),10000)

    def test_comparison_uses_equal_elapsed_days_and_complete_past_months(self):
        self.tx(100,'INFLOW',day='2026-09-14')
        self.tx(900,'INFLOW',day='2026-09-20')
        self.assertEqual(Decimal(self.report()['comparison']['income']),100)
        result=self.report(month='2026-09')
        self.assertEqual(result['period']['end'],'2026-09-30')
        self.assertEqual(Decimal(result['metrics']['income']),1000)
        self.assertEqual(len(result['daily']),30)
        self.assertEqual(len(result['history']),12)

    def test_reporting_kind_update_changes_reports_without_changing_balance(self):
        tx=self.tx(2000,'INFLOW',reporting_kind='LOAN')
        self.assertEqual(Decimal(self.report()['metrics']['income']),0)
        self.bank.refresh_from_db();before=self.bank.current_balance
        response=self.client.patch(f"/api/ledger/transactions/{tx['id']}/",{'reporting_kind':'INCOME'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_balance,before)
        self.assertEqual(Decimal(self.report()['metrics']['income']),2000)
        response=self.client.patch(f"/api/ledger/transactions/{tx['id']}/",{'reporting_kind':'EXPENSE'},format='json')
        self.assertEqual(response.status_code,400)

    def test_budget_category_rollups_currency_and_drilldown_agree(self):
        for currency in ('THB','USD'):
            CategoryBudget.objects.create(user=self.user,category=self.category,period_month='2026-10',currency=currency,limit_amount=1000)
        self.tx(300,category=str(self.child.id))
        self.tx(50,account=self.usd,category=str(self.child.id))
        self.tx(700,category=str(self.child.id),reporting_kind='INVESTMENT')
        self.assertEqual(Decimal(self.report()['budgets'][0]['spent']),300)
        self.assertEqual(Decimal(self.report('USD')['budgets'][0]['spent']),50)
        response=self.client.get('/api/ledger/budgets/',{'month':'2026-10'})
        self.assertEqual({b['currency']:Decimal(b['spent_amount']) for b in response.data},{'THB':Decimal(300),'USD':Decimal(50)})
        response=self.client.get('/api/ledger/transactions/',{'currency':'THB','report_kind':'EXPENSE','category':str(self.category.id)})
        self.assertEqual(response.data['count'],1)

    def test_uncategorized_review_excludes_loans_and_investments(self):
        self.tx(100)
        self.tx(200,reporting_kind='INVESTMENT')
        self.tx(500,'INFLOW',reporting_kind='LOAN')
        self.assertEqual(self.report()['uncategorized_count'],1)
        result=self.client.get('/api/ledger/transactions/',{'currency':'THB','uncategorized':'true'})
        self.assertEqual(result.data['count'],1)

    def test_dynamic_forecast_counts_known_partial_values_and_future_cycles(self):
        from apps.finance.strategies.subscription import SubscriptionStrategy
        strategy=SubscriptionStrategy()
        due=date(2026,10,16)
        items=[{'id':'fixed','name':'Room','type':'FIXED','amount':100}, {'id':'water','name':'Water','type':'DYNAMIC'}, {'id':'power','name':'Power','type':'DYNAMIC'}]
        cycle=strategy.update_cycle_draft(strategy.sync_current_cycle(items,None,due,'WEEKLY'),[{'id':'water','amount':25}])
        FinancialObligation.objects.create(user=self.user,title='Room',type='SUBSCRIPTION',amount=100,due_date=due,metadata={'billing_cycle':'WEEKLY','is_itemized':True,'items':items,'current_cycle':cycle})
        result=self.report()['forecast']
        self.assertEqual(Decimal(result['windows']['7']['known_due']),125)
        self.assertEqual(result['windows']['7']['pending_dynamic_count'],1)
        self.assertEqual(Decimal(result['windows']['30']['known_due']),525)
        self.assertEqual(result['windows']['30']['pending_dynamic_count'],9)

    def test_forecast_uses_installment_amount_and_bnpl_statements_once(self):
        FinancialObligation.objects.create(user=self.user,title='Installment',type='INSTALLMENT',amount=350,due_date=date(2026,10,18),metadata={'total_terms':3,'current_term':0})
        parent=FinancialObligation.objects.create(user=self.user,title='BNPL',type='INSTALLMENT',subtype='BNPL_ACCOUNT',amount=50000,due_date=date(2026,10,20),metadata={'due_day':20,'credit_limit':'50000'})
        FinancialObligation.objects.create(user=self.user,parent=parent,title='Child',type='INSTALLMENT',subtype='BNPL_ORDER',amount=200,due_date=date(2026,10,20),metadata={'total_terms':3,'current_term':0,'order_date':'2026-09-01'})
        result=self.report()['forecast']
        self.assertEqual(Decimal(result['windows']['30']['known_due']),550)
        self.assertEqual(len(result['bills']),2)

    def test_trial_risk_and_inflows_do_not_reduce_known_bill_balance(self):
        FinancialObligation.objects.create(user=self.user,title='Trial',type='FREE_TRIAL',amount=100,due_date=date(2026,10,16),metadata={'auto_renew_cost':100})
        FinancialObligation.objects.create(user=self.user,title='Client fee',type='SUBSCRIPTION',direction='INFLOW',amount=5000,due_date=date(2026,10,16))
        FinancialObligation.objects.create(user=self.user,title='Undated',type='SUBSCRIPTION',amount=1000)
        result=self.report()['forecast']['windows']['7']
        self.assertEqual(Decimal(result['known_due']),0)
        self.assertEqual(Decimal(result['conditional_amount']),100)
        self.assertEqual(Decimal(result['remaining']),60000)

    def test_invalid_report_and_budget_parameters_are_validation_errors(self):
        for params in ({'month':'0000-01'},{'month':'bad'},{'currency':'bad-code'},{'history':'100'}):
            self.assertEqual(self.client.get('/api/ledger/transactions/dashboard/',params).status_code,400)
        payload={'category':str(self.category.id),'period_month':'2026-10','currency':'USD','limit_amount':'100'}
        self.assertEqual(self.client.post('/api/ledger/budgets/',payload,format='json').status_code,201)
        self.assertEqual(self.client.post('/api/ledger/budgets/',payload,format='json').status_code,400)

    def test_month_end_comparison_clamps_to_february_and_preserves_full_month(self):
        self.tx(125,'INFLOW',day='2026-02-28')
        self.tx(250,'INFLOW',day='2026-03-31')
        with patch('django.utils.timezone.now',return_value=datetime(2026,3,31,5,tzinfo=dtz.utc)):
            result=self.report(month='2026-03')
        self.assertEqual(result['period']['previous_end'],'2026-02-28')
        self.assertEqual(Decimal(result['comparison']['income']),125)
        self.assertEqual(Decimal(result['metrics']['income']),250)

    def test_termination_forecast_respects_final_bill_and_scheduled_end(self):
        FinancialObligation.objects.create(user=self.user,title='Final bill',type='SUBSCRIPTION',amount=100,due_date=date(2026,10,16),metadata={
            'billing_cycle':'WEEKLY','termination':{'status':'TERMINATED','mode':'IMMEDIATE','effective_end_date':'2026-10-15','has_unpaid_final_bill':True}})
        FinancialObligation.objects.create(user=self.user,title='Scheduled end',type='SUBSCRIPTION',amount=200,due_date=date(2026,10,16),metadata={
            'billing_cycle':'WEEKLY','termination':{'status':'TERMINATED','mode':'SCHEDULED','effective_end_date':'2026-10-25','has_unpaid_final_bill':True}})
        bills=self.report()['forecast']['bills']
        self.assertEqual([b['due_date'] for b in bills if b['title']=='Final bill'],['2026-10-16'])
        self.assertEqual([b['due_date'] for b in bills if b['title']=='Scheduled end'],['2026-10-16','2026-10-23'])
