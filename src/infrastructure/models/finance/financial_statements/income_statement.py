"""
Infrastructure model for income statement.
SQLAlchemy model for domain income statement entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import DECIMAL
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatementModel


class IncomeStatementModel(FinancialStatementModel):
    __tablename__ = 'income_statements'
    
    id = Column(Integer, ForeignKey("financial_statements.id"), primary_key=True)
    revenue = Column(DECIMAL(precision=20, scale=2), nullable=False)
    expenses = Column(DECIMAL(precision=20, scale=2), nullable=False)
    net_income = Column(DECIMAL(precision=20, scale=2), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'income_statement',
    }
    
    def __init__(self, company_id: int, period: str, year: int, revenue: float, expenses: float, net_income: float):
        super().__init__(company_id, period, year)
        self.revenue = revenue
        self.expenses = expenses
        self.net_income = net_income
    
    def __repr__(self):
        return f"<IncomeStatement(company_id={self.company_id}, period={self.period}, year={self.year}, revenue={self.revenue})>"