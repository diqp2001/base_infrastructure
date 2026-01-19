"""
ORM model for Derivatives - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class DerivativeModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Derivative securities.
    Base class for all derivative instruments.
    """
    __tablename__ = 'derivatives'

    
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    __mapper_args__ = {
    "polymorphic_identity": "derivative",
}
    def __repr__(self):
        return f"<Derivative(id={self.id})>"