from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor


class EquityFactorPort(ABC):
    """Port interface for EquityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[EquityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[EquityFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[EquityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[EquityFactor]: ...

    @abstractmethod
    def add(self, entity: EquityFactor) -> Optional[EquityFactor]: ...

    @abstractmethod
    def update(self, entity: EquityFactor) -> Optional[EquityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[EquityFactor]: ...
