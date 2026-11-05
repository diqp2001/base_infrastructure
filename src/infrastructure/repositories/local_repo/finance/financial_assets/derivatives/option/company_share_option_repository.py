"""
CompanyShareOption Repository for local database operations.
The logic common to options on a share lives in ShareOptionRepository.
"""

from typing import List

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption as DomainCompanyShareOption
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.company_share_option_mapper import CompanyShareOptionMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.share_option_repository import ShareOptionRepository


class CompanyShareOptionRepository(ShareOptionRepository):
    """Repository for company share option operations in the local database."""

    mapper_class = CompanyShareOptionMapper
    underlying_model = CompanyShareModel
    underlying_repository_key = 'CompanyShare'

    def get_by_company_share_id(self, company_share_id: int) -> List[DomainCompanyShareOption]:
        """Retrieve company share options by their underlying company share ID."""
        return self.get_by_underlying_id(company_share_id)
