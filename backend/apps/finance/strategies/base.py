import calendar
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any
from datetime import date
from dateutil.relativedelta import relativedelta


class BaseObligationStrategy(ABC):
    """Abstract Strategy สำหรับแต่ละประเภทของภาระทางการเงิน"""

    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ตรวจสอบความถูกต้องของ metadata ตามประเภท"""
        pass

    @abstractmethod
    def get_summary(self, obligation) -> Dict[str, Any]:
        """ดึงข้อมูลสรุปสถานะ (เช่น งวดที่เหลือ, ยอดคงเหลือ, วันนับถอยหลัง)"""
        pass

    @abstractmethod
    def on_paid(self, obligation, paid_amount: Decimal, term_number: int = None, note: str = '') -> Dict[str, Any]:
        """ตรรกะเมื่อมีการจ่ายเงิน/ตัดรอบ"""
        pass

    @staticmethod
    def calculate_next_due_date(current_due_date: date, billing_day: int = None, months_to_add: int = 1) -> date:
        """
        เลื่อนวันครบกำหนดไปอีก N เดือนอย่างปลอดภัย
        รับมือกับกรณีสิ้นเดือน (เช่น วันที่ 31 มกราคม เลื่อนไป 1 เดือน จะกลายเป็น 28/29 กุมภาพันธ์)
        และถ้าเดือนถัดไปมี 31 วันอีกครั้ง จะกลับไปใช้วันที่ billing_day เดิม
        """
        if not current_due_date:
            return None

        # หาเดือนถัดไป
        next_month_date = current_due_date + relativedelta(months=months_to_add)

        # หากมีการระบุ billing_day ดั้งเดิมไว้ ให้พยายามใช้วันนั้น
        target_day = billing_day or current_due_date.day
        max_day = calendar.monthrange(next_month_date.year, next_month_date.month)[1]
        clamped_day = min(target_day, max_day)
        return next_month_date.replace(day=clamped_day)
