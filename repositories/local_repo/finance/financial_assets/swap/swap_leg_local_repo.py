# Swap Leg Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/swap/swap_leg.py

class SwapLegLocalRepository:
    """Local repository for swap leg model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, swap_leg):
        """Save swap leg to local storage"""
        self.data_store.append(swap_leg)
        
    def find_by_id(self, swap_leg_id):
        """Find swap leg by ID"""
        for swap_leg in self.data_store:
            if getattr(swap_leg, 'id', None) == swap_leg_id:
                return swap_leg
        return None
        
    def find_all(self):
        """Find all swap legs"""
        return self.data_store.copy()