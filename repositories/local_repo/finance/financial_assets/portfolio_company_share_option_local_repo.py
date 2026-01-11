# Portfolio Company Share Option Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/portfolio_company_share_option.py

class PortfolioCompanyShareOptionLocalRepository:
    """Local repository for portfolio company share option model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, portfolio_company_share_option):
        """Save portfolio company share option to local storage"""
        self.data_store.append(portfolio_company_share_option)
        
    def find_by_id(self, portfolio_company_share_option_id):
        """Find portfolio company share option by ID"""
        for option in self.data_store:
            if getattr(option, 'id', None) == portfolio_company_share_option_id:
                return option
        return None
        
    def find_all(self):
        """Find all portfolio company share options"""
        return self.data_store.copy()