"""
ORM model for Swaps - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class SwapModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Swap contracts.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'swaps'

    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    

    swap_legs = relationship("src.infrastructure.models.finance.financial_assets.derivative.swap.swap_leg.SwapLegModel", back_populates="swaps")
    
    
    __mapper_args__ = {
    "polymorphic_identity": "swap",
}
    def __repr__(self):
        return f"<Swap(id={self.id}, type={self.swap_type}, pv={self.present_value})>"







