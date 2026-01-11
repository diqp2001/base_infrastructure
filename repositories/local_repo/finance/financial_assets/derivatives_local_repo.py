# Derivatives Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/derivatives.py

class DerivativesLocalRepository:
    """Local repository for derivatives model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, derivative):
        """Save derivative to local storage"""
        self.data_store.append(derivative)
        
    def find_by_id(self, derivative_id):
        """Find derivative by ID"""
        for derivative in self.data_store:
            if getattr(derivative, 'id', None) == derivative_id:
                return derivative
        return None
        
    def find_all(self):
        """Find all derivatives"""
        return self.data_store.copy()