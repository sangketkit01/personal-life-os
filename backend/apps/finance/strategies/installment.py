from decimal import Decimal
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class InstallmentStrategy(BaseObligationStrategy):
    """
    Strategy สำหรับรายการผ่อนชำระ (เช่น ผ่อนมอเตอร์ไซค์, ผ่อน TikTok Shop, SPayLater)
    - ติดตามงวด 14/36
    - คำนวณยอดหนี้คงเหลือและ Progress Bar
    - เมื่อจ่ายงวดสุดท้าย (36/36) เปลี่ยนสถานะเป็น COMPLETED อัตโนมัติ
    """

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        if total_terms <= 0:
            raise ValueError("จำนวนงวดทั้งหมด (total_terms) ต้องมากกว่า 0")
        if current_term < 0:
            raise ValueError("งวดปัจจุบัน (current_term) ต้องไม่ติดลบ")
        if current_term > total_terms:
            raise ValueError("งวดปัจจุบันต้องไม่เกินจำนวนงวดทั้งหมด")

        return {
            'total_terms': total_terms,
            'current_term': current_term,
            'lender': str(metadata.get('lender', '')).strip(),
            'total_principal': str(Decimal(str(metadata.get('total_principal', '0.00')))),
            'auto_pay': bool(metadata.get('auto_pay', False))
        }

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        remaining_terms = max(0, total_terms - current_term)
        remaining_balance = Decimal(str(remaining_terms)) * obligation.amount

        progress_pct = round((current_term / total_terms) * 100, 1) if total_terms > 0 else 0.0

        return {
            'total_terms': total_terms,
            'current_term': current_term,
            'remaining_terms': remaining_terms,
            'remaining_balance': remaining_balance,
            'progress_pct': progress_pct,
            'is_finished': current_term >= total_terms,
            'lender': metadata.get('lender', '')
        }

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory, ObligationStatus

        if paid_amount is None:
            paid_amount = obligation.amount

        metadata = obligation.metadata or {}
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        next_term = current_term + 1
        if term_number is not None:
            next_term = term_number

        with transaction.atomic():
            # 1. บันทึกประวัติการจ่าย
            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                term_number=next_term,
                note=note
            )

            # 2. ปรับปรุงงวดใน metadata
            metadata['current_term'] = next_term
            obligation.metadata = metadata

            # 3. ตรวจสอบว่างวดสุดท้ายหรือยัง
            if next_term >= total_terms:
                obligation.status = ObligationStatus.COMPLETED
                # เมื่อผ่อนหมดแล้ว ไม่มีวันครบกำหนดถัดไป
                obligation.due_date = None
            else:
                base_due = obligation.due_date or timezone.localdate()
                # เลื่อนวันครบกำหนดไปเดือนถัดไปอย่างปลอดภัย
                obligation.due_date = self.calculate_next_due_date(
                    base_due,
                    billing_day=obligation.billing_day,
                    months_to_add=1
                )

            obligation.save()

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
