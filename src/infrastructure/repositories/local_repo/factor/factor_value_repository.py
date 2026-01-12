# Factor Value Local Repository
# Mirrors src/infrastructure/models/factor/factor_value.py

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class FactorValueRepository(BaseLocalRepository,FactorValuePort):
    """Local repository for factor value model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, factor_value):
        """Save factor value to local storage"""
        self.data_store.append(factor_value)
        
    def find_by_id(self, factor_value_id):
        """Find factor value by ID"""
        for factor_value in self.data_store:
            if getattr(factor_value, 'id', None) == factor_value_id:
                return factor_value
        return None
        
    def find_all(self):
        """Find all factor values"""
        return self.data_store.copy()