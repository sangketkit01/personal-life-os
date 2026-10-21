from .installment import InstallmentStrategy
from .subscription import SubscriptionStrategy
from .free_trial import FreeTrialStrategy
from .debt import DebtStrategy


class ObligationStrategyFactory:
    """Factory สำหรับคืน Strategy instance ตามประเภทของภาระผูกพัน"""

    _strategies = {
        'INSTALLMENT': InstallmentStrategy(),
        'SUBSCRIPTION': SubscriptionStrategy(),
        'FREE_TRIAL': FreeTrialStrategy(),
        'DEBT': DebtStrategy(),
    }

    @classmethod
    def get_strategy(cls, obligation_type: str):
        strategy = cls._strategies.get(obligation_type)
        if not strategy:
            raise ValueError(f"ไม่พบ Strategy สำหรับประเภท: {obligation_type}")
        return strategy
