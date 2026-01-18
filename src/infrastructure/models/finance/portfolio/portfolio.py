"""
Unified ORM model for Portfolio - combining live, mock, and snapshot portfolio data.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class PortfolioModel(Base):
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
