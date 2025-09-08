"""
ORM model for Currency - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Currency(Base):
    """
    SQLAlchemy ORM model for Currency.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'currencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    iso_code = Column(String(3), nullable=False, unique=True, index=True)  # ISO 4217 code
    
    # Exchange rate data
    exchange_rate_to_usd = Column(Numeric(15, 8), default=1.0, nullable=False)
    last_rate_update = Column(DateTime, nullable=True)
    
    # Currency properties
    is_major_currency = Column(Boolean, default=False)  # Major currencies like USD, EUR, JPY
    is_crypto_currency = Column(Boolean, default=False)
    decimal_places = Column(Integer, default=2)  # Number of decimal places for the currency
    
    # Status fields
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Currency(id={self.id}, iso_code={self.iso_code}, name={self.name})>"