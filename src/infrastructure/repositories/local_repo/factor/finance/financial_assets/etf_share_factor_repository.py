"""
Repository class for ETF Share factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from infrastructure.models.factor.finance.financial_assets.etf_share_factors import (
    ETFShareFactor, ETFShareFactorValue
)


class ETFShareFactorRepository(BaseFactorRepository):
    """Repository for ETF Share factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the ETFShareFactor model class."""
        return ETFShareFactor

    def get_factor_value_model(self):
        """Return the ETFShareFactorValue model class."""
        return ETFShareFactorValue

