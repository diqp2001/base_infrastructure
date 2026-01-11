# Portfolio Local Repository
# Mirrors src/infrastructure/models/finance/portfolio.py

class PortfolioLocalRepository:
    """Local repository for portfolio model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, portfolio):
        """Save portfolio to local storage"""
        self.data_store.append(portfolio)
        
    def find_by_id(self, portfolio_id):
        """Find portfolio by ID"""
        for portfolio in self.data_store:
            if getattr(portfolio, 'id', None) == portfolio_id:
                return portfolio
        return None
        
    def find_all(self):
        """Find all portfolios"""
        return self.data_store.copy()