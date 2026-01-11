# Portfolio Holding Local Repository
# Mirrors src/infrastructure/models/finance/holding/portfolio_holding.py

class PortfolioHoldingLocalRepository:
    """Local repository for portfolio holding model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, portfolio_holding):
        """Save portfolio holding to local storage"""
        self.data_store.append(portfolio_holding)
        
    def find_by_id(self, portfolio_holding_id):
        """Find portfolio holding by ID"""
        for holding in self.data_store:
            if getattr(holding, 'id', None) == portfolio_holding_id:
                return holding
        return None
        
    def find_all(self):
        """Find all portfolio holdings"""
        return self.data_store.copy()