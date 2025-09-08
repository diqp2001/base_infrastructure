"""
ORM model for Portfolio - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Portfolio(Base):
    """
    SQLAlchemy ORM model for Portfolio.
    Represents a collection of financial positions/assets.
    """
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Portfolio identification
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    portfolio_type = Column(String(50), nullable=False, default='STANDARD')  # 'STANDARD', 'RETIREMENT', 'MANAGED', etc.
    
    # Owner/Manager information
    owner_id = Column(Integer, nullable=True)  # Reference to user/client
    manager_id = Column(Integer, nullable=True)  # Reference to portfolio manager
    account_number = Column(String(50), nullable=True, unique=True)
    
    # Portfolio metrics
    total_value = Column(Numeric(20, 4), nullable=True, default=0)
    cash_balance = Column(Numeric(20, 4), nullable=True, default=0)
    invested_amount = Column(Numeric(20, 4), nullable=True, default=0)
    
    # Performance metrics
    total_return = Column(Numeric(15, 4), nullable=True, default=0)
    total_return_percent = Column(Numeric(10, 4), nullable=True, default=0)
    unrealized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    realized_pnl = Column(Numeric(20, 4), nullable=True, default=0)
    
    # Risk metrics
    volatility = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    var_95 = Column(Numeric(20, 4), nullable=True)  # Value at Risk (95% confidence)
    
    # Benchmark comparison
    benchmark_id = Column(Integer, nullable=True)  # Reference to benchmark index
    alpha = Column(Numeric(10, 4), nullable=True)  # Alpha vs benchmark
    tracking_error = Column(Numeric(10, 4), nullable=True)
    
    # Asset allocation (JSON stored as text)
    asset_allocation = Column(Text, nullable=True)  # JSON with allocation percentages
    sector_allocation = Column(Text, nullable=True)  # JSON with sector weights
    geographic_allocation = Column(Text, nullable=True)  # JSON with geographic weights
    
    # Portfolio configuration
    currency = Column(String(3), nullable=False, default='USD')
    rebalancing_frequency = Column(String(20), nullable=True)  # 'MONTHLY', 'QUARTERLY', etc.
    investment_strategy = Column(String(100), nullable=True)
    risk_tolerance = Column(String(20), nullable=True)  # 'CONSERVATIVE', 'MODERATE', 'AGGRESSIVE'
    
    # Status and dates
    is_active = Column(Boolean, default=True)
    is_paper_trading = Column(Boolean, default=False)
    inception_date = Column(Date, nullable=False)
    last_rebalance_date = Column(Date, nullable=True)
    
    # Fees and costs
    management_fee_rate = Column(Numeric(5, 4), nullable=True, default=0)  # Annual management fee %
    performance_fee_rate = Column(Numeric(5, 4), nullable=True, default=0)  # Performance fee %
    total_fees_paid = Column(Numeric(15, 4), nullable=True, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)

    # Relationships
    positions = relationship("Position", back_populates="portfolio")

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name}, value={self.total_value}, currency={self.currency})>"