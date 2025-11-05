"""
SQLAlchemy ORM models for Security factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class SecurityFactor(Base):
    """
    SQLAlchemy ORM model for Security factors.
    """
    __tablename__ = 'security_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("SecurityFactorValue", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SecurityFactor(id={self.id}, name={self.name}, group={self.group})>"


class SecurityFactorValue(Base):
    """
    SQLAlchemy ORM model for Security factor values.
    """
    __tablename__ = 'security_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('security_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('securities.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("SecurityFactor", back_populates="factor_values")
    entity = relationship("Security")

    def __repr__(self):
        return f"<SecurityFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


