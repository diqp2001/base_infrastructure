"""
Unified ORM model for Portfolio - combining live, mock, and snapshot portfolio data.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class PortfolioModel(Base):
    __tablename__ = "portfolios"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    portfolio_type = Column(String(50), nullable=False, default="STANDARD")
    backtest_id = Column(String(100), nullable=True, index=True)

    # ONE portfolio → MANY positions
    # positions = relationship(
    #     "src.infrastructure.models.finance.position.PositionModel",
    #     back_populates="portfolio",
    #     cascade="all, delete-orphan"
    # )
    portfolio_holdings = relationship("src.infrastructure.models.finance.holding.portfolio_holding.PortfolioHoldingsModel", back_populates="portfolios")
    security_holdings = relationship("src.infrastructure.models.finance.holding.security_holding.SecurityHoldingModel", back_populates="portfolios")
    #portfolio_statistics = relationship("src.infrastructure.models.finance.portfolio.portfolio_statistics.PortfolioStatisticsModel", back_populates="portfolios", cascade="all, delete-orphan")
    securities = relationship("src.infrastructure.models.finance.financial_assets.security.SecurityModel", back_populates="portfolios")

    def __repr__(self):
        return (
            f"<Portfolio(id={self.id}, name={self.name}, "
        )
