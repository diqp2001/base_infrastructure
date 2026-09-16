from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (
    CompanyShareLGBMCSQuintileRankMomentumFactor,
)
from src.domain.ports.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor_port import (
    CompanyShareLGBMCSQuintileRankMomentumFactorPort,
)
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareLGBMCSQuintileRankMomentumFactorRepository(
    BaseIBKRFactorRepository,
    CompanyShareLGBMCSQuintileRankMomentumFactorPort,
):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('CompanyShareLGBMCSQuintileRankMomentumFactor')
        return None

    @property
    def entity_class(self):
        return CompanyShareLGBMCSQuintileRankMomentumFactor

    @property
    def model_class(self):
        return self.local_repo.get_factor_model() if self.local_repo else None

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        try:
            if self.local_repo:
                return self.local_repo._create_or_get(
                    self.local_repo.get_factor_entity(), primary_key=primary_key, **kwargs
                )
            return None
        except Exception as e:
            print(f"Error in _create_or_get for LGBM CS quintile momentum factor '{primary_key}': {e}")
            return None

    def get_by_id(self, id: int) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareLGBMCSQuintileRankMomentumFactor) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareLGBMCSQuintileRankMomentumFactor) -> Optional[CompanyShareLGBMCSQuintileRankMomentumFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False
