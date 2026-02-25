"""
Infrastructure model for balance sheet.
SQLAlchemy model for domain balance sheet entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatementModel


class BalanceSheetModel(FinancialStatementModel):
    __tablename__ = 'balance_sheets'
    
    id = Column(Integer, ForeignKey("financial_statements.id"), primary_key=True)
    assets = Column(Integer, nullable=False)
    liabilities = Column(Integer, nullable=False)
    equity = Column(Integer, nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'balance_sheet',
    }
    
    
    
    def __repr__(self):
        return f"<BalanceSheet(company_id={self.company_id}, period={self.period}, year={self.year}, assets={self.assets})>"