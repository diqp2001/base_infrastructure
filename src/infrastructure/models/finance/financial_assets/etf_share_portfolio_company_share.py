"""
ORM model for ETFSharePortfolioCompanyShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.share import ShareModel


class ETFSharePortfolioCompanyShareModel(ShareModel):
    """
    SQLAlchemy ORM model for ETFSharePortfolioCompanyShare.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_share_portfolio_company_shares'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("shares.id"), primary_key=True)
    
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=True)
    underlying_asset_id = Column(Integer, ForeignKey('financial_assets.id'), nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "etf_share_portfolio_company_share",
    }

    # Relationships
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="etf_share_portfolio_company_shares")
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel", back_populates="etf_share_portfolio_company_shares")
    underlying_asset = relationship("src.infrastructure.models.finance.financial_assets.financial_asset.FinancialAssetModel", back_populates="etf_share_portfolio_company_shares")

    def __repr__(self):
        return f"<ETFSharePortfolioCompanyShare(id={self.id}, symbol={self.symbol})>"