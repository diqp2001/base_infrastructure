"""
Repository class for Commodity factor entities.
"""

from .base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.commodity_factors import (
    CommodityFactor, CommodityFactorValue, CommodityFactorRule
)


class CommodityFactorRepository(BaseFactorRepository):
    """Repository for Commodity factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the CommodityFactor model class."""
        return CommodityFactor

    def get_factor_value_model(self):
        """Return the CommodityFactorValue model class."""
        return CommodityFactorValue

    def get_factor_rule_model(self):
        """Return the CommodityFactorRule model class."""
        return CommodityFactorRule