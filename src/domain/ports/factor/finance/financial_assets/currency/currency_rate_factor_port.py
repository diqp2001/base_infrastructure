from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor


class CurrencyRateFactorPort(ABC):
    """Port interface for CurrencyRateFactor repositories (IBKR leaf factor for FX rates)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyRateFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyRateFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyRateFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyRateFactor) -> Optional[CurrencyRateFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyRateFactor) -> Optional[CurrencyRateFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyRateFactor]: ...
