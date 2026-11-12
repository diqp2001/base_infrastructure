"""
Repository class for CompanyShareFundamentalValuationFactor entities (calculated: one factor row per measure name and frequency).
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.fundamental.company_share_fundamental_valuation_factor_mapper import (
    CompanyShareFundamentalValuationFactorMapper,
)
from .company_share_fundamental_factor_repository import CompanyShareFundamentalFactorRepository


class CompanyShareFundamentalValuationFactorRepository(CompanyShareFundamentalFactorRepository):
    """Repository for CompanyShareFundamentalValuationFactor entities."""

    FACTOR_TYPE = 'company_share_fundamental_valuation_factor'

    def _mapper(self):
        return CompanyShareFundamentalValuationFactorMapper()
