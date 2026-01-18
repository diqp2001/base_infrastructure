from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class SecurityHoldingModel(Base):
    """
    SQLAlchemy ORM model for individual SecurityHoldings.
    Represents holdings for a specific security.
    """
    __tablename__ = "security_holdings"
    __table_args__ = {'extend_existing': True}

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
    portfolios = relationship("src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel", back_populates="security_holdings")
    
    def __repr__(self):
        return (
            f"<SecurityHoldingsModel(id={self.id}, symbol={self.symbol_ticker}, "
            f"quantity={self.quantity}, value={self.market_value})>"
        )