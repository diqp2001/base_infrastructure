"""
ORM model for CompanyShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models import ModelBase as Base


class ShareModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Share.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'shares'

    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="shares") 
    __mapper_args__ = {
    "polymorphic_identity": "share",
}
    def __repr__(self):
        return f"<Share(id={self.id}, ticker={self.ticker})>"