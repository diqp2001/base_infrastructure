"""
ORM model for Equity - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class EquityModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Equity.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'equities'

    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    __mapper_args__ = {
    "polymorphic_identity": "equity",
}
    def __repr__(self):
        return f"<Equity(id={self.id}, ticker={self.ticker}, exchange={self.exchange}, price={self.current_price})>"