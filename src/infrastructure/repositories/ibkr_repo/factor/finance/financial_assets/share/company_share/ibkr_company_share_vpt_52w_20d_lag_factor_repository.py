from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor
from src.domain.ports.factor.company_share_vpt_52w_20d_lag_factor_port import CompanyShareVpt52w20dLagFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareVpt52w20dLagFactorRepository(BaseIBKRFactorRepository, CompanyShareVpt52w20dLagFactorPort):

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('company_share_vpt_52w_20d_lag_factor')
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
            print(f"Error in _create_or_get for vpt_52w_20d_lag factor {name}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareVpt52w20dLagFactor) -> Optional[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareVpt52w20dLagFactor) -> Optional[CompanyShareVpt52w20dLagFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        return self.local_repo.delete(factor_id) if self.local_repo else False
