from decimal import Decimal
from typing import Dict, Any
from django.db import transaction
from .base import BaseObligationStrategy


class DebtStrategy(BaseObligationStrategy):
    """
    Strategy สำหรับหนี้สิน ยืม-คืน (Debt & Lending)
    - รองรับการทยอยจ่าย (Partial Payment)
    - ลดทอนยอดหนี้คงเหลือ จนกระทั่งครบ 0 จึงเปลี่ยนเป็น COMPLETED
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        counterparty = str(metadata.get('counterparty', '')).strip()
        is_flexible = bool(metadata.get('is_flexible', False))
        contact = str(metadata.get('contact', '')).strip()
        reason = str(metadata.get('reason', '')).strip()

        # ยอดคงเหลือเริ่มต้น ถ้ายังไม่มี ให้ตั้งเท่ากับยอดเต็ม
        remaining_balance = metadata.get('remaining_balance')
        if remaining_balance is not None:
            remaining_balance = str(Decimal(str(remaining_balance)))

        return {
            'counterparty': counterparty,
            'is_flexible': is_flexible,
            'contact': contact,
            'reason': reason,
            'remaining_balance': remaining_balance
        }

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        counterparty = metadata.get('counterparty', 'ไม่ระบุ')
        is_flexible = metadata.get('is_flexible', False)

        remaining_balance_raw = metadata.get('remaining_balance')
        if remaining_balance_raw is None:
            remaining_balance = obligation.amount
        else:
            remaining_balance = Decimal(str(remaining_balance_raw))

        initial_amount = obligation.amount
        total_paid = max(Decimal('0'), initial_amount - remaining_balance)

        progress_pct = round((total_paid / initial_amount) * 100, 1) if initial_amount > 0 else 0.0

        return {
            'counterparty': counterparty,
            'is_flexible': is_flexible,
            'initial_amount': initial_amount,
            'remaining_balance': remaining_balance,
            'total_paid': total_paid,
            'progress_pct': progress_pct,
            'is_settled': remaining_balance <= Decimal('0')
        }

    def on_paid(self, obligation, paid_amount: Decimal, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory, ObligationStatus

        if paid_amount is None or paid_amount <= Decimal('0'):
            raise ValueError("ยอดเงินที่ชำระต้องมากกว่า 0")

        metadata = obligation.metadata or {}
        remaining_balance_raw = metadata.get('remaining_balance')
        if remaining_balance_raw is None:
            current_remaining = obligation.amount
        else:
            current_remaining = Decimal(str(remaining_balance_raw))

        with transaction.atomic():
            # 1. บันทึกประวัติการจ่าย
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                note=note
            )

            # 2. คำนวณยอดหนี้คงเหลือใหม่
            new_remaining = current_remaining - paid_amount
            if new_remaining <= Decimal('0'):
                new_remaining = Decimal('0')
                obligation.status = ObligationStatus.COMPLETED
                obligation.due_date = None

            metadata['remaining_balance'] = float(round(new_remaining, 2))
            obligation.metadata = metadata
            obligation.save()

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
