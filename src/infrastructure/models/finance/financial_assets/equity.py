"""
ORM model for Equity - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Equity(Base):
    """
    SQLAlchemy ORM model for Equity.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'equities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Symbol information (inherits Security properties)
    ticker = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    security_type = Column(String(50), nullable=False, default='equity')
    
    # Market data
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    last_update = Column(DateTime, nullable=True)
    
    # Fundamental data
    pe_ratio = Column(Numeric(10, 4), nullable=True)
    dividend_yield = Column(Numeric(5, 4), nullable=True)
    market_cap = Column(Numeric(20, 2), nullable=True)
    shares_outstanding = Column(Numeric(20, 0), nullable=True)
    book_value_per_share = Column(Numeric(15, 4), nullable=True)
    earnings_per_share = Column(Numeric(15, 4), nullable=True)
    
    # Classification
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    
    # Dividend history (JSON stored as text)
    dividend_history = Column(Text, nullable=True)  # JSON array of dividend payments
    stock_splits = Column(Text, nullable=True)  # JSON array of stock splits
    
    # Holdings information
    holdings_quantity = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_average_cost = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_market_value = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_unrealized_pnl = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Trading properties
    is_tradeable = Column(Boolean, default=True)
    contract_multiplier = Column(Numeric(15, 4), nullable=True, default=1)
    
    # Margin requirements
    long_margin_requirement = Column(Numeric(5, 4), nullable=True, default=0.5)  # 50%
    short_margin_requirement = Column(Numeric(5, 4), nullable=True, default=1.5)  # 150%
    
    # Volatility metrics
    volatility_20d = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    
    # Corporate actions tracking
    last_dividend_date = Column(Date, nullable=True)
    next_earnings_date = Column(Date, nullable=True)
    last_split_date = Column(Date, nullable=True)
    
    # Status fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Equity(id={self.id}, ticker={self.ticker}, exchange={self.exchange}, price={self.current_price})>"