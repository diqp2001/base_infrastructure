from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor


class CurrencyFactorPort(ABC):
    """Port interface for CurrencyFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CurrencyFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyFactor) -> Optional[CurrencyFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyFactor) -> Optional[CurrencyFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyFactor]: ...
