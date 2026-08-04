from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_spread_factor import BondSpreadFactor


class BondSpreadFactorPort(ABC):
    """Port interface for BondSpreadFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondSpreadFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondSpreadFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondSpreadFactor]: ...

    @abstractmethod
    def add(self, entity: BondSpreadFactor) -> Optional[BondSpreadFactor]: ...

    @abstractmethod
    def update(self, entity: BondSpreadFactor) -> Optional[BondSpreadFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondSpreadFactor]: ...
