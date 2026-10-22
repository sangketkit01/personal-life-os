from decimal import Decimal
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class FreeTrialStrategy(BaseObligationStrategy):
    """
    Strategy for Free Trial Watchdog (Prevents surprise renewals!)
    - Expiration countdown with urgency tiers:
      CRITICAL (<= 1 day), WARNING (<= alert_days), SAFE (> alert_days), EXPIRED (< 0 days)
    - Supports 1-click status transition to CANCELLED
    - Retains auto-renew cost liability metrics
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert_days = int(metadata.get('alert_days_before', 3))
        except (ValueError, TypeError):
            alert_days = 3

        try:
            auto_renew_cost = Decimal(str(metadata.get('auto_renew_cost', '0.00')))
        except Exception:
            auto_renew_cost = Decimal('0.00')

        return {
            'plan_name': str(metadata.get('plan_name', '')).strip(),
            'account_email': str(metadata.get('account_email', '')).strip(),
            'linked_card': str(metadata.get('linked_card', metadata.get('payment_method', ''))).strip(),
            'payment_method': str(metadata.get('payment_method', metadata.get('linked_card', ''))).strip(),
            'category': str(metadata.get('category', 'GENERAL')).strip().upper(),
            'cancel_url': str(metadata.get('cancel_url', '')).strip(),
            'cancel_steps': str(metadata.get('cancel_steps', '')).strip(),
            'alert_days_before': alert_days,
            'auto_renew_cost': str(auto_renew_cost),
            'documents': metadata.get('documents', []) if isinstance(metadata.get('documents'), list) else [],
            'notes': str(metadata.get('notes', '')).strip()
        }

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        today = timezone.localdate()

        days_remaining = None
        urgency = 'SAFE'

        alert_days = int(metadata.get('alert_days_before', 3))

        if obligation.due_date:
            days_remaining = (obligation.due_date - today).days
            if days_remaining < 0:
                urgency = 'EXPIRED'
            elif days_remaining <= 1:
                urgency = 'CRITICAL'
            elif days_remaining <= alert_days:
                urgency = 'WARNING'
            else:
                urgency = 'SAFE'

        auto_renew_cost = Decimal(str(metadata.get('auto_renew_cost', obligation.amount or '0.00')))

        return {
            'plan_name': metadata.get('plan_name', ''),
            'account_email': metadata.get('account_email', ''),
            'linked_card': metadata.get('linked_card', metadata.get('payment_method', '')),
            'payment_method': metadata.get('payment_method', metadata.get('linked_card', '')),
            'category': metadata.get('category', 'GENERAL'),
            'cancel_url': metadata.get('cancel_url', ''),
            'cancel_steps': metadata.get('cancel_steps', ''),
            'alert_days_before': alert_days,
            'auto_renew_cost': auto_renew_cost,
            'days_remaining': days_remaining,
            'days_left': days_remaining,
            'urgency': urgency,
            'is_cancelled': obligation.status == 'CANCELLED',
            'documents': metadata.get('documents', [])
        }

    def cancel(self, obligation) -> Dict[str, Any]:
        """Mark trial as cancelled, transitioning status to CANCELLED"""
        from apps.finance.models import ObligationStatus
        obligation.status = ObligationStatus.CANCELLED
        obligation.save(update_fields=['status', 'updated_at'])
        return self.get_summary(obligation)

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory
        if paid_amount is None:
            paid_amount = obligation.amount

        with transaction.atomic():
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                note=note or 'Auto-renew charge after free trial expiration'
            )
        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
