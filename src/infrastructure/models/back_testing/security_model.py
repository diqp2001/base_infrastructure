"""
Infrastructure models for security system.
SQLAlchemy ORM models.
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.infrastructure.models import ModelBase as Base


class Security(Base):
    """SQLAlchemy model for Security domain entity."""
    __tablename__ = 'bt_securities'
    
    id = Column(String(255), primary_key=True)  # UUID or symbol_id
    symbol_id = Column(String(255), nullable=False, index=True, unique=True)
    resolution = Column(String(20), default="Minute")
    leverage = Column(Numeric(precision=18, scale=8), default=1)
    fill_data_forward = Column(Boolean, default=True)
    
    # Market data
    market_price = Column(Numeric(precision=18, scale=8))
    bid_price = Column(Numeric(precision=18, scale=8))
    ask_price = Column(Numeric(precision=18, scale=8))
    volume = Column(Integer, default=0)
    last_update_time = Column(DateTime)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    symbol = relationship("Symbol", back_populates="securities")
    holdings = relationship("SecurityHolding", back_populates="security")


class SecurityHolding(Base):
    """SQLAlchemy model for SecurityHolding domain entity."""
    __tablename__ = 'bt_security_holdings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(String(255), nullable=False, index=True)
    security_id = Column(String(255), ForeignKey('bt_securities.id'), nullable=False, index=True)
    symbol_id = Column(String(255), nullable=False)
    quantity = Column(Integer, default=0)
    average_price = Column(Numeric(precision=18, scale=8), default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    security = relationship("Security", back_populates="holdings")


class Portfolio(Base):
    """SQLAlchemy model for Portfolio domain entity."""
    __tablename__ = 'bt_portfolios'
    
    id = Column(String(255), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    cash = Column(Numeric(precision=18, scale=2), default=100000)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class MarketData(Base):
    """SQLAlchemy model for market data storage."""
    __tablename__ = 'bt_market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    data_type = Column(String(20), nullable=False, index=True)  # TRADE_BAR, QUOTE_BAR, TICK
    
    # OHLCV data
    open_price = Column(Numeric(precision=18, scale=8))
    high_price = Column(Numeric(precision=18, scale=8))
    low_price = Column(Numeric(precision=18, scale=8))
    close_price = Column(Numeric(precision=18, scale=8))
    volume = Column(Integer)
    
    # Tick data
    bid_price = Column(Numeric(precision=18, scale=8))
    ask_price = Column(Numeric(precision=18, scale=8))
    bid_size = Column(Integer)
    ask_size = Column(Integer)
    tick_type = Column(String(20))
    
    # Metadata
    exchange = Column(String(50))
    suspicious = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Algorithm(Base):
    """SQLAlchemy model for trading algorithms."""
    __tablename__ = 'bt_algorithms'
    
    id = Column(String(255), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    language = Column(String(20), default="python")
    
    # Configuration
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_cash = Column(Numeric(precision=18, scale=2), default=100000)
    
    # Results
    total_return = Column(Numeric(precision=18, scale=8))
    sharpe_ratio = Column(Numeric(precision=18, scale=8))
    max_drawdown = Column(Numeric(precision=18, scale=8))
    
    # Code and logs
    source_code = Column(Text)
    logs = Column(Text)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))