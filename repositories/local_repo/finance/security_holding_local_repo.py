# Security Holding Local Repository
# Mirrors src/infrastructure/models/finance/security_holding.py

class SecurityHoldingLocalRepository:
    """Local repository for security holding model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, security_holding):
        """Save security holding to local storage"""
        self.data_store.append(security_holding)
        
    def find_by_id(self, security_holding_id):
        """Find security holding by ID"""
        for holding in self.data_store:
            if getattr(holding, 'id', None) == security_holding_id:
                return holding
        return None
        
    def find_all(self):
        """Find all security holdings"""
        return self.data_store.copy()