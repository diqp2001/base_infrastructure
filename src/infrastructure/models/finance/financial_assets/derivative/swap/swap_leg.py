
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class SwapLegModel(Base):
    """
    SQLAlchemy ORM model for Swap Leg.
    Represents one side of a swap transaction.
    """
    __tablename__ = 'swap_legs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    swap_id = Column(Integer, ForeignKey('swaps.id'), nullable=False)
    
    # Leg identification
    leg_type = Column(String(20), nullable=False)  # 'FIXED', 'FLOATING'
    leg_position = Column(String(10), nullable=False)  # 'PAY', 'RECEIVE'
    
    # Rate information
    fixed_rate = Column(Numeric(10, 6), nullable=True)  # For fixed legs
    spread = Column(Numeric(10, 6), nullable=True, default=0)  # Spread over reference rate
    reference_rate = Column(String(20), nullable=True)  # 'LIBOR', 'SOFR', etc. for floating
    
    # Payment details
    notional_amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    payment_frequency = Column(String(20), nullable=False, default='quarterly')
    day_count_convention = Column(String(20), nullable=False, default='30/360')
    
    # Calculated values
    accrued_interest = Column(Numeric(15, 4), nullable=True, default=0)
    last_payment_date = Column(Date, nullable=True)
    next_payment_date = Column(Date, nullable=True)
    
    # Relationship
    swaps = relationship("src.infrastructure.models.finance.financial_assets.derivative.swap.swap.SwapModel", back_populates="swap_legs")

    def __repr__(self):
        return f"<SwapLeg(id={self.id}, swap_id={self.swap_id}, type={self.leg_type}, rate={self.fixed_rate})>"