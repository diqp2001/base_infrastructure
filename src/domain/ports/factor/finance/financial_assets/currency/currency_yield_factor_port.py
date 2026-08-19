from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor


class CurrencyYieldFactorPort(ABC):
    """Port interface for CurrencyYieldFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyYieldFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyYieldFactor) -> Optional[CurrencyYieldFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyYieldFactor) -> Optional[CurrencyYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyYieldFactor]: ...
