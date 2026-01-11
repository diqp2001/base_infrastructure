# Security Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/security.py

class SecurityRepository:
    """Local repository for security model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, security):
        """Save security to local storage"""
        self.data_store.append(security)
        
    def find_by_id(self, security_id):
        """Find security by ID"""
        for security in self.data_store:
            if getattr(security, 'id', None) == security_id:
                return security
        return None
        
    def find_all(self):
        """Find all securities"""
        return self.data_store.copy()