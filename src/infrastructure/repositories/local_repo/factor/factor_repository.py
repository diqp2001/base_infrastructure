# Factor Local Repository
# Mirrors src/infrastructure/models/factor/factor.py

class FactorRepository:
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