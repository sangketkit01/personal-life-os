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
        subtype = metadata.get('subtype', 'STANDARD')

        # 1. วงเงินเครดิตช้อปปิ้งออนไลน์ BNPL Account (SPayLater, LazPayLater, TikTok)
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

        # 2. รายการปกติ, รายการซื้อย่อย BNPL, และสัญญาเช่าซื้อรถ (Hire Purchase)
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        if total_terms <= 0:
            raise ValueError("Total terms must be greater than 0.")
        if current_term < 0:
            raise ValueError("Current term cannot be negative.")
        if current_term > total_terms:
            raise ValueError("Current term cannot exceed total terms.")

        validated = {
            'subtype': subtype,
            'total_terms': total_terms,
            'current_term': current_term,
            'lender': str(metadata.get('lender', '')).strip(),
            'total_principal': str(Decimal(str(metadata.get('total_principal', '0.00')))),
            'auto_pay': bool(metadata.get('auto_pay', False)),
            'contract_number': str(metadata.get('contract_number', '')).strip(),
            'notes': str(metadata.get('notes', '')).strip(),
            # BNPL Sub-Order specifics
            'store': str(metadata.get('store', '')).strip(),
            'order_number': str(metadata.get('order_number', '')).strip(),
            'order_date': str(metadata.get('order_date', '')).strip() if metadata.get('order_date') else None,
            'item_name': str(metadata.get('item_name', '')).strip(),
        }

        # Additional metadata for Vehicle Hire Purchase & Loan contracts
        if subtype == 'HIRE_PURCHASE':
            validated.update({
                'vehicle_model': str(metadata.get('vehicle_model', '')).strip(),
                'down_payment': str(Decimal(str(metadata.get('down_payment', '0.00')))),
                'financed_amount': str(Decimal(str(metadata.get('financed_amount', metadata.get('total_principal', '0.00'))))),
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

        # 1. Summary สำหรับบัญชีแม่ BNPL Account (SPayLater / LazPayLater)
        if subtype == 'BNPL_ACCOUNT':
            sub_orders = obligation.sub_orders.filter(status='ACTIVE')
            credit_limit = Decimal(str(metadata.get('credit_limit', '0.00')))
            
            # คำนวณยอดที่ต้องชำระในรอบบิลปัจจุบันจากผลรวมของ Order ลูก
            current_bill_amount = Decimal('0.00')
            total_remaining_debt = Decimal('0.00')

            orders_summary = []
            for order in sub_orders:
                order_meta = order.metadata or {}
                o_total_terms = int(order_meta.get('total_terms', 1))
                o_current_term = int(order_meta.get('current_term', 0))
                o_remaining_terms = max(0, o_total_terms - o_current_term)
                o_remaining_balance = Decimal(str(o_remaining_terms)) * order.amount

                current_bill_amount += order.amount
                total_remaining_debt += o_remaining_balance

                orders_summary.append({
                    'id': str(order.id),
                    'title': order.title,
                    'amount': order.amount,
                    'current_term': o_current_term,
                    'total_terms': o_total_terms,
                    'remaining_balance': o_remaining_balance
                })

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
                'due_day': metadata.get('due_day', 10),
                'sub_orders': orders_summary,
                'next_due_date': obligation.due_date.isoformat() if obligation.due_date else None
            }

        # 2. Summary สำหรับผ่อนทั่วไป และสัญญาเช่าซื้อรถ (Hire Purchase)
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

        # คำนวณส่วนลดปิดบัญชีก่อนกำหนดตามประกาศ สคบ. พ.ศ. 2566
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

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '') -> Dict[str, Any]:
        from apps.finance.models import PaymentHistory, ObligationStatus

        metadata = obligation.metadata or {}
        subtype = getattr(obligation, 'subtype', None) or metadata.get('subtype', 'STANDARD')

        # กรณีเป็นบัญชีแม่ BNPL Account (วงเงินหมุนเวียน Revolving Credit Line)
        if subtype == 'BNPL_ACCOUNT':
            summary_before = self.get_summary(obligation)
            if paid_amount is None:
                paid_amount = summary_before.get('current_bill_amount', obligation.amount)

            with transaction.atomic():
                # 1. บันทึกประวัติการจ่ายบิลรอบเดือน
                payment = PaymentHistory.objects.create(
                    user=obligation.user,
                    obligation=obligation,
                    paid_amount=paid_amount,
                    note=note or f"Payment for billing cycle {metadata.get('provider', obligation.title)}"
                )

                # 2. เลื่อนงวดของคำสั่งซื้อย่อยทั้งหมดที่ยัง ACTIVE
                for sub_order in obligation.sub_orders.filter(status='ACTIVE'):
                    s_meta = sub_order.metadata or {}
                    s_total = int(s_meta.get('total_terms', 1))
                    s_current = int(s_meta.get('current_term', 0)) + 1
                    s_meta['current_term'] = s_current
                    sub_order.metadata = s_meta

                    if s_current >= s_total:
                        sub_order.status = ObligationStatus.COMPLETED
                        sub_order.due_date = None
                    else:
                        s_base_due = sub_order.due_date or timezone.localdate()
                        sub_order.due_date = self.calculate_next_due_date(
                            s_base_due,
                            billing_day=sub_order.billing_day or metadata.get('due_day', 10),
                            months_to_add=1
                        )
                    sub_order.save()

                # 3. บัญชีแม่ BNPL ยังคงสถานะ ACTIVE เสมอ (วงเงินหมุนเวียน ไม่ปิดบัญชี)
                obligation.status = ObligationStatus.ACTIVE
                due_day = int(metadata.get('due_day', obligation.billing_day or 10))
                base_due = obligation.due_date or timezone.localdate()
                obligation.due_date = self.calculate_next_due_date(
                    base_due,
                    billing_day=due_day,
                    months_to_add=1
                )
                obligation.save()

            summary = self.get_summary(obligation)
            summary['payment_id'] = str(payment.id)
            return summary

        # กรณีรายการผ่อนทั่วไป และสัญญาเช่าซื้อรถ (Hire Purchase)
        if paid_amount is None:
            paid_amount = obligation.amount

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
