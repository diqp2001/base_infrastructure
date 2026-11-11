"""
Repository class for ETFShareOptionNetPremiumFactor entities (calculated: one factor row per name - premium_<measure>). Same CRUD as
ETFShareOptionFactorRepository with its own mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_net_premium_factor_mapper import (
    ETFShareOptionNetPremiumFactorMapper,
)
from .etf_share_option_factor_repository import ETFShareOptionFactorRepository


class ETFShareOptionNetPremiumFactorRepository(ETFShareOptionFactorRepository):
    """Repository for ETFShareOptionNetPremiumFactor entities."""

    FACTOR_TYPE = 'etf_share_option_net_premium_factor'

    def _mapper(self):
        return ETFShareOptionNetPremiumFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'premium', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
