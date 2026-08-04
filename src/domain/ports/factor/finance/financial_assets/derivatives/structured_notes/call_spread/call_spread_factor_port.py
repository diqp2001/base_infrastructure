from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_factor import CallSpreadFactor


class CallSpreadFactorPort(ABC):
    """Port interface for CallSpreadFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadFactor) -> Optional[CallSpreadFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadFactor) -> Optional[CallSpreadFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadFactor]: ...
