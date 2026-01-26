# Balance Sheet Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/balance_sheet.py

from typing import Optional
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
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

    def get_or_create(self, company_id: int, period_date: Optional[str] = None, **kwargs) -> Optional[dict]:
        """
        Get or create a balance sheet with dependency resolution.
        
        Args:
            company_id: Company ID (primary identifier)
            period_date: Financial period date (optional)
            **kwargs: Additional fields for the balance sheet
            
        Returns:
            Balance sheet or None if creation failed
        """
        try:
            from datetime import datetime
            
            # Set default period date
            period_date = period_date or datetime.now().strftime('%Y-%m-%d')
            
            # First try to find existing balance sheet
            for sheet in self.data_store:
                if (getattr(sheet, 'company_id', None) == company_id and 
                    getattr(sheet, 'period_date', None) == period_date):
                    return sheet
            
            # Create new balance sheet
            balance_sheet_data = {
                'company_id': company_id,
                'period_date': period_date,
                'created_at': datetime.now(),
                **kwargs
            }
            
            # Save to data store
            self.save(balance_sheet_data)
            
            return balance_sheet_data
            
        except Exception as e:
            print(f"Error in get_or_create for balance sheet (company_id: {company_id}): {e}")
            return None