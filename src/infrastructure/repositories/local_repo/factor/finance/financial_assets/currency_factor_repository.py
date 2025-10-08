"""
Repository class for Currency factor entities.
"""

from .base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.currency_factors import (
    CurrencyFactor, CurrencyFactorValue, CurrencyFactorRule
)


class CurrencyFactorRepository(BaseFactorRepository):
    """Repository for Currency factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the CurrencyFactor model class."""
        return CurrencyFactor

    def get_factor_value_model(self):
        """Return the CurrencyFactorValue model class."""
        return CurrencyFactorValue

    def get_factor_rule_model(self):
        """Return the CurrencyFactorRule model class."""
        return CurrencyFactorRule