"""
ORM model for Futures - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
import enum


class FutureType(enum.Enum):
    COMMODITY = "commodity"
    BOND = "bond"
    INDEX = "index"
    CURRENCY = "currency"


class Futures(Base):
    """
    SQLAlchemy ORM model for Futures.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'futures'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True, unique=True)
    contract_name = Column(String(255), nullable=False)
    future_type = Column(SQLEnum(FutureType), nullable=False)
    underlying_asset = Column(String(100), nullable=False)
    
    # Contract specifications
    contract_size = Column(Numeric(15, 4), nullable=False)  # Units per contract
    contract_unit = Column(String(50), nullable=False)  # bushels, ounces, etc.
    expiration_date = Column(Date, nullable=False)
    delivery_month = Column(String(10), nullable=False)  # MAR25, JUN25, etc.
    settlement_type = Column(String(20), nullable=False, default='physical')  # physical or cash
    
    # Market data fields
    current_price = Column(Numeric(15, 4), default=0)
    settlement_price = Column(Numeric(15, 4), nullable=True)
    bid_price = Column(Numeric(15, 4), nullable=True)
    ask_price = Column(Numeric(15, 4), nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    daily_high = Column(Numeric(15, 4), nullable=True)
    daily_low = Column(Numeric(15, 4), nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Margin requirements
    initial_margin = Column(Numeric(15, 2), nullable=True)
    maintenance_margin = Column(Numeric(15, 2), nullable=True)
    
    # Price limits
    daily_price_limit_up = Column(Numeric(15, 4), nullable=True)
    daily_price_limit_down = Column(Numeric(15, 4), nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Exchange information
    exchange = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=False, default='USD')

    def __repr__(self):
        return f"<Futures(id={self.id}, symbol={self.symbol}, type={self.future_type})>"