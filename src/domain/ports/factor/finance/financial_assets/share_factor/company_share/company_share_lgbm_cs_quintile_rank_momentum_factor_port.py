from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (
    CompanyShareLGBMCSQuintileRankMomentumFactor,
)


class CompanyShareLGBMCSQuintileRankMomentumFactorPort(ABC):
    """Port interface for CompanyShareLGBMCSQuintileRankMomentumFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareLGBMCSQuintileRankMomentumFactor) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareLGBMCSQuintileRankMomentumFactor) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]: ...
