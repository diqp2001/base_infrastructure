# Income Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/income_statement.py
from typing import Optional
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from sqlalchemy.orm import Session
class IncomeStatementRepository(BaseLocalRepository):
    
    def __init__(self, session: Session):

        super().__init__(session)
        self.data_store = []
    
    def save(self, income_statement):
        """Save income statement to local storage"""
        self.data_store.append(income_statement)
        
    def find_by_id(self, income_statement_id):
        """Find income statement by ID"""
        for statement in self.data_store:
            if getattr(statement, 'id', None) == income_statement_id:
                return statement
        return None
        
    def find_all(self):
        """Find all income statements"""
        return self.data_store.copy()

    def get_or_create(self, company_id: int, period_date: Optional[str] = None, **kwargs) -> Optional[dict]:
        """
        Get or create an income statement with dependency resolution.
        
        Args:
            company_id: Company ID (primary identifier)
            period_date: Financial period date (optional)
            **kwargs: Additional fields for the income statement
            
        Returns:
            Income statement or None if creation failed
        """
        try:
            from datetime import datetime
            
            # Set default period date
            period_date = period_date or datetime.now().strftime('%Y-%m-%d')
            
            # First try to find existing income statement
            for statement in self.data_store:
                if (getattr(statement, 'company_id', None) == company_id and 
                    getattr(statement, 'period_date', None) == period_date):
                    return statement
            
            # Create new income statement
            statement_data = {
                'company_id': company_id,
                'period_date': period_date,
                'created_at': datetime.now(),
                **kwargs
            }
            
            # Save to data store
            self.save(statement_data)
            
            return statement_data
            
        except Exception as e:
            print(f"Error in get_or_create for income statement (company_id: {company_id}): {e}")
            return None