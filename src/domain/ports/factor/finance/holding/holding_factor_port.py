from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.holding_factor import HoldingFactor


class HoldingFactorPort(ABC):
    """Port interface for HoldingFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[HoldingFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[HoldingFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[HoldingFactor]: ...

    @abstractmethod
    def get_all(self) -> List[HoldingFactor]: ...

    @abstractmethod
    def add(self, entity: HoldingFactor) -> Optional[HoldingFactor]: ...

    @abstractmethod
    def update(self, entity: HoldingFactor) -> Optional[HoldingFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[HoldingFactor]: ...
