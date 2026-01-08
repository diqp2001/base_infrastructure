"""
Infrastructure model for balance sheet.
SQLAlchemy model for domain balance sheet entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import DECIMAL
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatement


class BalanceSheet(FinancialStatement):
    __tablename__ = 'balance_sheets'
    
    id = Column(Integer, ForeignKey("financial_statements.id"), primary_key=True)
    assets = Column(DECIMAL(precision=20, scale=2), nullable=False)
    liabilities = Column(DECIMAL(precision=20, scale=2), nullable=False)
    equity = Column(DECIMAL(precision=20, scale=2), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'balance_sheet',
    }
    
    def __init__(self, company_id: int, period: str, year: int, assets: float, liabilities: float, equity: float):
        super().__init__(company_id, period, year)
        self.assets = assets
        self.liabilities = liabilities
        self.equity = equity
    
    def __repr__(self):
        return f"<BalanceSheet(company_id={self.company_id}, period={self.period}, year={self.year}, assets={self.assets})>"