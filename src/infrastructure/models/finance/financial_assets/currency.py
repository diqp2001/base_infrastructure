"""
ORM model for Currency - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Currency(Base):
    """
    SQLAlchemy ORM model for Currency.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    Enhanced with country relationship and exchange rate management.
    """
    __tablename__ = 'currencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    iso_code = Column(String(3), nullable=False, unique=True, index=True)  # ISO 4217 code
    
    # Country relationship
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=True, index=True)
    
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
    
    # Relationships
    country = relationship("Country", back_populates="currencies")

    def __repr__(self):
        return f"<Currency(id={self.id}, iso_code={self.iso_code}, name={self.name}, country_id={self.country_id})>"


class CurrencyRate(Base):
    """
    SQLAlchemy ORM model for historical currency exchange rates.
    Stores time-series data for currency exchange rates.
    """
    __tablename__ = 'currency_rates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_id = Column(Integer, ForeignKey('currencies.id'), nullable=False, index=True)
    rate = Column(Numeric(15, 8), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    target_currency = Column(String(3), default="USD", nullable=False)  # Usually USD
    
    # Relationships
    currency = relationship("Currency", backref="historical_rates")

    def __repr__(self):
        return f"<CurrencyRate(id={self.id}, currency_id={self.currency_id}, rate={self.rate}, timestamp={self.timestamp}, target={self.target_currency})>"