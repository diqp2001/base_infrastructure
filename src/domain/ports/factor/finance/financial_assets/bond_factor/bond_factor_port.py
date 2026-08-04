from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor


class BondFactorPort(ABC):
    """Port interface for BondFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[BondFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFactor]: ...

    @abstractmethod
    def add(self, entity: BondFactor) -> Optional[BondFactor]: ...

    @abstractmethod
    def update(self, entity: BondFactor) -> Optional[BondFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFactor]: ...
