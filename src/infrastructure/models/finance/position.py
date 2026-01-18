"""
Infrastructure model for position.
SQLAlchemy model for domain position entity.
"""
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from src.infrastructure.models import ModelBase as Base
from src.domain.entities.finance.holding.position import PositionType


class PositionModel(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quantity = Column(Integer, nullable=False)
    position_type = Column(SQLEnum(PositionType), nullable=False)
    
    def __init__(self, quantity: int, position_type: PositionType):
        self.quantity = quantity
        self.position_type = position_type
    
    def __repr__(self):
        return f"<Position(id={self.id}, quantity={self.quantity}, position_type={self.position_type})>"