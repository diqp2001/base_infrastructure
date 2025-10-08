"""
SQLAlchemy ORM models for Options factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class OptionsFactor(Base):
    """
    SQLAlchemy ORM model for Options factors.
    """
    __tablename__ = 'options_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("OptionsFactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("OptionsFactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OptionsFactor(id={self.id}, name={self.name}, group={self.group})>"


class OptionsFactorValue(Base):
    """
    SQLAlchemy ORM model for Options factor values.
    """
    __tablename__ = 'options_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('options_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('options.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("OptionsFactor", back_populates="factor_values")
    entity = relationship("Options")

    def __repr__(self):
        return f"<OptionsFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class OptionsFactorRule(Base):
    """
    SQLAlchemy ORM model for Options factor rules.
    """
    __tablename__ = 'options_factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('options_factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("OptionsFactor", back_populates="factor_rules")

    def __repr__(self):
        return f"<OptionsFactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"