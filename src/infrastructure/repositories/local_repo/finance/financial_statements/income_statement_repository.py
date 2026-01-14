# Income Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/income_statement.py
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
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