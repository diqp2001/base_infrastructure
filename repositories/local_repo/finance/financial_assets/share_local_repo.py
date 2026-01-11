# Share Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/share.py

class ShareLocalRepository:
    """Local repository for share model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, share):
        """Save share to local storage"""
        self.data_store.append(share)
        
    def find_by_id(self, share_id):
        """Find share by ID"""
        for share in self.data_store:
            if getattr(share, 'id', None) == share_id:
                return share
        return None
        
    def find_all(self):
        """Find all shares"""
        return self.data_store.copy()