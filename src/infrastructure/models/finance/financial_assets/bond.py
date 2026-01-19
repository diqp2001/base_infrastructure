"""
ORM model for Bond - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class BondModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Bond.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'bonds'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    # Currency relationship
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=True, index=True)
    

    __mapper_args__ = {
        "polymorphic_identity": "bond",
    }

    # Relationships
    currency = relationship("src.infrastructure.models.finance.financial_assets.currency.CurrencyModel", foreign_keys=[currency_id])

    def __repr__(self):
        return f"<Bond(id={self.id}, isin={self.isin}, issuer={self.issuer})>"
