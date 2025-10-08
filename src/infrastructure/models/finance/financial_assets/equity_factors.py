"""
SQLAlchemy ORM models for Equity factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class EquityFactor(Base):
    """
    SQLAlchemy ORM model for Equity factors.
    """
    __tablename__ = 'equity_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("EquityFactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("EquityFactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EquityFactor(id={self.id}, name={self.name}, group={self.group})>"


class EquityFactorValue(Base):
    """
    SQLAlchemy ORM model for Equity factor values.
    """
    __tablename__ = 'equity_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('equity_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('equities.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("EquityFactor", back_populates="factor_values")
    entity = relationship("Equity")

    def __repr__(self):
        return f"<EquityFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class EquityFactorRule(Base):
    """
    SQLAlchemy ORM model for Equity factor rules.
    """
    __tablename__ = 'equity_factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('equity_factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("EquityFactor", back_populates="factor_rules")

    def __repr__(self):
        return f"<EquityFactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"