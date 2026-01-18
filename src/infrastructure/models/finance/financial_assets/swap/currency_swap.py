


from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base



class CurrencySwapModel(Base):
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
    swaps = relationship("Swap", back_populates="currency_swaps")

    def __repr__(self):
        return f"<CurrencySwap(id={self.id}, {self.base_currency}/{self.quote_currency}, rate={self.initial_exchange_rate})>"