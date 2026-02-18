"""
ORM model for Futures - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text
from sqlalchemy import ForeignKey, Enum as SQLEnum
import enum
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.derivative.future.future import FutureModel




class IndexFutureModel(FutureModel):
    """
    SQLAlchemy ORM model for Futures.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'index_futures'

    id = Column(Integer, ForeignKey("futures.id"), primary_key=True)
    
    
    
    __mapper_args__ = {
    "polymorphic_identity": "index_future",
}
    def __repr__(self):
        return f"<Futures(id={self.id}, symbol={self.symbol}>"