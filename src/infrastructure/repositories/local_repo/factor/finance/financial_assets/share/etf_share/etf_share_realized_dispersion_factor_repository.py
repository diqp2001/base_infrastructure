"""
Repository class for ETFShareRealizedDispersionFactor entities (calculated: the ETF option dispersion series, one factor row per
name - realized_call_dispersion_3m, ...). Same CRUD as ETFShareFactorRepository with the dispersion mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.share.etf_share.etf_share_realized_dispersion_factor_mapper import (
    ETFShareRealizedDispersionFactorMapper,
)
from .etf_share_factor_repository import ETFShareFactorRepository


class ETFShareRealizedDispersionFactorRepository(ETFShareFactorRepository):
    """Repository for ETFShareRealizedDispersionFactor entities."""

    FACTOR_TYPE = 'etf_share_realized_dispersion_factor'

    def _mapper(self):
        return ETFShareRealizedDispersionFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'realized', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
