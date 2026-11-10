"""
Repository class for ETFShareImpliedDispersionFactor entities (calculated: the ETF option dispersion series, one factor row per
name - implied_call_dispersion_3m, ...). Same CRUD as ETFShareFactorRepository with the dispersion mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.etf_share.etf_share_implied_dispersion_factor_mapper import (
    ETFShareImpliedDispersionFactorMapper,
)
from .etf_share_factor_repository import ETFShareFactorRepository


class ETFShareImpliedDispersionFactorRepository(ETFShareFactorRepository):
    """Repository for ETFShareImpliedDispersionFactor entities."""

    FACTOR_TYPE = 'etf_share_implied_dispersion_factor'

    def _mapper(self):
        return ETFShareImpliedDispersionFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'implied', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
