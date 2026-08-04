from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_vega_factor import CallSpreadVegaFactor


class CallSpreadVegaFactorPort(ABC):
    """Port interface for CallSpreadVegaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadVegaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadVegaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadVegaFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadVegaFactor) -> Optional[CallSpreadVegaFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadVegaFactor) -> Optional[CallSpreadVegaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadVegaFactor]: ...
