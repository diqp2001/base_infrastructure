"""
ORM model for Futures - separate from src.domain entity to avoid metaclass conflicts.
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


class FutureModel(Base):
    """
    SQLAlchemy ORM model for Futures.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'futures'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True, unique=True)
    contract_name = Column(String(255), nullable=False)
    future_type = Column(SQLEnum(FutureType), nullable=False)
    underlying_asset = Column(String(100), nullable=False)
    
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Exchange information
    #needs foreign keys here
    exchange = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=False, default='USD')

    def __repr__(self):
        return f"<Futures(id={self.id}, symbol={self.symbol}, type={self.future_type})>"