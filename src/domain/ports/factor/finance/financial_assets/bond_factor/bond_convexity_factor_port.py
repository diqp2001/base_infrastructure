from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_convexity_factor import BondConvexityFactor


class BondConvexityFactorPort(ABC):
    """Port interface for BondConvexityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondConvexityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondConvexityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondConvexityFactor]: ...

    @abstractmethod
    def add(self, entity: BondConvexityFactor) -> Optional[BondConvexityFactor]: ...

    @abstractmethod
    def update(self, entity: BondConvexityFactor) -> Optional[BondConvexityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondConvexityFactor]: ...
