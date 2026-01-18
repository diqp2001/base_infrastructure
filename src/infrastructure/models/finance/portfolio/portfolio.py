"""
Unified ORM model for Portfolio - combining live, mock, and snapshot portfolio data.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Portfolio(Base):
    """
    SQLAlchemy ORM model for Portfolio.
    Represents both live portfolios and backtest/mock portfolios with snapshots.
    """
    __tablename__ = "portfolios"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Portfolio identification
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    portfolio_type = Column(String(50), nullable=False, default="STANDARD")  # 'STANDARD', 'RETIREMENT', 'BACKTEST', etc.
    backtest_id = Column(String(100), nullable=True, index=True)  # For mock/backtest portfolios

    # Owner/Manager information
    owner_id = Column(Integer, nullable=True)
    manager_id = Column(Integer, nullable=True)
    account_number = Column(String(50), nullable=True, unique=True)

    # Portfolio financial data
    initial_cash = Column(Numeric(20, 4), nullable=True)  # for backtests
    current_cash = Column(Numeric(20, 4), nullable=True)
    total_value = Column(Numeric(20, 4), nullable=True, default=0)
    cash_balance = Column(Numeric(20, 4), nullable=True, default=0)
    invested_amount = Column(Numeric(20, 4), nullable=True, default=0)
    holdings_value = Column(Numeric(20, 4), nullable=True, default=0)

    # Performance metrics
    total_return = Column(Numeric(15, 4), nullable=True, default=0)
    total_return_percent = Column(Numeric(10, 4), nullable=True, default=0)
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    max_drawdown = Column(Numeric(10, 4), nullable=True, default=0)
    high_water_mark = Column(Numeric(20, 4), nullable=True)

    # Trading statistics
    total_trades = Column(Integer, nullable=True, default=0)
    winning_trades = Column(Integer, nullable=True, default=0)
    losing_trades = Column(Integer, nullable=True, default=0)
    win_rate = Column(Numeric(5, 2), nullable=True, default=0)

    # Risk metrics
    volatility = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    var_95 = Column(Numeric(20, 4), nullable=True)
    alpha = Column(Numeric(10, 4), nullable=True)
    tracking_error = Column(Numeric(10, 4), nullable=True)

    # Benchmark comparison
    benchmark_id = Column(Integer, nullable=True)

    # Asset allocation (JSON stored as text)
    asset_allocation = Column(Text, nullable=True)
    sector_allocation = Column(Text, nullable=True)
    geographic_allocation = Column(Text, nullable=True)

    # Holdings & transactions (JSON)
    holdings_data = Column(JSON, nullable=True)        # {symbol: quantity}
    average_costs_data = Column(JSON, nullable=True)   # {symbol: avg_cost}
    securities_data = Column(JSON, nullable=True)      # Securities config
    transaction_history = Column(JSON, nullable=True)  # List of executed trades

    # Portfolio configuration
    currency = Column(String(3), nullable=False, default="USD")
    rebalancing_frequency = Column(String(20), nullable=True)
    investment_strategy = Column(String(100), nullable=True)
    risk_tolerance = Column(String(20), nullable=True)

    # Status and dates
    is_active = Column(Boolean, default=True)
    is_paper_trading = Column(Boolean, default=False)
    inception_date = Column(Date, nullable=True)
    last_rebalance_date = Column(Date, nullable=True)
    backtest_start_date = Column(DateTime, nullable=True)
    backtest_end_date = Column(DateTime, nullable=True)

    # Fees and costs
    management_fee_rate = Column(Numeric(5, 4), nullable=True, default=0)
    performance_fee_rate = Column(Numeric(5, 4), nullable=True, default=0)
    total_fees_paid = Column(Numeric(15, 4), nullable=True, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)

    # Snapshot fields (inline instead of separate table)
    snapshot_date = Column(DateTime, nullable=True, index=True) #ix_portfolios_snapshot_date 
    snapshot_cash = Column(Numeric(20, 4), nullable=True)
    snapshot_holdings_value = Column(Numeric(20, 4), nullable=True)
    snapshot_unrealized_pnl = Column(Numeric(20, 4), nullable=True)
    snapshot_total_return_percent = Column(Numeric(10, 4), nullable=True)
    snapshot_drawdown_percent = Column(Numeric(10, 4), nullable=True)
    holdings_snapshot = Column(JSON, nullable=True)

    # Relationships
    positions = relationship("Position", back_populates="portfolios")
    portfolio_holdings = relationship("PortfolioHoldings", back_populates="portfolios", cascade="all, delete-orphan")
    portfolio_statistics = relationship("PortfolioStatistics", back_populates="portfolios", cascade="all, delete-orphan")
    securities = relationship("Security", back_populates="portfolios", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Portfolio(id={self.id}, name={self.name}, "
            f"value={self.total_value}, type={self.portfolio_type}, currency={self.currency})>"
        )
