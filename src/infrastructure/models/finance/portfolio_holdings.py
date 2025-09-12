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
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Holdings data
    cash_balance = Column(Numeric(20, 4), nullable=False, default=0)
    total_value = Column(Numeric(20, 4), nullable=False, default=0)
    holdings_value = Column(Numeric(20, 4), nullable=False, default=0)
    
    # JSON storage for individual holdings
    holdings_data = Column(JSON, nullable=True)  # Serialized SecurityHoldings
    
    # Timestamps
    
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="portfolio_holdings")
    
    def __repr__(self):
        return (
            f"<PortfolioHoldingsModel(id={self.id}, portfolio_id={self.portfolio_id}, "
            f"total_value={self.total_value}, cash={self.cash_balance})>"
        )


