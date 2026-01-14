# Commodity Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/commodity.py

from domain.ports.finance.financial_assets.commodity_port import CommodityPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from sqlalchemy.orm import Session

class CommodityRepository(FinancialAssetRepository, CommodityPort):
    """Local repository for commodity model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    def save(self, commodity):
        """Save commodity to local storage"""
        self.data_store.append(commodity)
        
    def find_by_id(self, commodity_id):
        """Find commodity by ID"""
        for commodity in self.data_store:
            if getattr(commodity, 'id', None) == commodity_id:
                return commodity
        return None
        
    def find_all(self):
        """Find all commodities"""
        return self.data_store.copy()