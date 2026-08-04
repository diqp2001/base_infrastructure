from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_annualized_price_return_factor import FutureAnnualizedPriceReturnFactor


class FutureAnnualizedPriceReturnFactorPort(ABC):
    """Port interface for FutureAnnualizedPriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FutureAnnualizedPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FutureAnnualizedPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FutureAnnualizedPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: FutureAnnualizedPriceReturnFactor) -> Optional[FutureAnnualizedPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: FutureAnnualizedPriceReturnFactor) -> Optional[FutureAnnualizedPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FutureAnnualizedPriceReturnFactor]: ...
