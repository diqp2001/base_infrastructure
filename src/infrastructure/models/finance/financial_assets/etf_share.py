"""
ORM model for ETFShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class ETFShareModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for ETFShare.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_shares'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    ticker = Column(String(20), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # ETF-specific fields
    fund_name = Column(String(255), nullable=False)
    expense_ratio = Column(Numeric(5, 4), nullable=True)
    net_assets = Column(Numeric(20, 2), nullable=True)
    tracking_index = Column(String(100), nullable=True)
    dividend_frequency = Column(String(20), nullable=True)
    
    # Market data fields
    current_price = Column(Numeric(15, 4), default=0)
    nav_price = Column(Numeric(15, 4), nullable=True)  # Net Asset Value
    premium_discount = Column(Numeric(5, 4), nullable=True)  # vs NAV
    last_update = Column(DateTime, nullable=True)
    
    # Fundamental data fields
    market_cap = Column(Numeric(20, 2), nullable=True)
    shares_outstanding = Column(Numeric(20, 0), nullable=True)
    dividend_yield = Column(Numeric(5, 4), nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "etf_share",
    }

    # Relationships
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="etf_shares")

    def __repr__(self):
        return f"<ETFShare(id={self.id}, ticker={self.ticker}, fund_name={self.fund_name})>"