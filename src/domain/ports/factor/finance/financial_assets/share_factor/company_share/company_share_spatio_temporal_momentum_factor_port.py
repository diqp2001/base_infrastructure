from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import (
    CompanyShareSpatioTemporalMomentumFactor,
)


class CompanyShareSpatioTemporalMomentumFactorPort(ABC):
    """Port interface for CompanyShareSpatioTemporalMomentumFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareSpatioTemporalMomentumFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareSpatioTemporalMomentumFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareSpatioTemporalMomentumFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareSpatioTemporalMomentumFactor) -> Optional[CompanyShareSpatioTemporalMomentumFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareSpatioTemporalMomentumFactor) -> Optional[CompanyShareSpatioTemporalMomentumFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareSpatioTemporalMomentumFactor]: ...
