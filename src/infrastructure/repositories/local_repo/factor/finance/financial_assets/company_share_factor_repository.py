"""
Repository class for Company Share factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.company_share_factors import (
    CompanyShareFactor, CompanyShareFactorValue, CompanyShareFactorRule
)


class CompanyShareFactorRepository(BaseFactorRepository):
    """Repository for Company Share factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the CompanyShareFactor model class."""
        return CompanyShareFactor

    def get_factor_value_model(self):
        """Return the CompanyShareFactorValue model class."""
        return CompanyShareFactorValue

    def get_factor_rule_model(self):
        """Return the CompanyShareFactorRule model class."""
        return CompanyShareFactorRule