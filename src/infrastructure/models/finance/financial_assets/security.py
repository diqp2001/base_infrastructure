"""
ORM model for Security - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Security(Base):
    """
    SQLAlchemy ORM model for Security base class.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'securities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Symbol information
    ticker = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    security_type = Column(String(50), nullable=False)  # 'equity', 'forex', 'crypto', etc.
    
    # Market data
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    last_update = Column(DateTime, nullable=True)
    
    # Holdings information
    holdings_quantity = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_average_cost = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_market_value = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_unrealized_pnl = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Market data history (JSON stored as text)
    price_history = Column(Text, nullable=True)  # JSON array of recent prices
    market_data_cache = Column(Text, nullable=True)  # JSON for market data cache
    
    # Trading properties
    is_tradeable = Column(Boolean, default=True)
    contract_multiplier = Column(Numeric(15, 4), nullable=True, default=1)
    
    # Risk metrics
    volatility_20d = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    
    # Status fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Security(id={self.id}, ticker={self.ticker}, exchange={self.exchange}, type={self.security_type})>"