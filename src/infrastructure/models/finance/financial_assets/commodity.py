"""
ORM model for Commodity - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class CommodityModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Commodity.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'commodities'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
   

    __mapper_args__ = {
        "polymorphic_identity": "commodity",
    }

    def __repr__(self):
        return f"<Commodity(id={self.id}, ticker={self.ticker}, name={self.name}, price={self.current_price})>"