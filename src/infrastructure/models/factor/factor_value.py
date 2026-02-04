"""
Infrastructure model for factor value.
SQLAlchemy model for domain factor value entity.
"""
from datetime import date
from sqlalchemy import Column, DateTime, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FactorValueModel(Base):
    __tablename__ = 'factor_values'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey("factors.id"), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Generic entity reference
    date = Column(DateTime(timezone=True), nullable=False)
    value = Column(String(255), nullable=False)
    
    # Relationships
    factors = relationship("src.infrastructure.models.factor.factor.FactorModel",back_populates="factor_values")
    
    

    
    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date})>"