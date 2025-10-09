"""
Repository class for Security factor entities.
"""

from ...base_factor_repository import BaseFactorRepository
from src.infrastructure.models.finance.financial_assets.security_factors import (
    SecurityFactor, SecurityFactorValue, SecurityFactorRule
)


class SecurityFactorRepository(BaseFactorRepository):
    """Repository for Security factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    def get_factor_model(self):
        """Return the SecurityFactor model class."""
        return SecurityFactor

    def get_factor_value_model(self):
        """Return the SecurityFactorValue model class."""
        return SecurityFactorValue

    def get_factor_rule_model(self):
        """Return the SecurityFactorRule model class."""
        return SecurityFactorRule