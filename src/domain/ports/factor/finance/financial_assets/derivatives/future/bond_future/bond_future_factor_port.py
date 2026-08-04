from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor


class BondFutureFactorPort(ABC):
    """Port interface for BondFutureFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFutureFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFutureFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFutureFactor]: ...

    @abstractmethod
    def add(self, entity: BondFutureFactor) -> Optional[BondFutureFactor]: ...

    @abstractmethod
    def update(self, entity: BondFutureFactor) -> Optional[BondFutureFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFutureFactor]: ...
