"""
ORM model for MockPortfolio - infrastructure layer for backtesting.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, JSON
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class MockPortfolioModel(Base):
    """
    SQLAlchemy ORM model for MockPortfolio backtesting data.
    Stores portfolio states and performance during backtests.
    """
    __tablename__ = 'mock_portfolios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Backtest identification
    backtest_id = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Portfolio financial data
    initial_cash = Column(Numeric(20, 4), nullable=False)
    current_cash = Column(Numeric(20, 4), nullable=False)
    total_portfolio_value = Column(Numeric(20, 4), nullable=False)
    holdings_value = Column(Numeric(20, 4), nullable=False, default=0)
    
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
    
    # Risk metrics (simplified)
    volatility = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    
    # Holdings data (JSON)
    holdings_data = Column(JSON, nullable=True)  # {symbol: quantity}
    average_costs_data = Column(JSON, nullable=True)  # {symbol: avg_cost}
    securities_data = Column(JSON, nullable=True)  # Security configurations
    
    # Transaction history (JSON array)
    transaction_history = Column(JSON, nullable=True)
    
    # Portfolio state
    is_active = Column(Boolean, default=True)
    is_paper_trading = Column(Boolean, default=True)  # Always true for mocks
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    backtest_start_date = Column(DateTime, nullable=True)
    backtest_end_date = Column(DateTime, nullable=True)
    
    # Relationships
    mock_securities = relationship("MockSecurityModel", back_populates="portfolio")

    def __repr__(self):
        return (f"<MockPortfolioModel(id={self.id}, backtest_id={self.backtest_id}, "
                f"value={self.total_portfolio_value})>")


class MockPortfolioSnapshot(Base):
    """
    Model for storing portfolio snapshots at specific points in time during backtest.
    Used for performance tracking and analysis.
    """
    __tablename__ = 'mock_portfolio_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('mock_portfolios.id'), nullable=False)
    
    # Snapshot timestamp
    snapshot_date = Column(DateTime, nullable=False, index=True)
    
    # Portfolio values at snapshot time
    cash = Column(Numeric(20, 4), nullable=False)
    total_portfolio_value = Column(Numeric(20, 4), nullable=False)
    holdings_value = Column(Numeric(20, 4), nullable=False)
    unrealized_pnl = Column(Numeric(20, 4), nullable=False)
    
    # Performance metrics at snapshot
    total_return_percent = Column(Numeric(10, 4), nullable=True)
    drawdown_percent = Column(Numeric(10, 4), nullable=True)
    
    # Holdings snapshot (JSON)
    holdings_snapshot = Column(JSON, nullable=True)
    
    # Relationship
    portfolio = relationship("MockPortfolioModel")
    
    def __repr__(self):
        return (f"<MockPortfolioSnapshot(id={self.id}, portfolio_id={self.portfolio_id}, "
                f"date={self.snapshot_date}, value={self.total_portfolio_value})>")