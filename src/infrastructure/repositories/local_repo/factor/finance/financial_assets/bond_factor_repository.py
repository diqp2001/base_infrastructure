"""
Repository class for Bond factor entities.
"""

from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class BondFactorRepository(BaseFactorRepository):
    """Repository for Bond factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)
    
    def get_factor_model(self):
        return FactorMapper().get_factor_model()
    
    def get_factor_entity(self):
        return FactorMapper().get_factor_entity()

    
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()
  