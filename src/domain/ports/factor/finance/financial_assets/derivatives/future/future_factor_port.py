from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class FutureFactorPort(ABC):
    """Port interface for FutureFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FutureFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FutureFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[FutureFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FutureFactor]: ...

    @abstractmethod
    def add(self, entity: FutureFactor) -> Optional[FutureFactor]: ...

    @abstractmethod
    def update(self, entity: FutureFactor) -> Optional[FutureFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FutureFactor]: ...
