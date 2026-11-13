"""
Repository class for CompanyShareFundamentalStatementItemFactor entities (calculated: one factor row per measure name and frequency).
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.company_share.fundamental.company_share_fundamental_statement_item_factor_mapper import (
    CompanyShareFundamentalStatementItemFactorMapper,
)
from .company_share_fundamental_factor_repository import CompanyShareFundamentalFactorRepository


class CompanyShareFundamentalStatementItemFactorRepository(CompanyShareFundamentalFactorRepository):
    """Repository for CompanyShareFundamentalStatementItemFactor entities."""

    FACTOR_TYPE = 'company_share_fundamental_statement_item_factor'

    def _mapper(self):
        return CompanyShareFundamentalStatementItemFactorMapper()
