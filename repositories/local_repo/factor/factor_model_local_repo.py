# Factor Model Local Repository
# Mirrors src/infrastructure/models/factor/factor_model.py

class FactorModelLocalRepository:
    """Local repository for factor model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, factor_model):
        """Save factor model to local storage"""
        self.data_store.append(factor_model)
        
    def find_by_id(self, factor_model_id):
        """Find factor model by ID"""
        for factor_model in self.data_store:
            if getattr(factor_model, 'id', None) == factor_model_id:
                return factor_model
        return None
        
    def find_all(self):
        """Find all factor models"""
        return self.data_store.copy()