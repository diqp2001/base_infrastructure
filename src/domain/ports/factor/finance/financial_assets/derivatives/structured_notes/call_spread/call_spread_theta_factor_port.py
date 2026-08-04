from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.call_spread.call_spread_theta_factor import CallSpreadThetaFactor


class CallSpreadThetaFactorPort(ABC):
    """Port interface for CallSpreadThetaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CallSpreadThetaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CallSpreadThetaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CallSpreadThetaFactor]: ...

    @abstractmethod
    def add(self, entity: CallSpreadThetaFactor) -> Optional[CallSpreadThetaFactor]: ...

    @abstractmethod
    def update(self, entity: CallSpreadThetaFactor) -> Optional[CallSpreadThetaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CallSpreadThetaFactor]: ...
