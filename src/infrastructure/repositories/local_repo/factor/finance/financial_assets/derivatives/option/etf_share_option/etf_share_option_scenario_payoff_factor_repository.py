"""
Repository class for ETFShareOptionScenarioPayoffFactor entities (calculated: one factor row per name - scenario_<measure>). Same CRUD as
ETFShareOptionFactorRepository with its own mapper.
"""
from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor_mapper import (
    ETFShareOptionScenarioPayoffFactorMapper,
)
from .etf_share_option_factor_repository import ETFShareOptionFactorRepository


class ETFShareOptionScenarioPayoffFactorRepository(ETFShareOptionFactorRepository):
    """Repository for ETFShareOptionScenarioPayoffFactor entities."""

    FACTOR_TYPE = 'etf_share_option_scenario_payoff_factor'

    def _mapper(self):
        return ETFShareOptionScenarioPayoffFactorMapper()

    def _defaults(self, primary_key: str, kwargs: dict) -> dict:
        return {'group': 'dispersion', 'subgroup': 'scenario', 'frequency': '1d', 'data_type': 'numeric',
                'source': 'calculated'}
