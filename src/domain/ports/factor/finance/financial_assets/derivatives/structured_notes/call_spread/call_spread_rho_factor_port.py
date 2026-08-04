from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_rho_factor import CallSpreadRhoFactor


class CallSpreadRhoFactorPort(ABC):
    """Port interface for CallSpreadRhoFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadRhoFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadRhoFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadRhoFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadRhoFactor) -> Optional[CallSpreadRhoFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadRhoFactor) -> Optional[CallSpreadRhoFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadRhoFactor]: ...
