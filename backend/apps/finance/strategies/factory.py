from .installment import InstallmentStrategy
from .subscription import SubscriptionStrategy
from .free_trial import FreeTrialStrategy
from .debt import DebtStrategy


class ObligationStrategyFactory:
    """Factory returning domain strategy instance based on obligation type."""

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
            raise ValueError(f"Strategy not found for obligation type: {obligation_type}")
        return strategy
