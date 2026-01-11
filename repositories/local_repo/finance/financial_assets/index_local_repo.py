# Index Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/index.py

class IndexLocalRepository:
    """Local repository for index model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, index):
        """Save index to local storage"""
        self.data_store.append(index)
        
    def find_by_id(self, index_id):
        """Find index by ID"""
        for index in self.data_store:
            if getattr(index, 'id', None) == index_id:
                return index
        return None
        
    def find_all(self):
        """Find all indices"""
        return self.data_store.copy()