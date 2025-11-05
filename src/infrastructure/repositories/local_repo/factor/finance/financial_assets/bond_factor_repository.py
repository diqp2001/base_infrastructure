"""
Repository class for Bond factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from infrastructure.models.factor.finance.financial_assets.bond_factors import (
    BondFactor, BondFactorValue
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

  