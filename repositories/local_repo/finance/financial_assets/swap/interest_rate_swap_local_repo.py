# Interest Rate Swap Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/swap/interest_rate_swap.py

class InterestRateSwapLocalRepository:
    """Local repository for interest rate swap model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, interest_rate_swap):
        """Save interest rate swap to local storage"""
        self.data_store.append(interest_rate_swap)
        
    def find_by_id(self, interest_rate_swap_id):
        """Find interest rate swap by ID"""
        for swap in self.data_store:
            if getattr(swap, 'id', None) == interest_rate_swap_id:
                return swap
        return None
        
    def find_all(self):
        """Find all interest rate swaps"""
        return self.data_store.copy()