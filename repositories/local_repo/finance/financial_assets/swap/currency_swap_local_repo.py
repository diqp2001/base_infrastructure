# Currency Swap Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/swap/currency_swap.py

class CurrencySwapLocalRepository:
    """Local repository for currency swap model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, currency_swap):
        """Save currency swap to local storage"""
        self.data_store.append(currency_swap)
        
    def find_by_id(self, currency_swap_id):
        """Find currency swap by ID"""
        for swap in self.data_store:
            if getattr(swap, 'id', None) == currency_swap_id:
                return swap
        return None
        
    def find_all(self):
        """Find all currency swaps"""
        return self.data_store.copy()