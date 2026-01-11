# Holding Local Repository
# Mirrors src/infrastructure/models/finance/holding/holding.py

class HoldingLocalRepository:
    """Local repository for holding model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, holding):
        """Save holding to local storage"""
        self.data_store.append(holding)
        
    def find_by_id(self, holding_id):
        """Find holding by ID"""
        for holding in self.data_store:
            if getattr(holding, 'id', None) == holding_id:
                return holding
        return None
        
    def find_all(self):
        """Find all holdings"""
        return self.data_store.copy()