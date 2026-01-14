# Swap Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/swap/swap.py
from sqlalchemy.orm import Session

from domain.ports.finance.financial_assets.derivatives.swap_port import SwapPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
class SwapRepository(FinancialAssetRepository, SwapPort):
    """Local repository for swap model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    def save(self, swap):
        """Save swap to local storage"""
        self.data_store.append(swap)
        
    def find_by_id(self, swap_id):
        """Find swap by ID"""
        for swap in self.data_store:
            if getattr(swap, 'id', None) == swap_id:
                return swap
        return None
        
    def find_all(self):
        """Find all swaps"""
        return self.data_store.copy()