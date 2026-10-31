import calendar
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List
from django.utils import timezone
from .models import FinancialObligation, ObligationStatus, ObligationType, FlowDirection
from .strategies import ObligationStrategyFactory


def get_exchange_rate_to_thb(currency: str) -> Decimal:
    """Fetch exchange rate to THB based on cache or live market rates."""
    clean_curr = (currency or 'THB').strip().upper()
    if clean_curr == 'THB':
        return Decimal('1.0000')

    RATES = {
        'USD': Decimal('35.0000'),
        'EUR': Decimal('38.0000'),
        'GBP': Decimal('45.0000'),
        'JPY': Decimal('0.2300'),
        'SGD': Decimal('26.5000'),
        'CNY': Decimal('4.8500'),
        'HKD': Decimal('4.5000'),
        'AUD': Decimal('23.0000'),
    }

    if clean_curr == 'USD':
        try:
            from apps.portfolio.services import get_usd_to_thb_rate
            rate = get_usd_to_thb_rate()
            if rate and rate > 0:
                return rate
        except Exception:
            pass
        return RATES['USD']

    return RATES.get(clean_curr, Decimal('1.0000'))


def get_financial_overview(user, target_date: date = None) -> Dict[str, Any]:
    """
    Calculate monthly financial overview for Dashboard:
    - Monthly Burn Rate (Fixed commitments required this month, converted to THB)
    - Expected Inflow (Receivables expected this month, e.g. loans owed by others)
    - Potential Liability (Risk from Free Trials auto-renewing, converted to THB)
    - Upcoming Bills in 7 Days (Obligations due in the next 7 days)
    - Summary breakdown by obligation type
    """
    if target_date is None:
        target_date = timezone.localdate()

    target_year = target_date.year
    target_month = target_date.month

    # Scoped strictly to current user's ACTIVE obligations (Strict Multi-Tenancy)
    active_obligations = FinancialObligation.objects.filter(
        user=user,
        status=ObligationStatus.ACTIVE
    ).select_related('project')

    confirmed_burn_rate = Decimal('0.00')
    potential_risk_amount = Decimal('0.00')
    expected_inflow_amount = Decimal('0.00')
    expected_inflow_items: List[Dict[str, Any]] = []

    active_debtor_records_count = 0
    total_debtors_outstanding_amount = Decimal('0.00')

    categorized_items: Dict[str, List[Dict[str, Any]]] = {
        'INSTALLMENT': [],
        'SUBSCRIPTION': [],
        'FREE_TRIAL': [],
        'DEBT': []
    }

    today = target_date
    next_7_days = today + timedelta(days=7)
    upcoming_7_days: List[Dict[str, Any]] = []

    active_trials_count = 0
    critical_trials_count = 0
    has_pending_dynamic = False
    total_pending_dynamic_count = 0

    for ob in active_obligations:
        rate = get_exchange_rate_to_thb(ob.currency)
        amount_thb = (ob.amount * rate).quantize(Decimal('0.01'))

        strategy = ObligationStrategyFactory.get_strategy(ob.type)
        summary = strategy.get_summary(ob)
        item_data = {
            'id': str(ob.id),
            'title': ob.title,
            'type': ob.type,
            'direction': ob.direction,
            'amount': ob.amount,
            'amount_thb': amount_thb,
            'currency': ob.currency,
            'due_date': ob.due_date.isoformat() if ob.due_date else None,
            'billing_day': ob.billing_day,
            'summary': summary
        }

        # Group by type
        categorized_items[ob.type].append(item_data)

        # Track active debtor records (strictly DEBT + INFLOW with remaining balance > 0)
        if ob.type == ObligationType.DEBT and ob.direction == FlowDirection.INFLOW:
            remaining = Decimal(str(summary.get('remaining_balance', ob.amount)))
            if remaining > Decimal('0.00'):
                active_debtor_records_count += 1
                total_debtors_outstanding_amount += (remaining * rate).quantize(Decimal('0.01'))

        # 1. Monthly Burn Rate (Outflows) and Expected Inflows
        if ob.direction == FlowDirection.INFLOW:
            # Expected inflow (e.g. debt repaid by counterparty / recurring income)
            if ob.type == ObligationType.DEBT:
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    remaining = Decimal(str(summary.get('remaining_balance', ob.amount)))
                    if remaining > Decimal('0.00'):
                        item_thb = (remaining * rate).quantize(Decimal('0.01'))
                        expected_inflow_amount += item_thb
                        counterparty = summary.get('counterparty') or (ob.metadata or {}).get('counterparty') or ob.title
                        expected_inflow_items.append({
                            'id': str(ob.id),
                            'title': ob.title,
                            'category': 'DEBT',
                            'category_label': 'Debt Repayment',
                            'type': ob.type,
                            'amount': remaining,
                            'amount_thb': item_thb,
                            'currency': ob.currency,
                            'due_date': ob.due_date.isoformat() if ob.due_date else None,
                            'counterparty': counterparty,
                            'project_id': None,
                        })
            elif ob.type == ObligationType.SUBSCRIPTION:
                billing_cycle = (ob.metadata or {}).get('billing_cycle', 'MONTHLY').upper()
                include_inflow = False
                inflow_amount = amount_thb
                inflow_raw_amount = ob.amount

                if billing_cycle == 'YEARLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        include_inflow = True
                elif billing_cycle == 'QUARTERLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        include_inflow = True
                elif billing_cycle == 'WEEKLY':
                    if ob.due_date:
                        last_day_num = calendar.monthrange(target_year, target_month)[1]
                        last_day = date(target_year, target_month, last_day_num)
                        first_day = date(target_year, target_month, 1)
                        if ob.due_date <= last_day:
                            curr = ob.due_date
                            while curr < first_day:
                                curr += timedelta(days=7)
                            weekly_count = 0
                            while curr.year == target_year and curr.month == target_month:
                                weekly_count += 1
                                curr += timedelta(days=7)
                            if weekly_count > 0:
                                include_inflow = True
                                inflow_amount = (amount_thb * Decimal(str(weekly_count))).quantize(Decimal('0.01'))
                                inflow_raw_amount = (ob.amount * Decimal(str(weekly_count))).quantize(Decimal('0.01'))
                else:
                    # Monthly: only included if scheduled in target_year, target_month!
                    # Respects already paid obligations whose due_date shifted to next month,
                    # as well as future contracts starting next month.
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        include_inflow = True
                    elif ob.due_date is None and ob.billing_day:
                        include_inflow = True

                if include_inflow:
                    expected_inflow_amount += inflow_amount
                    meta = ob.metadata or {}
                    # Check explicit MA contract source:
                    # Must have source_type == 'MA_CONTRACT' or linked project is explicitly of type MA_CONTRACT
                    is_ma = bool(
                        meta.get('source_type') == 'MA_CONTRACT' or
                        (getattr(ob, 'project', None) and getattr(ob.project, 'project_type', '') == 'MA_CONTRACT')
                    )
                    proj_id = str(ob.project_id) if ob.project_id else meta.get('project_id')
                    client_name = meta.get('client_name') or meta.get('counterparty') or ''
                    expected_inflow_items.append({
                        'id': str(ob.id),
                        'title': ob.title,
                        'category': 'MA' if is_ma else 'RECURRING',
                        'category_label': 'MA Revenue' if is_ma else 'Recurring Inflow',
                        'type': ob.type,
                        'amount': inflow_raw_amount,
                        'amount_thb': inflow_amount,
                        'currency': ob.currency,
                        'due_date': ob.due_date.isoformat() if ob.due_date else None,
                        'counterparty': client_name,
                        'project_id': proj_id if is_ma else None,
                    })
            elif ob.type == ObligationType.INSTALLMENT:
                # Installment inflow (e.g. counterparty paying installment to user)
                # Must be scheduled in target_year, target_month and not finished!
                is_due_this_month = False
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    is_due_this_month = True
                elif ob.due_date is None and ob.billing_day:
                    is_due_this_month = True

                if is_due_this_month and not summary.get('is_finished', False):
                    expected_inflow_amount += amount_thb
                    meta = ob.metadata or {}
                    expected_inflow_items.append({
                        'id': str(ob.id),
                        'title': ob.title,
                        'category': 'RECURRING',
                        'category_label': 'Recurring Inflow',
                        'type': ob.type,
                        'amount': ob.amount,
                        'amount_thb': amount_thb,
                        'currency': ob.currency,
                        'due_date': ob.due_date.isoformat() if ob.due_date else None,
                        'counterparty': meta.get('counterparty') or '',
                        'project_id': None,
                    })
        else:
            # Outflow commitments
            if ob.type == ObligationType.INSTALLMENT:
                if ob.parent_id:
                    # BNPL sub-order: excluded to prevent double counting (included in parent account bill)
                    pass
                elif getattr(ob, 'subtype', '') == 'BNPL_ACCOUNT':
                    # BNPL parent account: include current monthly bill
                    current_bill = summary.get('current_bill_amount', Decimal('0.00'))
                    confirmed_burn_rate += (Decimal(str(current_bill)) * rate).quantize(Decimal('0.01'))
                else:
                    # Standard installment or hire purchase
                    if not summary.get('is_finished', False):
                        confirmed_burn_rate += amount_thb

            elif ob.type == ObligationType.SUBSCRIPTION:
                is_itemized = summary.get('is_itemized', False)
                pending_count = summary.get('pending_dynamic_count', 0)
                if is_itemized and pending_count > 0:
                    has_pending_dynamic = True
                    total_pending_dynamic_count += pending_count

                sub_amount = summary.get('amount_per_period')
                if sub_amount is not None:
                    sub_amt = Decimal(str(sub_amount))
                    sub_thb = (sub_amt * rate).quantize(Decimal('0.01'))
                else:
                    sub_amt = Decimal('0.00')
                    sub_thb = Decimal('0.00')

                billing_cycle = (ob.metadata or {}).get('billing_cycle', 'MONTHLY').upper()
                if billing_cycle == 'YEARLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        confirmed_burn_rate += sub_thb
                elif billing_cycle == 'QUARTERLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        confirmed_burn_rate += sub_thb
                elif billing_cycle == 'WEEKLY':
                    # Approximately 4.3333 weeks in a month
                    weekly_norm = (sub_thb * Decimal('4.3333')).quantize(Decimal('0.01'))
                    confirmed_burn_rate += weekly_norm
                else:
                    # Monthly: charged every month
                    confirmed_burn_rate += sub_thb

            elif ob.type == ObligationType.DEBT:
                # Debt repayment due this month
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    remaining = summary.get('remaining_balance', ob.amount)
                    confirmed_burn_rate += (Decimal(str(remaining)) * rate).quantize(Decimal('0.01'))

            elif ob.type == ObligationType.FREE_TRIAL:
                active_trials_count += 1
                if summary.get('urgency') in ['CRITICAL', 'WARNING']:
                    critical_trials_count += 1

                # Free trial potential risk (if expiring this month)
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    auto_renew = summary.get('auto_renew_cost', ob.amount)
                    potential_risk_amount += (Decimal(str(auto_renew)) * rate).quantize(Decimal('0.01'))

        # 2. Upcoming bills in 7 days (consolidate BNPL sub-orders into parent account)
        if ob.parent_id:
            continue

        if ob.due_date and today <= ob.due_date <= next_7_days:
            bill_amount = ob.amount
            bill_amount_thb = amount_thb
            if ob.subtype == 'BNPL_ACCOUNT':
                bill_amount = Decimal(str(summary.get('current_bill_amount', 0)))
                bill_amount_thb = bill_amount
            elif ob.type == ObligationType.SUBSCRIPTION and summary.get('is_itemized'):
                if summary.get('is_bill_complete') and summary.get('total_bill_amount') is not None:
                    bill_amount = Decimal(str(summary['total_bill_amount']))
                else:
                    bill_amount = Decimal(str(summary.get('fixed_total', '0.00')))
                bill_amount_thb = (bill_amount * rate).quantize(Decimal('0.01'))

            if bill_amount > Decimal('0.00') or ob.type == ObligationType.FREE_TRIAL or (ob.type == ObligationType.SUBSCRIPTION and summary.get('is_itemized')):
                upcoming_7_days.append({
                    'id': str(ob.id),
                    'title': ob.title,
                    'type': ob.type,
                    'direction': ob.direction,
                    'amount': bill_amount,
                    'amount_thb': bill_amount_thb,
                    'currency': ob.currency,
                    'due_date': ob.due_date.isoformat(),
                    'days_left': (ob.due_date - today).days,
                    'is_trial': ob.type == ObligationType.FREE_TRIAL,
                    'summary': summary
                })

    # Sort upcoming 7 days by urgency
    upcoming_7_days.sort(key=lambda x: x['days_left'])

    debt_total_count = FinancialObligation.objects.filter(
        user=user,
        type=ObligationType.DEBT
    ).count()

    debt_breakdown_amount = sum((item['amount_thb'] for item in expected_inflow_items if item['category'] == 'DEBT'), Decimal('0.00'))
    ma_breakdown_amount = sum((item['amount_thb'] for item in expected_inflow_items if item['category'] == 'MA'), Decimal('0.00'))
    recurring_breakdown_amount = sum((item['amount_thb'] for item in expected_inflow_items if item['category'] == 'RECURRING'), Decimal('0.00'))

    return {
        'target_month': f"{target_year}-{target_month:02d}",
        'confirmed_burn_rate': confirmed_burn_rate,
        'has_pending_dynamic': has_pending_dynamic,
        'pending_dynamic_count': total_pending_dynamic_count,
        'potential_risk_amount': potential_risk_amount,
        'expected_inflow_amount': expected_inflow_amount,
        'expected_inflow_breakdown': {
            'debt_amount': debt_breakdown_amount,
            'ma_amount': ma_breakdown_amount,
            'recurring_amount': recurring_breakdown_amount,
            'items': expected_inflow_items
        },
        'active_debtor_records_count': active_debtor_records_count,
        'total_debtors_outstanding_amount': total_debtors_outstanding_amount,
        'debt_total_count': debt_total_count,
        'active_trials_count': active_trials_count,
        'critical_trials_count': critical_trials_count,
        'upcoming_7_days_count': len(upcoming_7_days),
        'upcoming_7_days': upcoming_7_days,
        'items_by_type': categorized_items
    }
