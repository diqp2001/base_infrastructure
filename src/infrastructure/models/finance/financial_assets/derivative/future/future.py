"""
ORM model for Futures - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey, Enum as SQLEnum
import enum
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.derivative.derivatives import DerivativeModel
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel




class FutureModel(DerivativeModel):
    """
    SQLAlchemy ORM model for Futures.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'futures'

    id = Column(Integer, ForeignKey("derivatives.id"), primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    
    
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="futures") 
    
    __mapper_args__ = {
    "polymorphic_identity": "future",
}

    def __repr__(self):
        return f"<Futures(id={self.id}, symbol={self.symbol}>"