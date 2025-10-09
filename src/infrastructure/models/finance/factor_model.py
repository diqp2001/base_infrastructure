"""
Generic SQLAlchemy ORM models for Factor entities.
These are base models used by the BaseFactorRepository.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Factor(Base):
    """
    Generic SQLAlchemy ORM model for factors.
    This is used as a base model in the BaseFactorRepository.
    """
    __tablename__ = 'factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("FactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("FactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Factor(id={self.id}, name={self.name}, group={self.group})>"


class FactorValue(Base):
    """
    Generic SQLAlchemy ORM model for factor values.
    This is used as a base model in the BaseFactorRepository.
    """
    __tablename__ = 'factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Generic entity reference
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("Factor", back_populates="factor_values")

    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class FactorRule(Base):
    """
    Generic SQLAlchemy ORM model for factor rules.
    This is used as a base model in the BaseFactorRepository.
    """
    __tablename__ = 'factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("Factor", back_populates="factor_rules")

    def __repr__(self):
        return f"<FactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"