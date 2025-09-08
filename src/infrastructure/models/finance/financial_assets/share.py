"""
ORM model for CompanyShare - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Share(Base):
    """
    SQLAlchemy ORM model for Share.
    Completely separate from domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'shares'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    exchange = relationship("Exchange", back_populates="shares") 

    def __repr__(self):
        return f"<Share(id={self.id}, ticker={self.ticker})>"