from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_annualized_roll_yield_factor import FutureAnnualizedRollYieldFactor


class FutureAnnualizedRollYieldFactorPort(ABC):
    """Port interface for FutureAnnualizedRollYieldFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def add(self, entity: FutureAnnualizedRollYieldFactor) -> Optional[FutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def update(self, entity: FutureAnnualizedRollYieldFactor) -> Optional[FutureAnnualizedRollYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FutureAnnualizedRollYieldFactor]: ...
