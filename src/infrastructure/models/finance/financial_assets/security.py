"""
Unified ORM model for Security - combining live and backtesting data.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Security(Base):
    """
    SQLAlchemy ORM model for Security.
    Represents both live and mock/backtest securities with optional price snapshots.
    """
    __tablename__ = "securities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    # Symbol information
    ticker = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    security_type = Column(String(50), nullable=False)  # 'equity', 'forex', 'crypto', etc.

    # Market data
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    bid_price = Column(Numeric(20, 8), nullable=True)
    ask_price = Column(Numeric(20, 8), nullable=True)
    volume = Column(Integer, nullable=True, default=0)

    # Daily OHLC data
    daily_open = Column(Numeric(20, 8), nullable=True)
    daily_high = Column(Numeric(20, 8), nullable=True)
    daily_low = Column(Numeric(20, 8), nullable=True)
    daily_close = Column(Numeric(20, 8), nullable=True)

    # Holdings information
    holdings_quantity = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_average_cost = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_market_value = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_unrealized_pnl = Column(Numeric(20, 8), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 8), nullable=True, default=0)

    # Risk and performance metrics
    volatility_20d = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    volatility = Column(Numeric(10, 4), nullable=True)  # generic backtest field
    beta = Column(Numeric(10, 4), nullable=True)
    correlation = Column(Numeric(10, 4), nullable=True)

    # Trading properties
    is_tradeable = Column(Boolean, default=True)
    is_delisted = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    contract_multiplier = Column(Numeric(15, 4), nullable=True, default=1)
    tick_size = Column(Numeric(10, 6), nullable=True, default=0.01)
    margin_requirement = Column(Numeric(5, 4), nullable=True, default=0.5)  # %

    # Market data cache and history
    price_history = Column(JSON, nullable=True)       # JSON array of prices
    market_data_cache = Column(JSON, nullable=True)   # Cached indicators, etc.

    # Snapshot fields (inline instead of separate table)
    snapshot_timestamp = Column(DateTime, nullable=True, index=True)
    snapshot_price = Column(Numeric(20, 8), nullable=True)
    snapshot_volume = Column(Integer, nullable=True)
    snapshot_bid = Column(Numeric(20, 8), nullable=True)
    snapshot_ask = Column(Numeric(20, 8), nullable=True)
    snapshot_open = Column(Numeric(20, 8), nullable=True)
    snapshot_high = Column(Numeric(20, 8), nullable=True)
    snapshot_low = Column(Numeric(20, 8), nullable=True)
    snapshot_close = Column(Numeric(20, 8), nullable=True)
    snapshot_return_1d = Column(Numeric(15, 8), nullable=True)
    snapshot_volatility_20d = Column(Numeric(10, 4), nullable=True)

    # Status fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_market_update = Column(DateTime, nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="securities")
    market_data_history = relationship("MarketDataModel", 
                                     primaryjoin="and_(Security.ticker==MarketDataModel.symbol_ticker, "
                                               "Security.exchange==MarketDataModel.symbol_exchange)",
                                     foreign_keys="[MarketDataModel.symbol_ticker, MarketDataModel.symbol_exchange]",
                                     viewonly=True)

    def __repr__(self):
        return (
            f"<Security(id={self.id}, ticker={self.ticker}, "
            f"exchange={self.exchange}, type={self.security_type}, "
            f"price={self.current_price}, qty={self.holdings_quantity})>"
        )
