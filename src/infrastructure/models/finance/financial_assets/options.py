"""
ORM model for Options - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base
import enum


class OptionType(enum.Enum):
    CALL = "call"
    PUT = "put"


class OptionsModel(Base):
    """
    SQLAlchemy ORM model for Options.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'options'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True, unique=True)
    underlying_ticker = Column(String(20), nullable=False, index=True)
    option_type = Column(SQLEnum(OptionType), nullable=False)
    
    # Option contract details
    strike_price = Column(Numeric(15, 4), nullable=False)
    expiration_date = Column(Date, nullable=False)
    contract_size = Column(Integer, nullable=False, default=100)  # Shares per contract
    
    # Market data fields
    current_price = Column(Numeric(15, 4), default=0)
    bid_price = Column(Numeric(15, 4), nullable=True)
    ask_price = Column(Numeric(15, 4), nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Greeks
    delta = Column(Numeric(8, 6), nullable=True)
    gamma = Column(Numeric(8, 6), nullable=True)
    theta = Column(Numeric(8, 6), nullable=True)
    vega = Column(Numeric(8, 6), nullable=True)
    rho = Column(Numeric(8, 6), nullable=True)
    
    # Volatility and pricing
    implied_volatility = Column(Numeric(8, 4), nullable=True)
    theoretical_value = Column(Numeric(15, 4), nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    is_american = Column(Boolean, default=True)  # American vs European style
    days_to_expiration = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Options(id={self.id}, symbol={self.symbol}, type={self.option_type})>"