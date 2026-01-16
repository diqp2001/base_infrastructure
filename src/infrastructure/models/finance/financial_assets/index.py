"""
ORM model for Index - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Index(Base):
    """
    SQLAlchemy ORM model for Index.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'indices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), default="USD")
    
    # Index calculation properties
    base_value = Column(Numeric(15, 4), nullable=True)
    base_date = Column(Date, nullable=True)
    index_type = Column(String(50), default="EQUITY")
    weighting_method = Column(String(50), default="MARKET_CAP")
    calculation_method = Column(String(50), default="CAPITALIZATION_WEIGHTED")
    
    # Market data
    current_level = Column(Numeric(15, 4), nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # IBKR-specific fields
    ibkr_contract_id = Column(Integer, nullable=True)
    ibkr_local_symbol = Column(String(50), nullable=True)
    ibkr_exchange = Column(String(20), nullable=True)
    ibkr_min_tick = Column(Numeric(10, 8), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=False)
    creation_date = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Index(id={self.id}, symbol={self.symbol}, name={self.name})>"