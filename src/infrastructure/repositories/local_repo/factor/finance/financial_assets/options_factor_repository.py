"""
Repository class for Options factor entities.
"""

from .base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.options_factors import (
    OptionsFactor, OptionsFactorValue, OptionsFactorRule
)


class OptionsFactorRepository(BaseFactorRepository):
    """Repository for Options factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the OptionsFactor model class."""
        return OptionsFactor

    def get_factor_value_model(self):
        """Return the OptionsFactorValue model class."""
        return OptionsFactorValue

    def get_factor_rule_model(self):
        """Return the OptionsFactorRule model class."""
        return OptionsFactorRule