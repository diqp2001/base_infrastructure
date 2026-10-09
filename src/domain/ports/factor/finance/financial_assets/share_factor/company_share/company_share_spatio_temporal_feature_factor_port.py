from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import (
    CompanyShareSpatioTemporalFeatureFactor,
)


class CompanyShareSpatioTemporalFeatureFactorPort(ABC):
    """Port interface for CompanyShareSpatioTemporalFeatureFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareSpatioTemporalFeatureFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareSpatioTemporalFeatureFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareSpatioTemporalFeatureFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareSpatioTemporalFeatureFactor) -> Optional[CompanyShareSpatioTemporalFeatureFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareSpatioTemporalFeatureFactor) -> Optional[CompanyShareSpatioTemporalFeatureFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareSpatioTemporalFeatureFactor]: ...
