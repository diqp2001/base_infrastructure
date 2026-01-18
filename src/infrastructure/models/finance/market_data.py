"""
SQLAlchemy ORM model for MarketData.
Maps to domain entity MarketData following DDD principles.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class MarketDataModel(Base):
    """
    SQLAlchemy ORM model for MarketData.
    Stores comprehensive market data with OHLCV information.
    """
    __tablename__ = "market_data"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Security identification
    symbol_ticker = Column(String(20), nullable=False, index=True)
    symbol_exchange = Column(String(50), nullable=False, index=True)
    security_type = Column(String(50), nullable=False)
    
    # Core market data
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Numeric(20, 8), nullable=False)  # Current/close price
    volume = Column(Integer, nullable=True)
    
    # Bid/Ask data
    bid = Column(Numeric(20, 8), nullable=True)
    ask = Column(Numeric(20, 8), nullable=True)
    bid_size = Column(Integer, nullable=True)
    ask_size = Column(Integer, nullable=True)
    
    # OHLC data
    open = Column(Numeric(20, 8), nullable=True)
    high = Column(Numeric(20, 8), nullable=True)
    low = Column(Numeric(20, 8), nullable=True)
    close = Column(Numeric(20, 8), nullable=True)
    
    # Additional metadata
    exchange = Column(String(10), nullable=True)
    last_trade_time = Column(DateTime, nullable=True)
    
    # Calculated fields
    mid_price = Column(Numeric(20, 8), nullable=True)
    spread = Column(Numeric(20, 8), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    def __repr__(self):
        return (
            f"<MarketDataModel(symbol={self.symbol_ticker}, "
            f"timestamp={self.timestamp}, price={self.price}, volume={self.volume})>"
        )