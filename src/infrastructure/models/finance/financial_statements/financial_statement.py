"""
Infrastructure models for financial statements.
SQLAlchemy models for domain financial statement entities.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FinancialStatementModel(Base):
    __tablename__ = 'financial_statements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period = Column(String(20), nullable=False)  # Q1, Q2, Q3, Q4, Annual
    year = Column(Integer, nullable=False)
    statement_type = Column(String(50), nullable=False)  # Discriminator
    
    # Relationships
    company = relationship("Company")
    
    __mapper_args__ = {
        'polymorphic_identity': 'financial_statement',
        'polymorphic_on': statement_type
    }
    
    
    def __repr__(self):
        return f"<FinancialStatement(company_id={self.company_id}, period={self.period}, year={self.year})>"