"""
Repository class for Index factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from infrastructure.models.factor.finance.financial_assets.index_factors import (
    IndexFactor, IndexFactorValue
)


class IndexFactorRepository(BaseFactorRepository):
    """Repository for Index factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the IndexFactor model class."""
        return IndexFactor

    def get_factor_value_model(self):
        """Return the IndexFactorValue model class."""
        return IndexFactorValue

