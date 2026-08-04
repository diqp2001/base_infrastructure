from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_interest_rate_factor import BondInterestRateFactor


class BondInterestRateFactorPort(ABC):
    """Port interface for BondInterestRateFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondInterestRateFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondInterestRateFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondInterestRateFactor]: ...

    @abstractmethod
    def add(self, entity: BondInterestRateFactor) -> Optional[BondInterestRateFactor]: ...

    @abstractmethod
    def update(self, entity: BondInterestRateFactor) -> Optional[BondInterestRateFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondInterestRateFactor]: ...
