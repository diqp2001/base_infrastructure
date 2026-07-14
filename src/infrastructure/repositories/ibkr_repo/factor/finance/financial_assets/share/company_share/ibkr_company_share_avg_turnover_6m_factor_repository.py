from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import CompanyShareAvgTurnover6mFactor
from src.domain.ports.factor.company_share_avg_turnover_6m_factor_port import CompanyShareAvgTurnover6mFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareAvgTurnover6mFactorRepository(BaseIBKRFactorRepository, CompanyShareAvgTurnover6mFactorPort):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('company_share_avg_turnover_6m_factor')
        return None

    @property
    def entity_class(self):
        return self.mapper.get_factor_entity()

    @property
    def model_class(self):
        return self.local_repo.get_factor_model()

    def _create_or_get(self, name: str, **kwargs):
        try:
            if self.local_repo:
                return self.local_repo._create_or_get(
                    self.local_repo.get_factor_entity(), primary_key=name, **kwargs
                )
            return None
        except Exception as e:
            print(f"Error in _create_or_get for avg_turnover_6m factor {name}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareAvgTurnover6mFactor) -> Optional[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareAvgTurnover6mFactor) -> Optional[CompanyShareAvgTurnover6mFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        return self.local_repo.delete(factor_id) if self.local_repo else False
