# Balance Sheet Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/balance_sheet.py

from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from sqlalchemy.orm import Session

class BalanceSheetRepository(BaseLocalRepository):
    """Local repository for balance sheet model"""
    
    def __init__(self, session: Session):

        super().__init__(session)
        self.data_store = []
    
    def save(self, balance_sheet):
        """Save balance sheet to local storage"""
        self.data_store.append(balance_sheet)
        
    def find_by_id(self, balance_sheet_id):
        """Find balance sheet by ID"""
        for balance_sheet in self.data_store:
            if getattr(balance_sheet, 'id', None) == balance_sheet_id:
                return balance_sheet
        return None
        
    def find_all(self):
        """Find all balance sheets"""
        return self.data_store.copy()