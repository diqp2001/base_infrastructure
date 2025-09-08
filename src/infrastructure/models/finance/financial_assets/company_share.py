"""
ORM model for CompanyShare - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class CompanyShare(Base):
    """
    SQLAlchemy ORM model for CompanyShare.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'company_shares'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # Market data fields
    current_price = Column(Numeric(15, 4), default=0)
    last_update = Column(DateTime, nullable=True)
    
    # Fundamental data fields
    market_cap = Column(Numeric(20, 2), nullable=True)
    shares_outstanding = Column(Numeric(20, 0), nullable=True)
    pe_ratio = Column(Numeric(10, 4), nullable=True)
    dividend_yield = Column(Numeric(5, 4), nullable=True)
    book_value_per_share = Column(Numeric(15, 4), nullable=True)
    earnings_per_share = Column(Numeric(15, 4), nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="company_shares")
    exchange = relationship("Exchange", back_populates="company_shares") 

    def __repr__(self):
        return f"<CompanyShare(id={self.id}, ticker={self.ticker}, company_id={self.company_id})>"