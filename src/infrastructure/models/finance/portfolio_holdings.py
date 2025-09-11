"""
SQLAlchemy ORM model for PortfolioHoldings.
Maps to domain entity PortfolioHoldings following DDD principles.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class PortfolioHoldingsModel(Base):
    """
    SQLAlchemy ORM model for PortfolioHoldings.
    Represents current holdings snapshot for a portfolio.
    """
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Holdings data
    cash_balance = Column(Numeric(20, 4), nullable=False, default=0)
    total_value = Column(Numeric(20, 4), nullable=False, default=0)
    holdings_value = Column(Numeric(20, 4), nullable=False, default=0)
    
    # JSON storage for individual holdings
    holdings_data = Column(JSON, nullable=True)  # Serialized SecurityHoldings
    
    # Timestamps
    snapshot_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings_snapshots")
    
    def __repr__(self):
        return (
            f"<PortfolioHoldingsModel(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"total_value={self.total_value}, cash={self.cash_balance})>"
        )


class SecurityHoldingsModel(Base):
    """
    SQLAlchemy ORM model for individual SecurityHoldings.
    Represents holdings for a specific security.
    """
    __tablename__ = "security_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Security identification
    symbol_ticker = Column(String(20), nullable=False, index=True)
    symbol_exchange = Column(String(50), nullable=False)
    security_type = Column(String(50), nullable=False)
    
    # Holdings data
    quantity = Column(Numeric(20, 8), nullable=False, default=0)
    average_cost = Column(Numeric(20, 8), nullable=False, default=0)
    market_value = Column(Numeric(20, 8), nullable=False, default=0)
    unrealized_pnl = Column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl = Column(Numeric(20, 8), nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="security_holdings")
    
    def __repr__(self):
        return (
            f"<SecurityHoldingsModel(id={self.id}, symbol={self.symbol_ticker}, "
            f"quantity={self.quantity}, value={self.market_value})>"
        )