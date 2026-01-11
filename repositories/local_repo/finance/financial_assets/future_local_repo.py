# Future Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/future.py

class FutureLocalRepository:
    """Local repository for future model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, future):
        """Save future to local storage"""
        self.data_store.append(future)
        
    def find_by_id(self, future_id):
        """Find future by ID"""
        for future in self.data_store:
            if getattr(future, 'id', None) == future_id:
                return future
        return None
        
    def find_all(self):
        """Find all futures"""
        return self.data_store.copy()