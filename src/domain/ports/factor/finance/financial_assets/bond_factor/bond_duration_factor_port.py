from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_duration_factor import BondDurationFactor


class BondDurationFactorPort(ABC):
    """Port interface for BondDurationFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondDurationFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondDurationFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondDurationFactor]: ...

    @abstractmethod
    def add(self, entity: BondDurationFactor) -> Optional[BondDurationFactor]: ...

    @abstractmethod
    def update(self, entity: BondDurationFactor) -> Optional[BondDurationFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondDurationFactor]: ...
