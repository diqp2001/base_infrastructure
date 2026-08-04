from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_price_factor import BondPriceFactor


class BondPriceFactorPort(ABC):
    """Port interface for BondPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondPriceFactor]: ...

    @abstractmethod
    def add(self, entity: BondPriceFactor) -> Optional[BondPriceFactor]: ...

    @abstractmethod
    def update(self, entity: BondPriceFactor) -> Optional[BondPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondPriceFactor]: ...
