"""
Repository class for Equity factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from infrastructure.models.factor.finance.financial_assets.equity_factors import (
    EquityFactor, EquityFactorValue, 
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

