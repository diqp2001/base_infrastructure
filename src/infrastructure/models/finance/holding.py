"""
SQLAlchemy ORM model for Holding entities.
Represents assets held within portfolios or other containers.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class HoldingModel(Base):
    """
    SQLAlchemy ORM model for Holding.
    Represents an asset held in a container (portfolio, book, strategy, account).
    """
    __tablename__ = "holdings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Asset information
    asset_id = Column(Integer, nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)  # 'SHARE', 'BOND', 'OPTION', etc.
    
    # Container information
    container_id = Column(Integer, nullable=False, index=True)
    container_type = Column(String(50), nullable=False, default='PORTFOLIO')  # 'PORTFOLIO', 'BOOK', etc.
    
    # Holding details
    quantity = Column(Numeric(20, 8), nullable=False, default=0)
    average_cost = Column(Numeric(20, 4), nullable=True)
    current_price = Column(Numeric(20, 4), nullable=True)
    market_value = Column(Numeric(20, 4), nullable=True)
    
    # P&L information
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    
    # Position information
    weight_percent = Column(Numeric(10, 4), nullable=True, default=0)
    
    # Status and dates
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return (
            f"<HoldingModel(id={self.id}, asset_id={self.asset_id}, "
            f"container_id={self.container_id}, quantity={self.quantity})>"
        )


class PortfolioHoldingModel(Base):
    """
    Specialized model for portfolio holdings.
    """
    __tablename__ = "portfolio_holdings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relationships
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False, index=True)
    asset_id = Column(Integer, nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)
    
    # Holding details
    quantity = Column(Numeric(20, 8), nullable=False, default=0)
    average_cost = Column(Numeric(20, 4), nullable=True)
    current_price = Column(Numeric(20, 4), nullable=True)
    market_value = Column(Numeric(20, 4), nullable=True)
    
    # Portfolio-specific fields
    target_weight_percent = Column(Numeric(10, 4), nullable=True)
    actual_weight_percent = Column(Numeric(10, 4), nullable=True)
    
    # Performance
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    total_return = Column(Numeric(15, 4), nullable=True, default=0)
    
    # Status and dates
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="portfolio_holdings")
    
    def __repr__(self):
        return (
            f"<PortfolioHoldingModel(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"asset_id={self.asset_id}, quantity={self.quantity})>"
        )


class PortfolioCompanyShareHoldingModel(Base):
    """
    Specialized model for company share holdings in portfolios.
    """
    __tablename__ = "portfolio_company_share_holdings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relationships
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False, index=True)
    company_share_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    
    # Holding details
    quantity = Column(Numeric(20, 8), nullable=False, default=0)
    average_cost = Column(Numeric(20, 4), nullable=True)
    current_price = Column(Numeric(20, 4), nullable=True)
    market_value = Column(Numeric(20, 4), nullable=True)
    
    # Portfolio allocation
    target_weight_percent = Column(Numeric(10, 4), nullable=True)
    actual_weight_percent = Column(Numeric(10, 4), nullable=True)
    
    # Performance metrics
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    total_return = Column(Numeric(15, 4), nullable=True, default=0)
    total_return_percent = Column(Numeric(10, 4), nullable=True, default=0)
    
    # Risk metrics
    beta = Column(Numeric(10, 4), nullable=True)
    volatility = Column(Numeric(10, 4), nullable=True)
    
    # Trading information
    last_trade_date = Column(Date, nullable=True)
    last_trade_price = Column(Numeric(20, 4), nullable=True)
    
    # Status and dates
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="company_share_holdings")
    
    def __repr__(self):
        return (
            f"<PortfolioCompanyShareHoldingModel(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"symbol={self.symbol}, quantity={self.quantity})>"
        )