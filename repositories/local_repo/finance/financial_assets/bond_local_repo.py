# Bond Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/bond.py

class BondLocalRepository:
    """Local repository for bond model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, bond):
        """Save bond to local storage"""
        self.data_store.append(bond)
        
    def find_by_id(self, bond_id):
        """Find bond by ID"""
        for bond in self.data_store:
            if getattr(bond, 'id', None) == bond_id:
                return bond
        return None
        
    def find_all(self):
        """Find all bonds"""
        return self.data_store.copy()