"""
SQLAlchemy ORM models for Bond factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class BondFactor(Base):
    """
    SQLAlchemy ORM model for Bond factors.
    """
    __tablename__ = 'bond_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("BondFactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("BondFactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BondFactor(id={self.id}, name={self.name}, group={self.group})>"


class BondFactorValue(Base):
    """
    SQLAlchemy ORM model for Bond factor values.
    """
    __tablename__ = 'bond_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('bond_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('bonds.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("BondFactor", back_populates="factor_values")
    entity = relationship("Bond")

    def __repr__(self):
        return f"<BondFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class BondFactorRule(Base):
    """
    SQLAlchemy ORM model for Bond factor rules.
    """
    __tablename__ = 'bond_factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('bond_factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("BondFactor", back_populates="factor_rules")

    def __repr__(self):
        return f"<BondFactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"