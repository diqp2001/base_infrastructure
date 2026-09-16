from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
    CompanyShareOptionImpliedVolMlFactor,
)
from src.domain.ports.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor_port import (
    CompanyShareOptionImpliedVolMlFactorPort,
)


class IBKRCompanyShareOptionImpliedVolMlFactorRepository(CompanyShareOptionImpliedVolMlFactorPort):
    """IBKR repository for CompanyShareOptionImpliedVolMlFactor — delegates to local repo."""

    def __init__(self, ibkr_client=None, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = (
            factory._local_repositories.get("CompanyShareOptionImpliedVolMlFactor")
            if factory
            else None
        )

    @property
    def entity_class(self):
        return CompanyShareOptionImpliedVolMlFactor

    def _create_or_get(
        self, entity_cls, primary_key: str, **kwargs
    ) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        if self.local_repo:
            return self.local_repo._create_or_get(entity_cls, primary_key, **kwargs)
        return None

    def get_by_id(self, id: int) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CompanyShareOptionImpliedVolMlFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionImpliedVolMlFactor) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionImpliedVolMlFactor) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        return self.local_repo.delete(id) if self.local_repo else False
