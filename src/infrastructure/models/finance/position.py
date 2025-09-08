"""
ORM model for Position - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Position(Base):
    """
    SQLAlchemy ORM model for Position.
    Represents a holding of a specific financial asset within a portfolio.
    """
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Position identification
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    asset_id = Column(Integer, nullable=False)  # Reference to financial asset
    asset_type = Column(String(50), nullable=False, index=True)  # Type of asset held
    symbol = Column(String(20), nullable=True, index=True)  # Asset symbol for quick lookup
    
    # Quantity and pricing
    quantity = Column(Numeric(20, 8), nullable=False, default=0)
    average_cost = Column(Numeric(20, 8), nullable=False, default=0)
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Values
    cost_basis = Column(Numeric(20, 4), nullable=True, default=0)  # quantity * average_cost
    market_value = Column(Numeric(20, 4), nullable=True, default=0)  # quantity * current_price
    
    # P&L calculations
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    unrealized_pnl_percent = Column(Numeric(10, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    total_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    
    # Position metrics
    weight_in_portfolio = Column(Numeric(10, 6), nullable=True, default=0)  # Position weight as % of portfolio
    exposure = Column(Numeric(20, 4), nullable=True)  # Notional exposure (for derivatives)
    leverage = Column(Numeric(10, 4), nullable=True, default=1)
    
    # Risk metrics
    position_var = Column(Numeric(20, 4), nullable=True)  # Position-level Value at Risk
    delta_exposure = Column(Numeric(20, 4), nullable=True)  # For derivatives
    volatility_contribution = Column(Numeric(10, 6), nullable=True)
    
    # Trading information
    position_type = Column(String(20), nullable=False, default='LONG')  # 'LONG', 'SHORT'
    entry_date = Column(Date, nullable=True)
    last_transaction_date = Column(Date, nullable=True)
    average_holding_period_days = Column(Integer, nullable=True)
    
    # Fees and costs
    total_commissions = Column(Numeric(15, 4), nullable=True, default=0)
    total_fees = Column(Numeric(15, 4), nullable=True, default=0)
    accrued_interest = Column(Numeric(15, 4), nullable=True, default=0)
    dividend_receivable = Column(Numeric(15, 4), nullable=True, default=0)
    
    # Asset classification
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    currency = Column(String(3), nullable=False, default='USD')
    country = Column(String(3), nullable=True)  # ISO country code
    
    # Status and flags
    is_active = Column(Boolean, default=True)
    is_closed = Column(Boolean, default=False)
    is_margin_position = Column(Boolean, default=False)
    is_restricted = Column(Boolean, default=False)
    
    # Corporate actions tracking
    pending_corporate_actions = Column(Text, nullable=True)  # JSON array of pending actions
    dividend_history = Column(Text, nullable=True)  # JSON array of dividend payments
    split_history = Column(Text, nullable=True)  # JSON array of stock splits
    
    # Analytics
    holding_period_return = Column(Numeric(10, 4), nullable=True)
    annualized_return = Column(Numeric(10, 4), nullable=True)
    contribution_to_portfolio_return = Column(Numeric(10, 4), nullable=True)
    
    # Risk management
    stop_loss_price = Column(Numeric(20, 8), nullable=True)
    take_profit_price = Column(Numeric(20, 8), nullable=True)
    position_limit = Column(Numeric(20, 8), nullable=True)
    margin_requirement = Column(Numeric(20, 4), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)
    position_opened_at = Column(DateTime, nullable=True)
    position_closed_at = Column(DateTime, nullable=True)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="positions")

    def __repr__(self):
        return f"<Position(id={self.id}, portfolio_id={self.portfolio_id}, symbol={self.symbol}, qty={self.quantity}, value={self.market_value})>"