"""
Repository class for Share factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from infrastructure.models.factor.finance.financial_assets.share_factors import (
    ShareFactor, ShareFactorValue
)


class ShareFactorRepository(BaseFactorRepository):
    """Repository for Share factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the ShareFactor model class."""
        return ShareFactor

    def get_factor_value_model(self):
        """Return the ShareFactorValue model class."""
        return ShareFactorValue

    