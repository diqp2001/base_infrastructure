"""
Repository class for Equity factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.equity_factors import (
    EquityFactor, EquityFactorValue, EquityFactorRule
)


class EquityFactorRepository(BaseFactorRepository):
    """Repository for Equity factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the EquityFactor model class."""
        return EquityFactor

    def get_factor_value_model(self):
        """Return the EquityFactorValue model class."""
        return EquityFactorValue

    def get_factor_rule_model(self):
        """Return the EquityFactorRule model class."""
        return EquityFactorRule