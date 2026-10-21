from decimal import Decimal
from typing import Dict, Any
from datetime import date
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class FreeTrialStrategy(BaseObligationStrategy):
    """
    Strategy สำหรับดักจับ Free Trial (กันลืมยกเลิก!)
    - นับถอยหลังวันหมดอายุ
    - จำแนกระดับความเร่งด่วน: CRITICAL (<= 1 วัน), WARNING (<= 3 วัน), SAFE (> 3 วัน)
    - รองรับการกดยกเลิกแล้วเปลี่ยนเป็น CANCELLED (ไม่ลบทิ้ง)
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'account_email': str(metadata.get('account_email', '')).strip(),
            'linked_card': str(metadata.get('linked_card', '')).strip(),
            'cancel_url': str(metadata.get('cancel_url', '')).strip(),
            'auto_renew_cost': str(Decimal(str(metadata.get('auto_renew_cost', 0.0))))
        }

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        today = timezone.localdate()

        days_remaining = None
        urgency = 'SAFE'

        if obligation.due_date:
            days_remaining = (obligation.due_date - today).days
            if days_remaining < 0:
                urgency = 'EXPIRED'
            elif days_remaining <= 1:
                urgency = 'CRITICAL'
            elif days_remaining <= 3:
                urgency = 'WARNING'
            else:
                urgency = 'SAFE'

        return {
            'account_email': metadata.get('account_email', ''),
            'linked_card': metadata.get('linked_card', ''),
            'cancel_url': metadata.get('cancel_url', ''),
            'auto_renew_cost': Decimal(str(metadata.get('auto_renew_cost', obligation.amount))),
            'days_remaining': days_remaining,
            'urgency': urgency,
            'is_cancelled': obligation.status == 'CANCELLED'
        }

    def cancel(self, obligation) -> Dict[str, Any]:
        """กดยกเลิก Free Trial สำเร็จ เปลี่ยนสถานะเป็น CANCELLED"""
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
                note=note or 'ตัดเงินอัตโนมัติหลังหมดช่วง Free Trial'
            )
        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
