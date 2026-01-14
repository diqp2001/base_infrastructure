# Cash Flow Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/cash_flow_statement.py
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from sqlalchemy.orm import Session
class CashFlowStatementRepository(BaseLocalRepository):
    
    def __init__(self, session: Session):

        super().__init__(session)
        self.data_store = []
    
    def save(self, cash_flow_statement):
        """Save cash flow statement to local storage"""
        self.data_store.append(cash_flow_statement)
        
    def find_by_id(self, cash_flow_statement_id):
        """Find cash flow statement by ID"""
        for statement in self.data_store:
            if getattr(statement, 'id', None) == cash_flow_statement_id:
                return statement
        return None
        
    def find_all(self):
        """Find all cash flow statements"""
        return self.data_store.copy()