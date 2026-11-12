"""
Repository class for CompanyShareFundamentalLeverageFactor entities (calculated: one factor row per measure name and frequency).
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.fundamental.company_share_fundamental_leverage_factor_mapper import (
    CompanyShareFundamentalLeverageFactorMapper,
)
from .company_share_fundamental_factor_repository import CompanyShareFundamentalFactorRepository


class CompanyShareFundamentalLeverageFactorRepository(CompanyShareFundamentalFactorRepository):
    """Repository for CompanyShareFundamentalLeverageFactor entities."""

    FACTOR_TYPE = 'company_share_fundamental_leverage_factor'

    def _mapper(self):
        return CompanyShareFundamentalLeverageFactorMapper()
