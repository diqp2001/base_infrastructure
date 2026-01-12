# Factor Local Repository
# Mirrors src/infrastructure/models/factor/factor.py

from src.domain.ports.factor.factor_port import FactorPort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class FactorRepository(BaseLocalRepository,FactorPort):
    """Local repository for factor model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, factor):
        """Save factor to local storage"""
        self.data_store.append(factor)
        
    def find_by_id(self, factor_id):
        """Find factor by ID"""
        for factor in self.data_store:
            if getattr(factor, 'id', None) == factor_id:
                return factor
        return None
        
    def find_all(self):
        """Find all factors"""
        return self.data_store.copy()