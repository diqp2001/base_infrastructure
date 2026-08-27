"""
IBKR Company Share Option Factor Repository - Retrieval and creation of company share option factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.ports.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor_port import CompanyShareOptionFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareOptionFactorRepository(BaseIBKRFactorRepository, CompanyShareOptionFactorPort):
    """
    IBKR implementation for CompanyShareOption factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Company Share Option Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('CompanyShareOptionFactor')

    @property
    def entity_class(self):
        return CompanyShareOptionFactor
    

    def _create_or_get(self, name: str, **kwargs):
        try:
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(
                    self.local_repo.get_factor_entity(), primary_key=name, **kwargs
                )
                if created_factor:
                    return created_factor

            print(f"Failed to create company share option factor: {name}")
            return None

        except Exception as e:
            print(f"Error in get_or_create for company share option factor {name}: {e}")
            return None

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[CompanyShareOptionFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False

    def get_by_group(self, group: str):
        if self.local_repo and hasattr(self.local_repo, 'get_by_group'):
            return self.local_repo.get_by_group(group)
        return []
