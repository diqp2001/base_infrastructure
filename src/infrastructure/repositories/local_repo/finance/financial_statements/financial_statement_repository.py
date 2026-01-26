# Financial Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/financial_statement.py
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from sqlalchemy.orm import Session
from typing import Optional
class FinancialStatementRepository(BaseLocalRepository):
    
    def __init__(self, session: Session):

        super().__init__(session)
        self.data_store = []
    
    def save(self, financial_statement):
        """Save financial statement to local storage"""
        self.data_store.append(financial_statement)
        
    def find_by_id(self, financial_statement_id):
        """Find financial statement by ID"""
        for statement in self.data_store:
            if getattr(statement, 'id', None) == financial_statement_id:
                return statement
        return None
        
    def find_all(self):
        """Find all financial statements"""
        return self.data_store.copy()

    def get_or_create(self, primary_key: str, **kwargs):
        """
        Get or create a financial statement with dependency resolution.
        
        Args:
            primary_key: Statement identifier
            **kwargs: Additional parameters for statement creation
            
        Returns:
            Financial statement entity or None if creation failed
        """
        try:
            # Check existing by primary identifier
            existing = self.find_by_id(primary_key)
            if existing:
                return existing
            
            # Create new financial statement with defaults
            from src.domain.entities.finance.financial_statements.financial_statement import FinancialStatement
            
            new_statement = FinancialStatement(
                id=primary_key,
                company_id=kwargs.get('company_id', 1),
                period=kwargs.get('period', 'Q4'),
                year=kwargs.get('year', 2024),
                statement_type=kwargs.get('statement_type', 'annual'),
                currency=kwargs.get('currency', 'USD'),
                filing_date=kwargs.get('filing_date'),
                source=kwargs.get('source', 'manual')
            )
            
            # Add to data store
            self.save(new_statement)
            return new_statement
            
        except Exception as e:
            print(f"Error in get_or_create for financial statement {primary_key}: {e}")
            return None