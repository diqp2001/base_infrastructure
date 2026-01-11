# ETF Share Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/etf_share.py

class ETFShareLocalRepository:
    """Local repository for ETF share model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, etf_share):
        """Save ETF share to local storage"""
        self.data_store.append(etf_share)
        
    def find_by_id(self, etf_share_id):
        """Find ETF share by ID"""
        for etf_share in self.data_store:
            if getattr(etf_share, 'id', None) == etf_share_id:
                return etf_share
        return None
        
    def find_all(self):
        """Find all ETF shares"""
        return self.data_store.copy()