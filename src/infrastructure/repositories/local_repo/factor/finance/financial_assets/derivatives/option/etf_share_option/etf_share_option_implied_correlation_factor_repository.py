"""
Repository class for ETFShareOptionImpliedCorrelationFactor entities (calculated: one factor row per name - implied_correlation_<measure>). Same CRUD as
ETFShareOptionFactorRepository with its own mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_implied_correlation_factor_mapper import (
    ETFShareOptionImpliedCorrelationFactorMapper,
)
from .etf_share_option_factor_repository import ETFShareOptionFactorRepository


class ETFShareOptionImpliedCorrelationFactorRepository(ETFShareOptionFactorRepository):
    """Repository for ETFShareOptionImpliedCorrelationFactor entities."""

    FACTOR_TYPE = 'etf_share_option_implied_correlation_factor'

    def _mapper(self):
        return ETFShareOptionImpliedCorrelationFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'implied_correlation', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
