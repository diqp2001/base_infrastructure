"""
Infrastructure model for factor value.
SQLAlchemy model for domain factor value entity.
"""
from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FactorValueModel(Base):
    __tablename__ = 'factor_values'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey("factors.id"), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Generic entity reference
    date = Column(Date, nullable=False)
    value = Column(String(255), nullable=False)
    
    # Relationships
    factor = relationship("Factor")
    
    def __init__(self, factor_id: int, entity_id: int, date: date, value: str):
        self.factor_id = factor_id
        self.entity_id = entity_id
        self.date = date
        self.value = value
    
    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date})>"