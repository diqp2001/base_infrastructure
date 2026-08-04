from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_gamma_factor import CallSpreadGammaFactor


class CallSpreadGammaFactorPort(ABC):
    """Port interface for CallSpreadGammaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadGammaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadGammaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadGammaFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadGammaFactor) -> Optional[CallSpreadGammaFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadGammaFactor) -> Optional[CallSpreadGammaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadGammaFactor]: ...
