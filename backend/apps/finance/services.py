from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List
from django.utils import timezone
from .models import FinancialObligation, ObligationStatus, ObligationType, FlowDirection
from .strategies import ObligationStrategyFactory


def get_exchange_rate_to_thb(currency: str) -> Decimal:
    """ดึงอัตราแลกเปลี่ยนเป็นบาท (THB) โดยอิงจากแคชหรือตลาดสด"""
    clean_curr = (currency or 'THB').strip().upper()
    if clean_curr == 'THB':
        return Decimal('1.0000')
    if clean_curr == 'USD':
        try:
            from apps.portfolio.services import get_usd_to_thb_rate
            rate = get_usd_to_thb_rate()
            if rate and rate > 0:
                return rate
        except Exception:
            pass
        return Decimal('35.0000')
    return Decimal('1.0000')


def get_financial_overview(user, target_date: date = None) -> Dict[str, Any]:
    """
    คำนวณสรุปสถานะการเงินประจำเดือนสำหรับ Dashboard:
    - Monthly Burn Rate (ภาระคงที่ที่ต้องเตรียมเงินจ่ายออกเดือนนี้ แปลงเป็น THB)
    - Expected Inflow (ยอดเงินที่คาดว่าจะได้รับคืนเดือนนี้ เช่น หนี้ที่คนอื่นยืมไป)
    - Potential Liability (ความเสี่ยงจาก Free Trial ที่อาจโดนตัดเงิน แปลงเป็น THB)
    - Upcoming Bills in 7 Days (รายการที่จะถึงกำหนดใน 7 วันข้างหน้า)
    - สรุปรายการตามประเภท
    """
    if target_date is None:
        target_date = timezone.localdate()

    target_year = target_date.year
    target_month = target_date.month

    # ดึงเฉพาะรายการที่ ACTIVE ของ User คนนี้เท่านั้น (Strict Multi-Tenancy)
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

        # จัดกลุ่มตาม Type
        categorized_items[ob.type].append(item_data)

        # 1. การคำนวณรายจ่าย (Burn Rate) และรายรับ (Expected Inflows) ประจำเดือน
        if ob.direction == FlowDirection.INFLOW:
            # รายการเงินไหลเข้า (เช่น เพื่อนคืนหนี้ / เงินได้คงที่)
            if ob.type == ObligationType.DEBT:
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    remaining = summary.get('remaining_balance', ob.amount)
                    expected_inflow_amount += (Decimal(str(remaining)) * rate).quantize(Decimal('0.01'))
            elif ob.type in [ObligationType.SUBSCRIPTION, ObligationType.INSTALLMENT]:
                expected_inflow_amount += amount_thb
        else:
            # รายการเงินไหลออก (OUTFLOW - ภาระค่าใช้จ่ายจริง)
            if ob.type == ObligationType.INSTALLMENT:
                if ob.parent_id:
                    # รายการซื้อย่อย BNPL: ไม่นำมารวมซ้ำเดี่ยวๆ เพราะถูกนับรวมในรอบบิลของบัญชีแม่แล้ว
                    pass
                elif getattr(ob, 'subtype', '') == 'BNPL_ACCOUNT':
                    # บัญชีแม่ BNPL: นำยอดบิลรวมของรอบเดือนปัจจุบันมาคำนวณ Burn rate
                    current_bill = summary.get('current_bill_amount', Decimal('0.00'))
                    confirmed_burn_rate += (Decimal(str(current_bill)) * rate).quantize(Decimal('0.01'))
                else:
                    # ค่างวดผ่อนทั่วไป และสัญญาเช่าซื้อรถ (Hire Purchase)
                    if not summary.get('is_finished', False):
                        confirmed_burn_rate += amount_thb

            elif ob.type == ObligationType.SUBSCRIPTION:
                is_yearly = summary.get('is_yearly', False)
                if is_yearly:
                    # รายปี: นับเป็นยอดเต็มเฉพาะเดือนที่ตัดเงินจริง
                    if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                        confirmed_burn_rate += amount_thb
                else:
                    # รายเดือน: นับทุกเดือน
                    confirmed_burn_rate += amount_thb

            elif ob.type == ObligationType.DEBT:
                # หนี้สินที่ต้องชำระคืน: ถ้าระบุวันคืนในเดือนนี้ ให้นับเป็นภาระ
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    remaining = summary.get('remaining_balance', ob.amount)
                    confirmed_burn_rate += (Decimal(str(remaining)) * rate).quantize(Decimal('0.01'))

            elif ob.type == ObligationType.FREE_TRIAL:
                active_trials_count += 1
                if summary.get('urgency') in ['CRITICAL', 'WARNING']:
                    critical_trials_count += 1

                # ยอด Free Trial เก็บเป็น Potential Risk (ถ้าหมดอายุในเดือนนี้)
                if ob.due_date and ob.due_date.year == target_year and ob.due_date.month == target_month:
                    auto_renew = summary.get('auto_renew_cost', ob.amount)
                    potential_risk_amount += (Decimal(str(auto_renew)) * rate).quantize(Decimal('0.01'))

        # 2. ตรวจสอบรายการที่ต้องจ่ายใน 7 วันข้างหน้า
        if ob.due_date and today <= ob.due_date <= next_7_days:
            upcoming_7_days.append({
                'id': str(ob.id),
                'title': ob.title,
                'type': ob.type,
                'direction': ob.direction,
                'amount': ob.amount,
                'amount_thb': amount_thb,
                'currency': ob.currency,
                'due_date': ob.due_date.isoformat(),
                'days_left': (ob.due_date - today).days,
                'is_trial': ob.type == ObligationType.FREE_TRIAL,
                'summary': summary
            })

    # เรียงลำดับรายการใน 7 วันตามความใกล้-ไกลของกำหนด
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
