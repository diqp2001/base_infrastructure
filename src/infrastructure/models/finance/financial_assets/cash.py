"""
ORM model for Cash - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Date, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class CashModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Cash.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'cash'

    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    # Currency relationship (required for cash)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False, index=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "cash",
    }

    # Relationships
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel", foreign_keys=[currency_id])
    def __repr__(self):
        return f"<Cash(id={self.id})>"