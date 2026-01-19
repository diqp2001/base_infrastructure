"""
ORM model for ETFShare - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class ETFShareModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for ETFShare.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'etf_shares'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
   
    
    

    __mapper_args__ = {
        "polymorphic_identity": "etf_share",
    }

    # Relationships
    exchange = relationship("src.infrastructure.models.finance.exchange.ExchangeModel", back_populates="etf_shares")

    def __repr__(self):
        return f"<ETFShare(id={self.id}, ticker={self.ticker}, fund_name={self.fund_name})>"