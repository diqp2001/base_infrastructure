"""
ORM model for Index - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Index(Base):
    """
    SQLAlchemy ORM model for Index.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'indices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Index-specific fields
    index_type = Column(String(50), nullable=False)  # Stock, Bond, Commodity, etc.
    weighting_method = Column(String(50), nullable=True)  # Market cap, Equal, Price weighted
    base_value = Column(Numeric(15, 4), nullable=True)
    base_date = Column(Date, nullable=True)
    currency = Column(String(3), nullable=False, default='USD')
    
    # Composition
    total_constituents = Column(Integer, nullable=True)
    rebalancing_frequency = Column(String(50), nullable=True)  # Monthly, Quarterly, etc.
    
    # Market data fields
    current_value = Column(Numeric(15, 4), default=0)
    previous_close = Column(Numeric(15, 4), nullable=True)
    daily_change = Column(Numeric(10, 4), nullable=True)
    daily_change_percent = Column(Numeric(5, 4), nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Performance metrics
    ytd_return = Column(Numeric(10, 4), nullable=True)
    one_year_return = Column(Numeric(10, 4), nullable=True)
    three_year_return = Column(Numeric(10, 4), nullable=True)
    five_year_return = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=False)  # Indices are typically not directly tradeable
    is_active = Column(Boolean, default=True)
    creation_date = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Index(id={self.id}, symbol={self.symbol}, name={self.name})>"