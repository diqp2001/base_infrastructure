from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor


class CurrencyValueFactorPort(ABC):
    """Port interface for CurrencyValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyValueFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyValueFactor) -> Optional[CurrencyValueFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyValueFactor) -> Optional[CurrencyValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyValueFactor]: ...
