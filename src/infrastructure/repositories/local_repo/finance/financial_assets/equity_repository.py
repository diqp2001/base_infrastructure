# Equity Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/equity.py

from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.domain.ports.finance.financial_assets.equity_port import EquityPort

class EquityRepository(FinancialAssetBaseRepository, EquityPort):
    """Local repository for equity model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, equity):
        """Save equity to local storage"""
        self.data_store.append(equity)
        
    def find_by_id(self, equity_id):
        """Find equity by ID"""
        for equity in self.data_store:
            if getattr(equity, 'id', None) == equity_id:
                return equity
        return None
        
    def find_all(self):
        """Find all equities"""
        return self.data_store.copy()