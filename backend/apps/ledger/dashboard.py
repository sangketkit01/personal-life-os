"""Personal income/expense reporting and cash movements share one classification policy."""
import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Exists, OuterRef, Sum
from django.db.models import Q
from django.utils import timezone
from .models import Account, AccountType, CategoryBudget, ReportingKind, Transaction, TransactionSplit

ZERO = Decimal('0')
LIQUID_TYPES = {AccountType.BANK, AccountType.CASH, AccountType.E_WALLET}


def reporting_queryset(user, currency=None):
    qs = Transaction.objects.filter(user=user, account__user=user).select_related(
        'account', 'category__parent', 'obligation', 'transfer_destination')
    if currency:
        qs = qs.filter(account__currency=currency)
    return qs.annotate(is_reimbursement=Exists(TransactionSplit.objects.filter(
        transaction__user=user, settlement_transaction_id=OuterRef('pk'))))


def reporting_kind(tx):
    # Structural links take precedence over optional manual classifications.
    if tx.transfer_peer_id or tx.transfer_destination_id or tx.transaction_type == 'TRANSFER':
        return 'TRANSFER'
    if getattr(tx, 'is_reimbursement', False):
        return 'REIMBURSEMENT'
    if tx.reporting_kind != 'AUTO':
        return tx.reporting_kind
    if tx.obligation_id and (tx.obligation.type == 'DEBT' or tx.obligation.subtype in ('FORMAL_LOAN','INFORMAL_BORROW')):
        return 'LOAN'
    if tx.portfolio_id:
        return 'INVESTMENT'
    return 'INCOME' if tx.transaction_type == 'INFLOW' else 'EXPENSE'


def report_amount(tx, kind=None):
    return tx.net_amount if (kind or reporting_kind(tx)) == 'EXPENSE' else tx.gross_amount


def cash_movement(tx):
    if tx.account.account_type not in LIQUID_TYPES:
        return ZERO
    if tx.transfer_destination_id and tx.transfer_destination.account_type in LIQUID_TYPES:
        return ZERO
    return tx.gross_amount if tx.transaction_type == 'INFLOW' else -tx.gross_amount if tx.transaction_type == 'OUTFLOW' else ZERO


def month_start(day, offset=0):
    index = day.year * 12 + day.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def metrics(rows):
    income = expense = cash_in = cash_out = ZERO
    for tx in rows:
        kind = reporting_kind(tx)
        if kind == 'INCOME':
            income += report_amount(tx, kind)
        elif kind == 'EXPENSE':
            expense += report_amount(tx, kind)
        cash = cash_movement(tx)
        cash_in += max(cash, ZERO)
        cash_out += max(-cash, ZERO)
    return {'income': str(income), 'expense': str(expense), 'surplus': str(income-expense),
            'cash_in': str(cash_in), 'cash_out': str(cash_out), 'cash_flow': str(cash_in-cash_out)}


def transaction_data(tx):
    kind = reporting_kind(tx)
    return {'id':str(tx.id), 'title':tx.title, 'date':tx.transaction_date.isoformat(),
        'account':str(tx.account_id), 'account_name':tx.account.name, 'account_type':tx.account.account_type,
        'currency':tx.account.currency, 'category':str(tx.category_id) if tx.category_id else None,
        'category_name':tx.category.name if tx.category_id else 'ยังไม่จัดหมวด', 'kind':kind,
        'transaction_type':tx.transaction_type, 'reporting_kind':tx.reporting_kind,
        'amount':str(report_amount(tx, kind)), 'gross_amount':str(tx.gross_amount), 'net_amount':str(tx.net_amount)}


def category_breakdown(rows, kind):
    groups = {}
    for tx in rows:
        if reporting_kind(tx) != kind:
            continue
        category = (tx.category.parent or tx.category) if tx.category_id else None
        key = str(category.id) if category else None
        group = groups.setdefault(key, {'id':key, 'name':category.name if category else 'ยังไม่จัดหมวด',
            'amount':ZERO, 'count':0, 'children':{}})
        group['amount'] += report_amount(tx, kind)
        group['count'] += 1
        if category and tx.category_id != category.id:
            child = group['children'].setdefault(str(tx.category_id), {'id':str(tx.category_id), 'name':tx.category.name, 'amount':ZERO, 'count':0})
            child['amount'] += report_amount(tx, kind)
            child['count'] += 1
    total = sum((g['amount'] for g in groups.values()), ZERO)
    result = []
    for group in sorted(groups.values(), key=lambda g:g['amount'], reverse=True):
        group['share'] = float(group['amount']/total*100) if total else 0
        group['amount'] = str(group['amount'])
        group['children'] = [{**c, 'amount':str(c['amount'])} for c in sorted(group['children'].values(), key=lambda c:c['amount'], reverse=True)]
        result.append(group)
    return result


def budget_data(user, period, currency, rows=None):
    start = date.fromisoformat(period+'-01')
    rows = rows if rows is not None else list(reporting_queryset(user, currency).filter(
        transaction_date__range=(start, min(month_end(start), timezone.localdate()))))
    spent = defaultdict(lambda: ZERO)
    for tx in rows:
        if tx.category_id and reporting_kind(tx) == 'EXPENSE':
            spent[tx.category_id] += tx.net_amount
            if tx.category.parent_id:
                spent[tx.category.parent_id] += tx.net_amount
    return [{'id':str(b.id), 'category':str(b.category_id), 'name':b.category.name, 'currency':b.currency,
        'limit':str(b.limit_amount), 'spent':str(spent[b.category_id]), 'remaining':str(b.limit_amount-spent[b.category_id]),
        'usage_pct':float(spent[b.category_id]/b.limit_amount*100) if b.limit_amount else 0}
        for b in CategoryBudget.objects.filter(user=user, period_month=period, currency=currency).select_related('category')]


def forecast(user, currency, liquid, today):
    from apps.finance.models import FinancialObligation
    from apps.finance.strategies import ObligationStrategyFactory
    horizon = today+timedelta(days=30)
    bills = []
    for ob in FinancialObligation.objects.filter(user=user, currency=currency, parent__isnull=True,
            status='ACTIVE', direction='OUTFLOW').filter(Q(due_date__lte=horizon) | Q(subtype='BNPL_ACCOUNT')).order_by('due_date'):
        summary = ObligationStrategyFactory.get_strategy(ob.type).get_summary(ob)
        if ob.subtype == 'BNPL_ACCOUNT':
            cycles = [(date.fromisoformat(s['due_date']), Decimal(str(s['total_due'])), 0, False)
                      for s in summary.get('statement_timeline', []) if Decimal(str(s['total_due'])) > 0]
        else:
            pending = int(summary.get('pending_dynamic_count', 0))
            known = Decimal(str(summary.get('fixed_total', 0))) if pending else Decimal(str(summary.get('total_bill_amount') if summary.get('is_itemized') else summary.get('remaining_balance', ob.amount) if ob.type == 'DEBT' else ob.amount))
            if pending:
                cycle = summary.get('current_cycle') or {}
                known += sum((Decimal(str(i['amount'])) for i in cycle.get('items', []) if i.get('type') == 'DYNAMIC' and i.get('amount') is not None), ZERO)
            if ob.type == 'FREE_TRIAL':
                known = Decimal(str(summary.get('auto_renew_cost', ob.amount)))
            cycles = [(ob.due_date, known, pending, False)]
            due = ob.due_date
            remaining = max(0, int(summary.get('total_terms', 1))-int(summary.get('current_term', 0)))
            for index in range(1, 32):
                termination = summary.get('termination') or {}
                if due < today or (summary.get('is_terminated') and termination.get('mode') != 'SCHEDULED') or ob.type not in ('SUBSCRIPTION', 'INSTALLMENT'):
                    break
                if ob.type == 'INSTALLMENT' and index >= remaining:
                    break
                cycle_name = (ob.metadata or {}).get('billing_cycle', 'MONTHLY') if ob.type == 'SUBSCRIPTION' else 'MONTHLY'
                due = due+timedelta(days=7) if cycle_name == 'WEEKLY' else ObligationStrategyFactory.get_strategy(ob.type).calculate_next_due_date(
                    due, billing_day=ob.billing_day or ob.due_date.day, months_to_add={'YEARLY':12,'QUARTERLY':3}.get(cycle_name,1))
                if due > horizon:
                    break
                if termination.get('effective_end_date') and due > date.fromisoformat(termination['effective_end_date']):
                    break
                dynamic = [i for i in summary.get('items', []) if i.get('type') == 'DYNAMIC']
                next_amount = Decimal(str(summary.get('fixed_total', ob.amount))) if summary.get('is_itemized') else ob.amount
                cycles.append((due, next_amount, len(dynamic), True))
        section = 'bnpl' if ob.subtype == 'BNPL_ACCOUNT' else {'SUBSCRIPTION':'subscriptions','FREE_TRIAL':'subscriptions','DEBT':'debts'}.get(ob.type,'installments')
        for due, amount, pending, projected in cycles:
            if due <= horizon and (amount > 0 or pending):
                bills.append({'id':str(ob.id), 'title':ob.title, 'due_date':due.isoformat(), 'known_amount':str(amount),
                    'pending_dynamic_count':pending, 'projected':projected, 'conditional':ob.type == 'FREE_TRIAL',
                    'path':f'/finance/{section}/{ob.id}'})
    bills.sort(key=lambda b:(b['due_date'],b['title']))
    windows = {}
    for days in (7,30):
        subset = [b for b in bills if date.fromisoformat(b['due_date']) <= today+timedelta(days=days)]
        total = sum((Decimal(b['known_amount']) for b in subset if not b['conditional']), ZERO)
        windows[str(days)] = {'known_due':str(total), 'remaining':str(liquid-total),
            'pending_dynamic_count':sum(b['pending_dynamic_count'] for b in subset),
            'conditional_amount':str(sum((Decimal(b['known_amount']) for b in subset if b['conditional']),ZERO)), 'count':len(subset)}
    return {'as_of':today.isoformat(), 'bills':bills, 'windows':windows}


def dashboard(user, period, currency, months=12):
    today = timezone.localdate()
    start = date.fromisoformat(period+'-01')
    end = min(month_end(start), today)
    previous = month_start(start,-1)
    previous_end = previous.replace(day=min(today.day,calendar.monthrange(previous.year, previous.month)[1])) if start == month_start(today) else month_end(previous)
    history_start = month_start(start, -(months-1))
    rows = list(reporting_queryset(user,currency).filter(transaction_date__range=(min(history_start,previous),end)).order_by('transaction_date','created_at'))
    current = [tx for tx in rows if start <= tx.transaction_date <= end]
    prior = [tx for tx in rows if previous <= tx.transaction_date <= previous_end]
    daily = []
    for i in range(max(0,(end-start).days+1)):
        day = start+timedelta(days=i)
        daily.append({'date':day.isoformat(), **metrics([tx for tx in current if tx.transaction_date == day])})
    history = []
    for i in range(months):
        month = month_start(start,i-months+1)
        history.append({'month':month.strftime('%Y-%m'), **metrics([tx for tx in rows if month <= tx.transaction_date <= min(month_end(month),end)])})
    accounts = list(Account.objects.filter(user=user, is_archived=False, currency=currency))
    future = defaultdict(lambda: ZERO)
    for row in Transaction.objects.filter(user=user, account__currency=currency, transaction_date__gt=today).values('account_id','transaction_type').annotate(total=Sum('gross_amount')):
        future[row['account_id']] += row['total'] if row['transaction_type'] == 'INFLOW' else -row['total'] if row['transaction_type'] == 'OUTFLOW' else ZERO
    for account in accounts:
        account.current_balance -= future[account.id]
    liquid = sum((a.current_balance for a in accounts if a.account_type in LIQUID_TYPES),ZERO)
    credit = sum((-min(a.current_balance,ZERO) for a in accounts if a.account_type == 'CREDIT_CARD'),ZERO)
    pending = TransactionSplit.objects.filter(transaction__user=user, transaction__account__currency=currency, is_settled=False)
    split_total = ZERO
    for s in pending.select_related('debtor_obligation'):
        remaining = (s.debtor_obligation.metadata or {}).get('remaining_balance') if s.debtor_obligation_id else None
        split_total += max(ZERO, Decimal(str(remaining)) if remaining is not None else s.amount)
    return {'period':{'month':period, 'start':start.isoformat(), 'end':end.isoformat(), 'is_partial':end < month_end(start),
                'previous_start':previous.isoformat(), 'previous_end':previous_end.isoformat()},
        'currency':currency, 'currencies':sorted(set(Account.objects.filter(user=user).values_list('currency',flat=True)) | {currency}),
        'as_of':timezone.now().isoformat(), 'metrics':metrics(current), 'comparison':metrics(prior), 'liquid_balance':str(liquid),
        'credit_debt':str(credit), 'pending_split_amount':str(split_total),
        'accounts':[{'id':str(a.id),'name':a.name,'type':a.account_type,'balance':str(a.current_balance)} for a in accounts],
        'daily':daily, 'history':history, 'income_sources':category_breakdown(current,'INCOME'), 'expense_categories':category_breakdown(current,'EXPENSE'),
        'budgets':budget_data(user,period,currency,current), 'forecast':forecast(user,currency,liquid,today),
        'recent':[transaction_data(tx) for tx in current[::-1][:8]],
        'largest_expenses':[transaction_data(tx) for tx in sorted((tx for tx in current if reporting_kind(tx)=='EXPENSE'),key=lambda tx:tx.net_amount,reverse=True)[:5]],
        'uncategorized_count':sum(not tx.category_id and reporting_kind(tx) in ('INCOME','EXPENSE') for tx in current)}
