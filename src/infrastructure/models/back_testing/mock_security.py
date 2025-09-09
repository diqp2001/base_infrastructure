"""
ORM model for MockSecurity - infrastructure layer for backtesting.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, JSON
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class MockSecurityModel(Base):
    """
    SQLAlchemy ORM model for MockSecurity backtesting data.
    Stores security configurations and state during backtests.
    """
    __tablename__ = 'mock_securities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('mock_portfolios.id'), nullable=True)
    
    # Security identification
    symbol_ticker = Column(String(20), nullable=False, index=True)
    symbol_exchange = Column(String(50), nullable=False)
    security_type = Column(String(20), nullable=False)
    
    # Current market data
    current_price = Column(Numeric(20, 6), nullable=False)
    bid_price = Column(Numeric(20, 6), nullable=True)
    ask_price = Column(Numeric(20, 6), nullable=True)
    volume = Column(Integer, nullable=True, default=0)
    
    # Daily OHLC data
    daily_open = Column(Numeric(20, 6), nullable=True)
    daily_high = Column(Numeric(20, 6), nullable=True)
    daily_low = Column(Numeric(20, 6), nullable=True)
    daily_close = Column(Numeric(20, 6), nullable=True)
    
    # Holdings information
    holdings_quantity = Column(Numeric(20, 6), nullable=False, default=0)
    average_cost = Column(Numeric(20, 6), nullable=False, default=0)
    market_value = Column(Numeric(20, 4), nullable=False, default=0)
    unrealized_pnl = Column(Numeric(20, 4), nullable=False, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=False, default=0)
    
    # Risk and performance metrics
    volatility = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    correlation = Column(Numeric(10, 4), nullable=True)
    
    # Trading state
    is_tradeable = Column(Boolean, default=True)
    is_delisted = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    
    # Market data cache (JSON)
    market_data_cache = Column(JSON, nullable=True)
    
    # Price history (JSON array) - limited to recent data
    price_history = Column(JSON, nullable=True)
    
    # Contract specifications
    contract_multiplier = Column(Numeric(10, 2), nullable=False, default=1)
    tick_size = Column(Numeric(10, 6), nullable=False, default=0.01)
    margin_requirement = Column(Numeric(5, 4), nullable=False, default=0.5)  # As percentage
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    last_market_update = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("MockPortfolioModel", back_populates="mock_securities")
    price_snapshots = relationship("MockSecurityPriceSnapshot", back_populates="security")

    def __repr__(self):
        return (f"<MockSecurityModel(id={self.id}, symbol={self.symbol_ticker}, "
                f"price=${self.current_price}, quantity={self.holdings_quantity})>")


class MockSecurityPriceSnapshot(Base):
    """
    Model for storing security price snapshots during backtests.
    Used for price history and volatility calculations.
    """
    __tablename__ = 'mock_security_price_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    security_id = Column(Integer, ForeignKey('mock_securities.id'), nullable=False)
    
    # Price data
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Numeric(20, 6), nullable=False)
    volume = Column(Integer, nullable=True)
    bid = Column(Numeric(20, 6), nullable=True)
    ask = Column(Numeric(20, 6), nullable=True)
    
    # OHLC data for the period
    open_price = Column(Numeric(20, 6), nullable=True)
    high_price = Column(Numeric(20, 6), nullable=True)
    low_price = Column(Numeric(20, 6), nullable=True)
    close_price = Column(Numeric(20, 6), nullable=True)
    
    # Calculated metrics
    return_1d = Column(Numeric(15, 8), nullable=True)  # 1-day return
    volatility_20d = Column(Numeric(10, 4), nullable=True)  # 20-day volatility
    
    # Relationship
    security = relationship("MockSecurityModel", back_populates="price_snapshots")
    
    def __repr__(self):
        return (f"<MockSecurityPriceSnapshot(id={self.id}, security_id={self.security_id}, "
                f"timestamp={self.timestamp}, price=${self.price})>")