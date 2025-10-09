"""
SQLAlchemy ORM models for Share factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class ShareFactor(Base):
    """
    SQLAlchemy ORM model for Share factors.
    """
    __tablename__ = 'share_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("ShareFactorValue", back_populates="factor", cascade="all, delete-orphan")
    factor_rules = relationship("ShareFactorRule", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ShareFactor(id={self.id}, name={self.name}, group={self.group})>"


class ShareFactorValue(Base):
    """
    SQLAlchemy ORM model for Share factor values.
    """
    __tablename__ = 'share_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('share_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('shares.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("ShareFactor", back_populates="factor_values")
    entity = relationship("Share")

    def __repr__(self):
        return f"<ShareFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"


class ShareFactorRule(Base):
    """
    SQLAlchemy ORM model for Share factor rules.
    """
    __tablename__ = 'share_factor_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('share_factors.id'), nullable=False)
    condition = Column(Text, nullable=False)
    rule_type = Column(String(50), nullable=False)
    method_ref = Column(String(255), nullable=True)

    # Relationships
    factor = relationship("ShareFactor", back_populates="factor_rules")

    def __repr__(self):
        return f"<ShareFactorRule(id={self.id}, factor_id={self.factor_id}, rule_type={self.rule_type})>"