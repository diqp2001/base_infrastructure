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
    
    # Status
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=False)
    start_date = Column(Date, nullable=True)

    def __repr__(self):
        return f"<Index(id={self.id}, symbol={self.symbol}, name={self.name})>"