# Derivatives Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/derivatives.py
from sqlalchemy.orm import Session

from domain.ports.finance.financial_assets.derivatives.derivative_port import DerivativePort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
class DerivativesRepository(FinancialAssetRepository, DerivativePort):
    """Local repository for derivatives model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    def save(self, derivative):
        """Save derivative to local storage"""
        self.data_store.append(derivative)
        
    def find_by_id(self, derivative_id):
        """Find derivative by ID"""
        for derivative in self.data_store:
            if getattr(derivative, 'id', None) == derivative_id:
                return derivative
        return None
        
    def find_all(self):
        """Find all derivatives"""
        return self.data_store.copy()