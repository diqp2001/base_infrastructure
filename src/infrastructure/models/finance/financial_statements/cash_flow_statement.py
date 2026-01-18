"""
Infrastructure model for cash flow statement.
SQLAlchemy model for domain cash flow statement entity.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import DECIMAL
from src.infrastructure.models.finance.financial_statements.financial_statement import FinancialStatementModel


class CashFlowStatementModel(FinancialStatementModel):
    __tablename__ = 'cash_flow_statements'
    
    id = Column(Integer, ForeignKey("financial_statements.id"), primary_key=True)
    operating_cash_flow = Column(DECIMAL(precision=20, scale=2), nullable=False)
    investing_cash_flow = Column(DECIMAL(precision=20, scale=2), nullable=False)
    financing_cash_flow = Column(DECIMAL(precision=20, scale=2), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'cash_flow_statement',
    }
    
    def __init__(self, company_id: int, period: str, year: int, operating_cash_flow: float, 
                 investing_cash_flow: float, financing_cash_flow: float):
        super().__init__(company_id, period, year)
        self.operating_cash_flow = operating_cash_flow
        self.investing_cash_flow = investing_cash_flow
        self.financing_cash_flow = financing_cash_flow
    
    def __repr__(self):
        return f"<CashFlowStatement(company_id={self.company_id}, period={self.period}, year={self.year})>"