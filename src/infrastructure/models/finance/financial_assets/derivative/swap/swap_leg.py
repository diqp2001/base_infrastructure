
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

class SwapLegModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Swap Leg.
    Represents one side of a swap transaction.
    """
    __tablename__ = 'swap_legs'

    swap_id = Column(Integer, ForeignKey('swaps.id'), nullable=False)
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    
    # Relationship
    swaps = relationship("src.infrastructure.models.finance.financial_assets.derivative.swap.swap.SwapModel", back_populates="swap_legs")
    __mapper_args__ = {
    "polymorphic_identity": "swap_leg",
}
    def __repr__(self):
        return f"<SwapLeg(id={self.id}, swap_id={self.swap_id}, type={self.leg_type}, rate={self.fixed_rate})>"