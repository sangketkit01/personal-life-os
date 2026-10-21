from decimal import Decimal
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class SubscriptionStrategy(BaseObligationStrategy):
    """
    Strategy สำหรับค่าบริการรายเดือน / รายปี (Netflix, iCloud, Spotify, VPS)
    - รองรับรอบ MONTHLY (รายเดือน) และ YEARLY (รายปี)
    - เมื่อจ่ายแล้ว จะเลื่อนวันครบกำหนดไปเดือนถัดไป (หรือปีถัดไป) อัตโนมัติ
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cycle = str(metadata.get('billing_cycle', 'MONTHLY')).upper()
        if cycle not in ['MONTHLY', 'YEARLY']:
            cycle = 'MONTHLY'

        return {
            'billing_cycle': cycle,
            'account_email': str(metadata.get('account_email', '')).strip(),
            'payment_method': str(metadata.get('payment_method', '')).strip(),
            'category': str(metadata.get('category', 'GENERAL')).strip()
        }

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY')

        return {
            'billing_cycle': billing_cycle,
            'is_yearly': billing_cycle == 'YEARLY',
            'account_email': metadata.get('account_email', ''),
            'payment_method': metadata.get('payment_method', ''),
            'category': metadata.get('category', 'GENERAL'),
            'amount_per_period': obligation.amount
        }

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory

        if paid_amount is None:
            paid_amount = obligation.amount

        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY')
        months_to_add = 12 if billing_cycle == 'YEARLY' else 1

        with transaction.atomic():
            # 1. บันทึกประวัติการจ่าย
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                note=note
            )

            # 2. เลื่อนวันครบกำหนดรอบถัดไป
            base_due = obligation.due_date or timezone.localdate()
            obligation.due_date = self.calculate_next_due_date(
                base_due,
                billing_day=obligation.billing_day,
                months_to_add=months_to_add
            )
            obligation.save()

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
