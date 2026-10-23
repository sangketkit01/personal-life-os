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
    )

    confirmed_burn_rate = Decimal('0.00')
    potential_risk_amount = Decimal('0.00')
    expected_inflow_amount = Decimal('0.00')

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

        # 1. Monthly Burn Rate (Outflows) and Expected Inflows
        if ob.direction == FlowDirection.INFLOW:
            # Expected inflow (e.g. debt repaid by counterparty / recurring income)
            if ob.type == ObligationType.DEBT:
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    remaining = summary.get('remaining_balance', ob.amount)
                    expected_inflow_amount += (Decimal(str(remaining)) * rate).quantize(Decimal('0.01'))
            elif ob.type in [ObligationType.SUBSCRIPTION, ObligationType.INSTALLMENT]:
                expected_inflow_amount += amount_thb
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
                billing_cycle = (ob.metadata or {}).get('billing_cycle', 'MONTHLY').upper()
                if billing_cycle == 'YEARLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        confirmed_burn_rate += amount_thb
                elif billing_cycle == 'QUARTERLY':
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        confirmed_burn_rate += amount_thb
                elif billing_cycle == 'WEEKLY':
                    # Approximately 4.3333 weeks in a month
                    weekly_norm = (amount_thb * Decimal('4.3333')).quantize(Decimal('0.01'))
                    confirmed_burn_rate += weekly_norm
                else:
                    # Monthly: charged every month
                    confirmed_burn_rate += amount_thb

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

            if bill_amount > Decimal('0.00') or ob.type == ObligationType.FREE_TRIAL:
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

    return {
        'target_month': f"{target_year}-{target_month:02d}",
        'confirmed_burn_rate': confirmed_burn_rate,
        'potential_risk_amount': potential_risk_amount,
        'expected_inflow_amount': expected_inflow_amount,
        'active_trials_count': active_trials_count,
        'critical_trials_count': critical_trials_count,
        'upcoming_7_days_count': len(upcoming_7_days),
        'upcoming_7_days': upcoming_7_days,
        'items_by_type': categorized_items
    }
