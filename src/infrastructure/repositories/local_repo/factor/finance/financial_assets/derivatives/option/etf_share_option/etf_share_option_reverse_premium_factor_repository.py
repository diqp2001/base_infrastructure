"""
Repository class for ETFShareOptionReversePremiumFactor entities (calculated: one factor row per name - reverse_premium_<measure>). Same CRUD as
ETFShareOptionFactorRepository with its own mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_reverse_premium_factor_mapper import (
    ETFShareOptionReversePremiumFactorMapper,
)
from .etf_share_option_factor_repository import ETFShareOptionFactorRepository


class ETFShareOptionReversePremiumFactorRepository(ETFShareOptionFactorRepository):
    """Repository for ETFShareOptionReversePremiumFactor entities."""

    FACTOR_TYPE = 'etf_share_option_reverse_premium_factor'

    def _mapper(self):
        return ETFShareOptionReversePremiumFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'reverse_premium', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
