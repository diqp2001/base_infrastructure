"""
SQLAlchemy ORM models for ETF Share factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class ETFShareFactor(Base):
    """
    SQLAlchemy ORM model for ETF Share factors.
    """
    __tablename__ = 'etf_share_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("ETFShareFactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("ETFShareFactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ETFShareFactor(id={self.id}, name={self.name}, group={self.group})>"


class ETFShareFactorValue(Base):
    """
    SQLAlchemy ORM model for ETF Share factor values.
    """
    __tablename__ = 'etf_share_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('etf_share_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('etf_shares.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("ETFShareFactor", back_populates="factor_values")
    entity = relationship("ETFShare")

    def __repr__(self):
        return f"<ETFShareFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class ETFShareFactorRule(Base):
    """
    SQLAlchemy ORM model for ETF Share factor rules.
    """
    __tablename__ = 'etf_share_factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('etf_share_factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("ETFShareFactor", back_populates="factor_rules")

    def __repr__(self):
        return f"<ETFShareFactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"