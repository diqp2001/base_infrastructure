"""
ORM model for Swaps - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class SwapModel(Base):
    """
    SQLAlchemy ORM model for Swap contracts.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'swaps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Swap identification
    ticker = Column(String(50), nullable=False, index=True)
    swap_type = Column(String(30), nullable=False)  # 'interest_rate', 'currency', 'credit_default', etc.
    
    # Contract dates
    start_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    
    # Pricing and valuation
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    present_value = Column(Numeric(20, 8), nullable=True, default=0)
    intrinsic_value = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Risk metrics
    duration = Column(Numeric(15, 6), nullable=True)
    dv01 = Column(Numeric(20, 8), nullable=True)  # Dollar value of 1 basis point
    convexity = Column(Numeric(15, 6), nullable=True)
    
    # Payment structure (JSON stored as text)
    payment_dates = Column(Text, nullable=True)  # JSON array of payment dates
    
    # Contract status
    days_to_expiry = Column(Integer, nullable=True)
    is_expired = Column(Boolean, default=False)
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Margin and collateral
    initial_margin = Column(Numeric(20, 2), nullable=True)
    variation_margin = Column(Numeric(20, 2), nullable=True)
    collateral_posted = Column(Numeric(20, 2), nullable=True, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)

    # Relationships
    interest_rate_swaps = relationship("InterestRateSwap", back_populates="swaps", uselist=False)
    currency_swaps = relationship("CurrencySwap", back_populates="swaps", uselist=False)
    swap_legs = relationship("SwapLeg", back_populates="swaps", uselist=False)
    def __repr__(self):
        return f"<Swap(id={self.id}, type={self.swap_type}, pv={self.present_value})>"







