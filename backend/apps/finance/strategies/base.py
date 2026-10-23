import calendar
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any
from datetime import date
from dateutil.relativedelta import relativedelta


class BaseObligationStrategy(ABC):
    """Abstract Strategy for financial obligation domain logic."""

    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize obligation metadata per subtype requirements."""
        pass

    @abstractmethod
    def get_summary(self, obligation) -> Dict[str, Any]:
        """Calculate and return runtime summary metrics (balances, terms, countdowns)."""
        pass

    @abstractmethod
    def on_paid(self, obligation, paid_amount: Decimal, term_number: int = None, note: str = '', **kwargs) -> Dict[str, Any]:
        """Domain transition handler when payment or settlement occurs."""
        pass

    @staticmethod
    def calculate_next_due_date(current_due_date: date, billing_day: int = None, months_to_add: int = 1) -> date:
        """
        Advance due date safely by N months.
        Handles end-of-month clamping (e.g. Jan 31 -> Feb 28/29)
        and preserves original billing_day when future months permit.
        """
        if not current_due_date:
            return None

        # Advance months
        next_month_date = current_due_date + relativedelta(months=months_to_add)

        # Preserve original billing_day clamped to target month's maximum days
        target_day = billing_day or current_due_date.day
        max_day = calendar.monthrange(next_month_date.year, next_month_date.month)[1]
        clamped_day = min(target_day, max_day)
        return next_month_date.replace(day=clamped_day)
