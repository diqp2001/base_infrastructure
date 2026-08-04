from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor


class DerivativeFactorPort(ABC):
    """Port interface for DerivativeFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[DerivativeFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[DerivativeFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[DerivativeFactor]: ...

    @abstractmethod
    def get_all(self) -> List[DerivativeFactor]: ...

    @abstractmethod
    def add(self, entity: DerivativeFactor) -> Optional[DerivativeFactor]: ...

    @abstractmethod
    def update(self, entity: DerivativeFactor) -> Optional[DerivativeFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[DerivativeFactor]: ...
