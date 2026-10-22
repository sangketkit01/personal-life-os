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
        subtype = metadata.get('subtype', 'INFORMAL_BORROW')
        counterparty = str(metadata.get('counterparty', '')).strip()
        is_flexible = bool(metadata.get('is_flexible', False))
        contact = str(metadata.get('contact', '')).strip()
        reason = str(metadata.get('reason', '')).strip()
        promptpay = str(metadata.get('promptpay', '')).strip()

        # ยอดคงเหลือเริ่มต้น ถ้ายังไม่มี ให้ตั้งเท่ากับยอดเต็ม
        remaining_balance = metadata.get('remaining_balance')
        if remaining_balance is not None:
            remaining_balance = str(Decimal(str(remaining_balance)))

        validated = {
            'subtype': subtype,
            'counterparty': counterparty,
            'is_flexible': is_flexible,
            'contact': contact,
            'reason': reason,
            'promptpay': promptpay,
            'remaining_balance': remaining_balance
        }

        # เสริมข้อมูลสินเชื่อทางการ (Formal Loan)
        if subtype == 'FORMAL_LOAN':
            validated.update({
                'interest_rate_pa': str(Decimal(str(metadata.get('interest_rate_pa', '0.00')))),
                'min_monthly_payment': str(Decimal(str(metadata.get('min_monthly_payment', '0.00')))),
                'creditor_bank': str(metadata.get('creditor_bank', '')).strip(),
                'contract_no': str(metadata.get('contract_no', '')).strip()
            })

        return validated

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        subtype = getattr(obligation, 'subtype', None) or metadata.get('subtype', 'INFORMAL_BORROW')
        counterparty = metadata.get('counterparty', 'Counterparty')
        is_flexible = metadata.get('is_flexible', False)
        promptpay = metadata.get('promptpay', '')

        remaining_balance_raw = metadata.get('remaining_balance')
        if remaining_balance_raw is None:
            remaining_balance = obligation.amount
        else:
            remaining_balance = Decimal(str(remaining_balance_raw))

        initial_amount = obligation.amount
        total_paid = max(Decimal('0'), initial_amount - remaining_balance)

        progress_pct = round((total_paid / initial_amount) * 100, 1) if initial_amount > 0 else 0.0

        due_date_str = obligation.due_date.strftime('%d/%m/%Y') if obligation.due_date else 'soon'

        # Generate recall reminder message for debtor receivables (INFLOW)
        recall_template = ""
        if obligation.direction == 'INFLOW':
            pp_text = f"PromptPay {promptpay}" if promptpay else "the designated account"
            cur = obligation.currency or 'THB'
            cur_symbol = '฿' if cur == 'THB' else cur
            recall_template = (
                f"Hi {counterparty}, friendly reminder regarding the outstanding balance of "
                f"{cur_symbol}{remaining_balance:,.2f} (due: {due_date_str}). "
                f"When convenient, please transfer to {pp_text}. Thank you!"
            )

        summary = {
            'subtype': subtype,
            'counterparty': counterparty,
            'is_flexible': is_flexible,
            'initial_amount': initial_amount,
            'remaining_balance': remaining_balance,
            'total_paid': total_paid,
            'paid_total': total_paid,
            'progress_pct': progress_pct,
            'progress_percentage': progress_pct,
            'is_settled': remaining_balance <= Decimal('0'),
            'recall_template': recall_template,
            'promptpay': promptpay
        }

        if subtype == 'FORMAL_LOAN':
            summary.update({
                'interest_rate_pa': Decimal(str(metadata.get('interest_rate_pa', '0.00'))),
                'min_monthly_payment': Decimal(str(metadata.get('min_monthly_payment', '0.00'))),
                'creditor_bank': metadata.get('creditor_bank', ''),
                'contract_no': metadata.get('contract_no', '')
            })

        return summary

    def on_paid(self, obligation, paid_amount: Decimal, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory, ObligationStatus

        if paid_amount is None or paid_amount <= Decimal('0'):
            raise ValueError("Payment amount must be greater than 0.")

        metadata = obligation.metadata or {}
        remaining_balance_raw = metadata.get('remaining_balance')
        if remaining_balance_raw is None:
            current_remaining = obligation.amount
        else:
            current_remaining = Decimal(str(remaining_balance_raw))

        with transaction.atomic():
            # 1. Record payment history
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
