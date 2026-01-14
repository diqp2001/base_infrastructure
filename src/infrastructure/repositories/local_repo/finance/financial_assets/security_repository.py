# Security Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/security.py

from domain.ports.finance.financial_assets.security_port import SecurityPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository


class SecurityRepository(FinancialAssetRepository, SecurityPort):
    """Local repository for security model"""
    
    def __init__(self, session):
        super().__init__(session)
        self.data_store = []
        
    
    def save(self, security):
        """Save security to local storage"""
        self.data_store.append(security)
        
    def find_by_id(self, security_id):
        """Find security by ID"""
        for security in self.data_store:
            if getattr(security, 'id', None) == security_id:
                return security
        return None
        
    def find_all(self):
        """Find all securities"""
        return self.data_store.copy()