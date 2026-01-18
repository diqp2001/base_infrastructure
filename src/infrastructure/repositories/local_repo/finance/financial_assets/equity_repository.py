# Equity Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/equity.py

from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.domain.ports.finance.financial_assets.equity_port import EquityPort
from src.infrastructure.models.finance.financial_assets.equity import EquityModel as EquityModel
from src.domain.entities.finance.financial_assets.equity import Equity as EquityEntity
from sqlalchemy.orm import Session
class EquityRepository(FinancialAssetRepository, EquityPort):
    """Local repository for equity model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Equity."""
        return EquityModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Equity."""
        return EquityEntity
    
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