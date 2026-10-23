import calendar
import datetime
from decimal import Decimal
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class InstallmentStrategy(BaseObligationStrategy):
    """
    Strategy for fixed installments, vehicle hire purchase, and BNPL revolving lines:
    - Tracks term progression e.g. 14/36.
    - Computes remaining balance and progress percentage.
    - Evaluates BNPL sub-orders strictly by purchase calendar month (disregarding day).
    - Schedules installments strictly starting the following month onwards (M+1, M+2, ...).
    - Supports hybrid down payment and financing fee / interest.
    - Automatically aggregates dynamic Monthly Statement Timeline Matrix.
    - Automatically transitions status to COMPLETED upon final term payment.
    """

    @staticmethod
    def calculate_term_due_date(base_date: datetime.date, term_num: int, due_day: int = 10) -> datetime.date:
        """
        Calculates term due date starting from base_date's month + term_num.
        Disregards day of month in base_date and strictly targets (base_date.month + term_num).
        Handles December-to-January rollovers and leap years cleanly.
        """
        total_months = (base_date.year * 12 + (base_date.month - 1)) + term_num
        target_year = total_months // 12
        target_month = (total_months % 12) + 1
        max_days = calendar.monthrange(target_year, target_month)[1]
        day = min(due_day, max_days)
        return datetime.date(target_year, target_month, day)

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        subtype = metadata.get('subtype', 'STANDARD')

        # 1. BNPL revolving credit account (SPayLater, LazPayLater, TikTok)
        if subtype == 'BNPL_ACCOUNT':
            return {
                'subtype': 'BNPL_ACCOUNT',
                'provider': str(metadata.get('provider', '')).strip(),
                'credit_limit': str(Decimal(str(metadata.get('credit_limit', '0.00')))),
                'cutoff_day': int(metadata.get('cutoff_day', 25)),
                'due_day': int(metadata.get('due_day', 10)),
                'account_number': str(metadata.get('account_number', '')).strip(),
                'notes': str(metadata.get('notes', '')).strip(),
            }

        # 2. Standard installment, BNPL sub-order, and Vehicle Hire Purchase
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        if total_terms <= 0:
            raise ValueError("Total terms must be greater than 0.")
        if current_term < 0:
            raise ValueError("Current term cannot be negative.")
        if current_term > total_terms:
            raise ValueError("Current term cannot exceed total terms.")

        total_price = Decimal(str(metadata.get('total_price', metadata.get('total_principal', '0.00'))))
        down_payment = Decimal(str(metadata.get('down_payment', '0.00')))
        financed_amount = Decimal(str(metadata.get('financed_amount', total_price - down_payment if total_price >= down_payment else '0.00')))
        interest_rate_pct = Decimal(str(metadata.get('interest_rate_pct', '0.00')))
        monthly_interest = Decimal(str(metadata.get('monthly_interest', '0.00')))

        validated = {
            'subtype': subtype,
            'total_terms': total_terms,
            'current_term': current_term,
            'lender': str(metadata.get('lender', '')).strip(),
            'total_principal': str(Decimal(str(metadata.get('total_principal', financed_amount)))),
            'auto_pay': bool(metadata.get('auto_pay', False)),
            'contract_number': str(metadata.get('contract_number', '')).strip(),
            'notes': str(metadata.get('notes', '')).strip(),
            # BNPL Sub-Order specifics
            'store': str(metadata.get('store', '')).strip(),
            'order_number': str(metadata.get('order_number', '')).strip(),
            'order_date': str(metadata.get('order_date', '')).strip() if metadata.get('order_date') else None,
            'item_name': str(metadata.get('item_name', '')).strip(),
            'total_price': str(total_price),
            'down_payment': str(down_payment),
            'financed_amount': str(financed_amount),
            'interest_rate_pct': str(interest_rate_pct),
            'monthly_interest': str(monthly_interest),
        }

        # Additional metadata for Vehicle Hire Purchase & Loan contracts
        if subtype == 'HIRE_PURCHASE':
            validated.update({
                'vehicle_model': str(metadata.get('vehicle_model', '')).strip(),
                'down_payment': str(down_payment),
                'financed_amount': str(financed_amount),
                'flat_rate_pa': str(Decimal(str(metadata.get('flat_rate_pa', '0.00')))),
                'vat_pct': str(Decimal(str(metadata.get('vat_pct', '7.00')))),
                'license_plate': str(metadata.get('license_plate', '')).strip(),
                'insurance_provider': str(metadata.get('insurance_provider', '')).strip(),
                'policy_number': str(metadata.get('policy_number', '')).strip(),
                'tax_expiry_date': str(metadata.get('tax_expiry_date', '')).strip() if metadata.get('tax_expiry_date') else None,
            })

        return validated

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        subtype = getattr(obligation, 'subtype', None) or metadata.get('subtype', 'STANDARD')

        # 1. Summary for BNPL Parent Account (Revolving Credit Facility)
        if subtype == 'BNPL_ACCOUNT':
            sub_orders = obligation.sub_orders.filter(status='ACTIVE')
            credit_limit = Decimal(str(metadata.get('credit_limit', '0.00')))
            due_day = int(metadata.get('due_day', obligation.billing_day or 10))

            # Group active sub-orders into calendar statement timeline
            timeline_buckets = {}
            total_remaining_debt = Decimal('0.00')
            orders_summary = []

            for order in sub_orders:
                order_meta = order.metadata or {}
                o_total_terms = int(order_meta.get('total_terms', 1))
                o_current_term = int(order_meta.get('current_term', 0))
                o_remaining_terms = max(0, o_total_terms - o_current_term)
                o_remaining_balance = Decimal(str(o_remaining_terms)) * order.amount

                total_remaining_debt += o_remaining_balance

                # Resolve base purchase date
                o_date_str = order_meta.get('order_date')
                if o_date_str:
                    try:
                        base_date = datetime.date.fromisoformat(o_date_str)
                    except ValueError:
                        base_date = order.created_at.date() if order.created_at else timezone.localdate()
                else:
                    raw_date = order.created_at.date() if order.created_at else timezone.localdate()
                    if o_current_term > 0:
                        from dateutil.relativedelta import relativedelta
                        base_date = raw_date - relativedelta(months=o_current_term)
                    else:
                        base_date = raw_date

                orders_summary.append({
                    'id': str(order.id),
                    'title': order.title,
                    'amount': order.amount,
                    'current_term': o_current_term,
                    'total_terms': o_total_terms,
                    'remaining_balance': o_remaining_balance,
                    'order_date': base_date.isoformat(),
                    'store': order_meta.get('store', ''),
                    'order_number': order_meta.get('order_number', ''),
                    'total_price': Decimal(str(order_meta.get('total_price', order.amount * o_total_terms))),
                    'down_payment': Decimal(str(order_meta.get('down_payment', '0.00'))),
                    'financed_amount': Decimal(str(order_meta.get('financed_amount', order.amount * o_total_terms))),
                    'interest_rate_pct': Decimal(str(order_meta.get('interest_rate_pct', '0.00'))),
                })

                # Distribute remaining terms into statement calendar months (M+1, M+2, ...)
                for term_idx in range(o_current_term + 1, o_total_terms + 1):
                    total_months = (base_date.year * 12 + (base_date.month - 1)) + term_idx
                    t_year = total_months // 12
                    t_month = (total_months % 12) + 1
                    m_key = f"{t_year:04d}-{t_month:02d}"

                    if m_key not in timeline_buckets:
                        max_days = calendar.monthrange(t_year, t_month)[1]
                        m_due_day = min(due_day, max_days)
                        due_date_str = f"{t_year:04d}-{t_month:02d}-{m_due_day:02d}"
                        month_label = datetime.date(t_year, t_month, 1).strftime('%B %Y')
                        timeline_buckets[m_key] = {
                            'statement_month': m_key,
                            'month_label': month_label,
                            'due_date': due_date_str,
                            'total_due': Decimal('0.00'),
                            'items': []
                        }

                    timeline_buckets[m_key]['total_due'] += order.amount
                    timeline_buckets[m_key]['items'].append({
                        'order_id': str(order.id),
                        'title': order.title,
                        'store': order_meta.get('store', ''),
                        'term_number': term_idx,
                        'total_terms': o_total_terms,
                        'amount': order.amount,
                        'remaining_order_debt': Decimal(str(max(0, o_total_terms - term_idx))) * order.amount
                    })

            # Sort statement timeline chronologically by month key
            sorted_timeline = []
            for m_key in sorted(timeline_buckets.keys()):
                bucket = timeline_buckets[m_key]
                sorted_timeline.append({
                    'statement_month': bucket['statement_month'],
                    'month_label': bucket['month_label'],
                    'due_date': bucket['due_date'],
                    'total_due': bucket['total_due'],
                    'orders_count': len(bucket['items']),
                    'items': bucket['items'],
                    'is_current': len(sorted_timeline) == 0
                })

            current_statement = sorted_timeline[0] if sorted_timeline else None
            current_bill_amount = current_statement['total_due'] if current_statement else Decimal('0.00')
            next_due_date = current_statement['due_date'] if current_statement else (
                obligation.due_date.isoformat() if obligation.due_date else None
            )

            available_credit = max(Decimal('0.00'), credit_limit - total_remaining_debt)
            utilization_pct = round((total_remaining_debt / credit_limit) * 100, 1) if credit_limit > 0 else 0.0

            return {
                'subtype': 'BNPL_ACCOUNT',
                'provider': metadata.get('provider', obligation.title),
                'credit_limit': credit_limit,
                'available_credit': available_credit,
                'utilization_pct': utilization_pct,
                'current_bill_amount': current_bill_amount,
                'total_remaining_debt': total_remaining_debt,
                'active_orders_count': sub_orders.count(),
                'cutoff_day': metadata.get('cutoff_day', 25),
                'due_day': due_day,
                'sub_orders': orders_summary,
                'statement_timeline': sorted_timeline,
                'current_statement': current_statement,
                'next_due_date': next_due_date
            }

        # 2. Summary for Standard Installment & Vehicle Hire Purchase
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        remaining_terms = max(0, total_terms - current_term)
        remaining_balance = Decimal(str(remaining_terms)) * obligation.amount

        progress_pct = round((current_term / total_terms) * 100, 1) if total_terms > 0 else 0.0

        summary = {
            'subtype': subtype,
            'total_terms': total_terms,
            'current_term': current_term,
            'remaining_terms': remaining_terms,
            'remaining_balance': remaining_balance,
            'progress_pct': progress_pct,
            'progress_percentage': progress_pct,
            'is_finished': current_term >= total_terms,
            'lender': metadata.get('lender', ''),
            'next_due_date': obligation.due_date.isoformat() if obligation.due_date else None
        }

        # Compute Early Payoff Discount per Consumer Protection Regulations (2023)
        if subtype == 'HIRE_PURCHASE' and total_terms > 0:
            financed_amount = Decimal(str(metadata.get('financed_amount', metadata.get('total_principal', '0.00'))))
            flat_rate_pa = Decimal(str(metadata.get('flat_rate_pa', '0.00')))
            vat_pct = Decimal(str(metadata.get('vat_pct', '7.00')))

            total_years = Decimal(str(total_terms)) / Decimal('12.0')
            total_interest = financed_amount * (flat_rate_pa / Decimal('100.0')) * total_years
            monthly_interest = (total_interest / Decimal(str(total_terms))).quantize(Decimal('0.01'))
            monthly_principal = (financed_amount / Decimal(str(total_terms))).quantize(Decimal('0.01'))

            remaining_principal = monthly_principal * Decimal(str(remaining_terms))
            remaining_interest = monthly_interest * Decimal(str(remaining_terms))

            ratio = Decimal(str(current_term)) / Decimal(str(total_terms))
            if ratio <= Decimal('0.3334'):
                discount_pct = Decimal('60.0')
            elif ratio <= Decimal('0.6667'):
                discount_pct = Decimal('70.0')
            else:
                discount_pct = Decimal('100.0')

            discounted_interest = (remaining_interest * (Decimal('1.0') - discount_pct / Decimal('100.0'))).quantize(Decimal('0.01'))
            payoff_subtotal = remaining_principal + discounted_interest
            payoff_vat = (payoff_subtotal * (vat_pct / Decimal('100.0'))).quantize(Decimal('0.01'))
            early_payoff_total = (payoff_subtotal + payoff_vat).quantize(Decimal('0.01'))

            summary['early_payoff'] = {
                'remaining_principal': remaining_principal,
                'remaining_interest_before_discount': remaining_interest,
                'discount_pct': discount_pct,
                'discounted_interest': discounted_interest,
                'payoff_vat': payoff_vat,
                'early_payoff_total': early_payoff_total
            }

        return summary

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '', **kwargs) -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory, ObligationStatus

        metadata = obligation.metadata or {}
        subtype = getattr(obligation, 'subtype', None) or metadata.get('subtype', 'STANDARD')

        # BNPL Parent Account (Revolving Credit Line)
        if subtype == 'BNPL_ACCOUNT':
            summary_before = self.get_summary(obligation)
            timeline = summary_before.get('statement_timeline', [])
            current_statement = summary_before.get('current_statement')

            # Identify target statement month (e.g. "2026-11")
            target_statement_month = kwargs.get('statement_month') or metadata.get('target_statement_month')
            target_statement = None
            if target_statement_month:
                target_statement = next((s for s in timeline if s.get('statement_month') == target_statement_month), None)
            if not target_statement:
                target_statement = current_statement

            if not target_statement:
                raise ValueError("There is no outstanding statement bill to pay.")

            target_statement_month = target_statement.get('statement_month')
            due_day = int(metadata.get('due_day', obligation.billing_day or 10))
            statement_due = Decimal(str(target_statement.get('total_due', '0.00')))

            if statement_due <= Decimal('0.00'):
                raise ValueError("There is no outstanding statement bill to pay.")

            if paid_amount is None:
                paid_amount = statement_due
            else:
                paid_amount = Decimal(str(paid_amount))
                if paid_amount != statement_due:
                    raise ValueError(f"Partial payment is not supported. Full statement amount of ฿{statement_due:,.2f} is required for {target_statement_month}.")

            with transaction.atomic():
                month_display = target_statement.get('month_label') or target_statement_month
                sub_order_advances = []

                # Advance term for orders due in this statement cycle
                for sub_order in obligation.sub_orders.filter(status='ACTIVE'):
                    s_meta = sub_order.metadata or {}
                    s_total = int(s_meta.get('total_terms', 1))
                    s_current = int(s_meta.get('current_term', 0))
                    prev_due = sub_order.due_date.isoformat() if sub_order.due_date else None
                    prev_status = sub_order.status

                    should_advance = False
                    next_term = s_current + 1

                    if target_statement_month:
                        o_date_str = s_meta.get('order_date')
                        if o_date_str:
                            try:
                                base_date = datetime.date.fromisoformat(o_date_str)
                            except ValueError:
                                base_date = sub_order.created_at.date() if sub_order.created_at else timezone.localdate()
                        else:
                            raw_date = sub_order.created_at.date() if sub_order.created_at else timezone.localdate()
                            if s_current > 0:
                                from dateutil.relativedelta import relativedelta
                                base_date = raw_date - relativedelta(months=s_current)
                            else:
                                base_date = raw_date

                        total_months = (base_date.year * 12 + (base_date.month - 1)) + next_term
                        t_year = total_months // 12
                        t_month = (total_months % 12) + 1
                        m_key = f"{t_year:04d}-{t_month:02d}"

                        if m_key == target_statement_month:
                            should_advance = True
                    else:
                        should_advance = True

                    if should_advance:
                        new_term = s_current + 1
                        s_meta['current_term'] = new_term
                        sub_order.metadata = s_meta

                        sub_order_advances.append({
                            'sub_order_id': str(sub_order.id),
                            'prev_term': s_current,
                            'new_term': new_term,
                            'prev_status': prev_status,
                            'prev_due_date': prev_due
                        })

                        if new_term >= s_total:
                            sub_order.status = ObligationStatus.COMPLETED
                            sub_order.due_date = None
                        else:
                            o_date_str = s_meta.get('order_date')
                            if o_date_str:
                                try:
                                    base_date = datetime.date.fromisoformat(o_date_str)
                                except ValueError:
                                    base_date = sub_order.created_at.date() if sub_order.created_at else timezone.localdate()
                            else:
                                raw_date = sub_order.created_at.date() if sub_order.created_at else timezone.localdate()
                                if s_current > 0:
                                    from dateutil.relativedelta import relativedelta
                                    base_date = raw_date - relativedelta(months=s_current)
                                else:
                                    base_date = raw_date

                            sub_order.due_date = self.calculate_term_due_date(base_date, new_term + 1, due_day)

                        sub_order.save()

                # 1. Record billing cycle payment history with advances snapshot
                payment = PaymentHistory.objects.create(
                    user=obligation.user,
                    obligation=obligation,
                    paid_amount=paid_amount,
                    note=note or f"Settled statement bill for {month_display} ({metadata.get('provider', obligation.title)})",
                    metadata={
                        'statement_month': target_statement_month,
                        'sub_order_advances': sub_order_advances
                    }
                )

                # 3. Parent BNPL account remains ACTIVE (revolving credit)
                obligation.status = ObligationStatus.ACTIVE
                new_summary = self.get_summary(obligation)
                if new_summary.get('next_due_date'):
                    try:
                        obligation.due_date = datetime.date.fromisoformat(new_summary['next_due_date'])
                    except (ValueError, TypeError):
                        obligation.due_date = None
                else:
                    obligation.due_date = None
                obligation.save()

            new_summary['payment_id'] = str(payment.id)
            return new_summary

        # Standard Installments & Vehicle Hire Purchase
        scheduled_amount = obligation.amount
        if paid_amount is None:
            paid_amount = scheduled_amount
        else:
            paid_amount = Decimal(str(paid_amount))
            if paid_amount != scheduled_amount:
                raise ValueError(f"Partial payment is not supported. Scheduled installment amount of ฿{scheduled_amount:,.2f} is required.")

        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        if current_term >= total_terms or obligation.status == ObligationStatus.COMPLETED:
            raise ValueError(f"Installment is already fully completed ({current_term}/{total_terms} terms paid).")

        next_term = current_term + 1
        if term_number is not None:
            if term_number != next_term:
                raise ValueError(f"Cannot skip terms. Expected next term {next_term}, but got {term_number}.")

        with transaction.atomic():
            # 1. Record payment history with reversal snapshot
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                term_number=next_term,
                note=note,
                metadata={
                    'prev_term': current_term,
                    'prev_due_date': obligation.due_date.isoformat() if obligation.due_date else None,
                    'prev_status': obligation.status
                }
            )

            # 2. Update term in metadata
            metadata['current_term'] = next_term
            obligation.metadata = metadata

            # 3. Check if all terms completed
            if next_term >= total_terms:
                obligation.status = ObligationStatus.COMPLETED
                obligation.due_date = None
            else:
                base_due = obligation.due_date or timezone.localdate()
                obligation.due_date = self.calculate_next_due_date(
                    base_due,
                    billing_day=obligation.billing_day,
                    months_to_add=1
                )

            obligation.save()

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
