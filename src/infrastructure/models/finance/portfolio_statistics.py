"""
SQLAlchemy ORM model for PortfolioStatistics.
Maps to domain entity PortfolioStatistics following DDD principles.
"""

from sqlalchemy import (
    Column, Integer, Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class PortfolioStatisticsModel(Base):
    """
    SQLAlchemy ORM model for PortfolioStatistics.
    Stores performance and risk metrics for a portfolio.
    """
    __tablename__ = "portfolio_statistics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Return metrics
    total_return = Column(Numeric(20, 4), nullable=False, default=0)
    total_return_percent = Column(Numeric(10, 4), nullable=False, default=0)
    max_drawdown = Column(Numeric(10, 4), nullable=False, default=0)
    high_water_mark = Column(Numeric(20, 4), nullable=False, default=0)
    
    # Risk metrics
    volatility = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    beta = Column(Numeric(10, 4), nullable=True)
    alpha = Column(Numeric(10, 4), nullable=True)
    var_95 = Column(Numeric(20, 4), nullable=True)
    tracking_error = Column(Numeric(10, 4), nullable=True)
    
    # Trading statistics
    win_rate = Column(Numeric(5, 2), nullable=False, default=0)
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    calculation_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="portfolio_statistics")
    
    def __repr__(self):
        return (
            f"<PortfolioStatisticsModel(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"return={self.total_return_percent}%, sharpe={self.sharpe_ratio})>"
        )