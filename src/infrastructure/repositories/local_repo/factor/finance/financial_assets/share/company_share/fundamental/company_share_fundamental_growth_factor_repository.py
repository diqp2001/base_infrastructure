"""
Repository class for CompanyShareFundamentalGrowthFactor entities (calculated: one factor row per measure name and frequency).
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.fundamental.company_share_fundamental_growth_factor_mapper import (
    CompanyShareFundamentalGrowthFactorMapper,
)
from .company_share_fundamental_factor_repository import CompanyShareFundamentalFactorRepository


class CompanyShareFundamentalGrowthFactorRepository(CompanyShareFundamentalFactorRepository):
    """Repository for CompanyShareFundamentalGrowthFactor entities."""

    FACTOR_TYPE = 'company_share_fundamental_growth_factor'

    def _mapper(self):
        return CompanyShareFundamentalGrowthFactorMapper()
