# Cash Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/cash.py

class CashLocalRepository:
    """Local repository for cash model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, cash):
        """Save cash to local storage"""
        self.data_store.append(cash)
        
    def find_by_id(self, cash_id):
        """Find cash by ID"""
        for cash in self.data_store:
            if getattr(cash, 'id', None) == cash_id:
                return cash
        return None
        
    def find_all(self):
        """Find all cash"""
        return self.data_store.copy()