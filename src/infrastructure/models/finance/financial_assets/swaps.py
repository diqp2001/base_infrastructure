"""
ORM model for Swaps - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Swap(Base):
    """
    SQLAlchemy ORM model for Swap contracts.
    Completely separate from domain entity to avoid metaclass conflicts.
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
    interest_rate_swap = relationship("InterestRateSwap", back_populates="swap", uselist=False)
    currency_swap = relationship("CurrencySwap", back_populates="swap", uselist=False)

    def __repr__(self):
        return f"<Swap(id={self.id}, type={self.swap_type}, pv={self.present_value})>"


class SwapLeg(Base):
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
    swap = relationship("Swap", back_populates="legs")

    def __repr__(self):
        return f"<SwapLeg(id={self.id}, swap_id={self.swap_id}, type={self.leg_type}, rate={self.fixed_rate})>"


class InterestRateSwap(Base):
    """
    SQLAlchemy ORM model for Interest Rate Swap.
    """
    __tablename__ = 'interest_rate_swaps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    swap_id = Column(Integer, ForeignKey('swaps.id'), nullable=False, unique=True)
    
    # IRS-specific fields
    fixed_rate = Column(Numeric(10, 6), nullable=False)
    floating_reference = Column(String(20), nullable=False)  # 'LIBOR', 'SOFR', etc.
    notional_amount = Column(Numeric(20, 2), nullable=False)
    
    # Payment details
    payment_frequency = Column(String(20), nullable=False, default='quarterly')
    currency = Column(String(3), nullable=False, default='USD')
    
    # Valuation metrics
    par_rate = Column(Numeric(10, 6), nullable=True)  # Market rate for equivalent maturity
    swap_spread = Column(Numeric(10, 6), nullable=True)  # Spread over treasury
    z_spread = Column(Numeric(10, 6), nullable=True)
    
    # Relationship
    swap = relationship("Swap", back_populates="interest_rate_swap")

    def __repr__(self):
        return f"<InterestRateSwap(id={self.id}, fixed_rate={self.fixed_rate}, floating={self.floating_reference})>"


class CurrencySwap(Base):
    """
    SQLAlchemy ORM model for Currency Swap.
    """
    __tablename__ = 'currency_swaps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    swap_id = Column(Integer, ForeignKey('swaps.id'), nullable=False, unique=True)
    
    # Currency pair
    base_currency = Column(String(3), nullable=False)
    quote_currency = Column(String(3), nullable=False)
    
    # Notional amounts in respective currencies
    base_notional = Column(Numeric(20, 2), nullable=False)
    quote_notional = Column(Numeric(20, 2), nullable=False)
    
    # Interest rates for each leg
    base_rate = Column(Numeric(10, 6), nullable=False)
    quote_rate = Column(Numeric(10, 6), nullable=False)
    
    # Exchange rate information
    initial_exchange_rate = Column(Numeric(15, 8), nullable=False)
    current_exchange_rate = Column(Numeric(15, 8), nullable=True)
    
    # Principal exchange flags
    exchange_initial_principal = Column(Boolean, default=True)
    exchange_final_principal = Column(Boolean, default=True)
    
    # Payment frequencies for each leg
    base_payment_frequency = Column(String(20), nullable=False, default='quarterly')
    quote_payment_frequency = Column(String(20), nullable=False, default='quarterly')
    
    # Relationship
    swap = relationship("Swap", back_populates="currency_swap")

    def __repr__(self):
        return f"<CurrencySwap(id={self.id}, {self.base_currency}/{self.quote_currency}, rate={self.initial_exchange_rate})>"


# Add the legs relationship to Swap
Swap.legs = relationship("SwapLeg", back_populates="swap")