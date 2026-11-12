"""
Repository class for CompanyShareFundamentalProfitabilityFactor entities (calculated: one factor row per measure name and frequency).
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.fundamental.company_share_fundamental_profitability_factor_mapper import (
    CompanyShareFundamentalProfitabilityFactorMapper,
)
from .company_share_fundamental_factor_repository import CompanyShareFundamentalFactorRepository


class CompanyShareFundamentalProfitabilityFactorRepository(CompanyShareFundamentalFactorRepository):
    """Repository for CompanyShareFundamentalProfitabilityFactor entities."""

    FACTOR_TYPE = 'company_share_fundamental_profitability_factor'

    def _mapper(self):
        return CompanyShareFundamentalProfitabilityFactorMapper()
