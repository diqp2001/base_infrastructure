from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_delta_factor import CallSpreadDeltaFactor


class CallSpreadDeltaFactorPort(ABC):
    """Port interface for CallSpreadDeltaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadDeltaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadDeltaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadDeltaFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadDeltaFactor) -> Optional[CallSpreadDeltaFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadDeltaFactor) -> Optional[CallSpreadDeltaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadDeltaFactor]: ...
