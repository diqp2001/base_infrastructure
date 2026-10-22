from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (
    CompanyShareCrossSectionalMomentumFactor,
)


class CompanyShareCrossSectionalMomentumFactorPort(ABC):
    """Port interface for CompanyShareCrossSectionalMomentumFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareCrossSectionalMomentumFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareCrossSectionalMomentumFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareCrossSectionalMomentumFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareCrossSectionalMomentumFactor) -> Optional[CompanyShareCrossSectionalMomentumFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareCrossSectionalMomentumFactor) -> Optional[CompanyShareCrossSectionalMomentumFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareCrossSectionalMomentumFactor]: ...
