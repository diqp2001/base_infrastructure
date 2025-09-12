from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

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
    swaps = relationship("Swap", back_populates="interest_rate_swaps")

    def __repr__(self):
        return f"<InterestRateSwap(id={self.id}, fixed_rate={self.fixed_rate}, floating={self.floating_reference})>"
