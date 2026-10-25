from decimal import Decimal
from typing import Dict, Any
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class SubscriptionStrategy(BaseObligationStrategy):
    """
    Strategy for recurring SaaS / Subscriptions (Netflix, iCloud, Spotify, ChatGPT, VPS)
    - Supports MONTHLY, YEARLY, QUARTERLY, and WEEKLY cycles
    - Auto-rolls due_date forward upon payment recording
    - Computes normalized monthly burn and annualized cost
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cycle = str(metadata.get('billing_cycle', 'MONTHLY')).upper()
        if cycle not in ['MONTHLY', 'YEARLY', 'QUARTERLY', 'WEEKLY']:
            cycle = 'MONTHLY'

        try:
            alert_days = int(metadata.get('alert_days_before', 3))
        except (ValueError, TypeError):
            alert_days = 3

        validated = {
            'billing_cycle': cycle,
            'plan_name': str(metadata.get('plan_name', '')).strip(),
            'account_email': str(metadata.get('account_email', '')).strip(),
            'payment_method': str(metadata.get('payment_method', '')).strip(),
            'category': str(metadata.get('category', 'GENERAL')).strip().upper(),
            'cancel_url': str(metadata.get('cancel_url', '')).strip(),
            'cancel_steps': str(metadata.get('cancel_steps', '')).strip(),
            'alert_days_before': alert_days,
            'documents': metadata.get('documents', []) if isinstance(metadata.get('documents'), list) else [],
            'notes': str(metadata.get('notes', '')).strip()
        }

        # Preserve workspace bridge keys (MA contracts / infrastructure assets)
        # so linking metadata survives serializer round-trips.
        source_type = str(metadata.get('source_type', '')).strip().upper()
        if source_type in ('INFRA_ASSET', 'MA_CONTRACT'):
            validated['source_type'] = source_type
            for aux_key in ('asset_id', 'project_id'):
                aux_val = str(metadata.get(aux_key, '')).strip()
                if aux_val:
                    validated[aux_key] = aux_val
            client_name = str(metadata.get('client_name', '')).strip()
            if client_name:
                validated['client_name'] = client_name

        return validated

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY').upper()
        amount = Decimal(str(obligation.amount or '0.00'))

        # Calculate normalized monthly equivalent and annualized burn
        if billing_cycle == 'YEARLY':
            monthly_equivalent = (amount / Decimal('12.0')).quantize(Decimal('0.01'))
            annual_burn = amount
        elif billing_cycle == 'QUARTERLY':
            monthly_equivalent = (amount / Decimal('3.0')).quantize(Decimal('0.01'))
            annual_burn = (amount * Decimal('4.0')).quantize(Decimal('0.01'))
        elif billing_cycle == 'WEEKLY':
            monthly_equivalent = (amount * Decimal('4.3333')).quantize(Decimal('0.01'))
            annual_burn = (amount * Decimal('52.0')).quantize(Decimal('0.01'))
        else:
            monthly_equivalent = amount
            annual_burn = (amount * Decimal('12.0')).quantize(Decimal('0.01'))

        days_until_renewal = None
        urgency = 'SAFE'
        if obligation.due_date:
            today = timezone.localdate()
            days_until_renewal = (obligation.due_date - today).days
            if days_until_renewal < 0:
                urgency = 'EXPIRED'
            elif days_until_renewal <= 1:
                urgency = 'CRITICAL'
            elif days_until_renewal <= metadata.get('alert_days_before', 3):
                urgency = 'WARNING'
            else:
                urgency = 'SAFE'

        return {
            'billing_cycle': billing_cycle,
            'is_yearly': billing_cycle == 'YEARLY',
            'plan_name': metadata.get('plan_name', ''),
            'account_email': metadata.get('account_email', ''),
            'payment_method': metadata.get('payment_method', ''),
            'category': metadata.get('category', 'GENERAL'),
            'cancel_url': metadata.get('cancel_url', ''),
            'cancel_steps': metadata.get('cancel_steps', ''),
            'alert_days_before': metadata.get('alert_days_before', 3),
            'amount_per_period': amount,
            'monthly_equivalent': monthly_equivalent,
            'annual_burn': annual_burn,
            'days_until_renewal': days_until_renewal,
            'days_left': days_until_renewal,
            'urgency': urgency,
            'documents': metadata.get('documents', [])
        }

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '', **kwargs) -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory

        scheduled_amount = obligation.amount
        if paid_amount is None:
            paid_amount = scheduled_amount
        else:
            paid_amount = Decimal(str(paid_amount))
            if paid_amount != scheduled_amount:
                raise ValueError(f"Full subscription payment of ฿{scheduled_amount:,.2f} is required.")

        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY').upper()

        with transaction.atomic():
            # 1. Record payment history with reversal snapshot
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                note=note or f"Subscription renewal ({billing_cycle})",
                metadata={
                    'prev_due_date': obligation.due_date.isoformat() if obligation.due_date else None
                }
            )

            # 2. Advance due date
            base_due = obligation.due_date or timezone.localdate()
            if billing_cycle == 'WEEKLY':
                obligation.due_date = base_due + timedelta(days=7)
            else:
                months_to_add = 12 if billing_cycle == 'YEARLY' else (3 if billing_cycle == 'QUARTERLY' else 1)
                obligation.due_date = self.calculate_next_due_date(
                    base_due,
                    billing_day=obligation.billing_day,
                    months_to_add=months_to_add
                )
            obligation.save()

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
