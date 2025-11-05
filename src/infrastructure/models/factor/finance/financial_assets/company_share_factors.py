"""
SQLAlchemy ORM models for Company Share factor entities.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class CompanyShareFactor(Base):
    """
    SQLAlchemy ORM model for Company Share factors.
    """
    __tablename__ = 'company_share_factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Relationships
    factor_values = relationship("CompanyShareFactorValue", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CompanyShareFactor(id={self.id}, name={self.name}, group={self.group})>"


class CompanyShareFactorValue(Base):
    """
    SQLAlchemy ORM model for Company Share factor values.
    """
    __tablename__ = 'company_share_factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('company_share_factors.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("CompanyShareFactor", back_populates="factor_values")
    entity = relationship("CompanyShare")

    def __repr__(self):
        return f"<CompanyShareFactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, date={self.date}, value={self.value})>"

