"""
Unified ORM model for Security - combining live and backtesting data.
"""

from sqlalchemy import (
    Column, Date, Integer, String, Numeric, Boolean, DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models import ModelBase as Base


class SecurityModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Security.
    Represents both live and mock/backtest securities with optional price snapshots.
    """
    __tablename__ = "securities"
    __table_args__ = {'extend_existing': True}

    

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    

    # Relationships
    portfolio = relationship("src.infrastructure.models.finance.portfolio.portfolio.PortfolioModel", back_populates="securities")
    __mapper_args__ = {
    "polymorphic_identity": "security",
}

    def __repr__(self):
        return (
            f"<Security(id={self.id})>"
        )
