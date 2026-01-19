"""
ORM model for CompanyShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class CompanyShareModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for CompanyShare.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'company_shares'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share",
    }
    # Relationships
    company = relationship("src.infrastructure.models.finance.company.CompanyModel", back_populates="company_shares")
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="company_shares") 
    portfolio_company_share_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHoldingModel", back_populates="company_shares") 
    def __repr__(self):
        return f"<CompanyShare(id={self.id}, ticker={self.ticker}, company_id={self.company_id})>"