"""
Repository class for Bond factor entities.
"""

from .base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.bond_factors import (
    BondFactor, BondFactorValue, BondFactorRule
)


class BondFactorRepository(BaseFactorRepository):
    """Repository for Bond factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the BondFactor model class."""
        return BondFactor

    def get_factor_value_model(self):
        """Return the BondFactorValue model class."""
        return BondFactorValue

    def get_factor_rule_model(self):
        """Return the BondFactorRule model class."""
        return BondFactorRule