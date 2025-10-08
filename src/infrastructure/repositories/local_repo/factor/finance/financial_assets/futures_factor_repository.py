"""
Repository class for Futures factor entities.
"""

from .base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.futures_factors import (
    FuturesFactor, FuturesFactorValue, FuturesFactorRule
)


class FuturesFactorRepository(BaseFactorRepository):
    """Repository for Futures factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the FuturesFactor model class."""
        return FuturesFactor

    def get_factor_value_model(self):
        """Return the FuturesFactorValue model class."""
        return FuturesFactorValue

    def get_factor_rule_model(self):
        """Return the FuturesFactorRule model class."""
        return FuturesFactorRule