# Cash Flow Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/cash_flow_statement.py
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from sqlalchemy.orm import Session
from typing import Optional
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

    def get_or_create(self, primary_key: str, **kwargs) -> Optional:
        """
        Get or create a cash flow statement with dependency resolution.
        
        Args:
            primary_key: Company ID and period identifier
            **kwargs: Additional parameters for statement creation
            
        Returns:
            Cash flow statement entity or None if creation failed
        """
        try:
            # Check existing by primary identifier
            existing = self.find_by_id(primary_key)
            if existing:
                return existing
            
            # Create new cash flow statement with defaults
            from src.domain.entities.finance.financial_statements.cash_flow_statement import CashFlowStatement
            
            new_statement = CashFlowStatement(
                id=primary_key,
                company_id=kwargs.get('company_id', 1),
                period=kwargs.get('period', 'Q4'),
                year=kwargs.get('year', 2024),
                currency=kwargs.get('currency', 'USD'),
                operating_cash_flow=kwargs.get('operating_cash_flow', 0.0),
                investing_cash_flow=kwargs.get('investing_cash_flow', 0.0),
                financing_cash_flow=kwargs.get('financing_cash_flow', 0.0),
                net_cash_flow=kwargs.get('net_cash_flow', 0.0),
                free_cash_flow=kwargs.get('free_cash_flow', 0.0)
            )
            
            # Add to data store
            self.save(new_statement)
            return new_statement
            
        except Exception as e:
            print(f"Error in get_or_create for cash flow statement {primary_key}: {e}")
            return None