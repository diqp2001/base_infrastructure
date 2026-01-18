"""
ORM model for CompanyShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class CompanyShareModel(Base):
    """
    SQLAlchemy ORM model for CompanyShare.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'company_shares'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)

    # Relationships
    company = relationship("src.infrastructure.models.finance.company.CompanyModel", back_populates="company_shares")
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="company_shares") 
    portfolio_company_share_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHoldingModel", back_populates="company_shares") 
    def __repr__(self):
        return f"<CompanyShare(id={self.id}, ticker={self.ticker}, company_id={self.company_id})>"