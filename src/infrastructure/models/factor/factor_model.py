"""
Unified SQLAlchemy ORM models for Factor entities using polymorphic inheritance.
All factor types are consolidated into a single 'factors' table with a discriminator column.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Factor(Base):
    """
    Unified SQLAlchemy ORM model for all factors using polymorphic inheritance.
    All factor types (bond, equity, currency, etc.) are stored in this single table.
    """
    __tablename__ = 'factors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_type = Column(String(50), nullable=False, index=True)  # Discriminator column
    name = Column(String(255), nullable=False, index=True)
    group = Column(String(100), nullable=False)
    subgroup = Column(String(100), nullable=True)
    data_type = Column(String(50), default='numeric')
    source = Column(String(100), nullable=True)
    definition = Column(Text, nullable=True)

    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type,
        'with_polymorphic': '*'
    }

    # Relationships
    factor_values = relationship("FactorValue", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Factor(id={self.id}, type={self.factor_type}, name={self.name}, group={self.group})>"


class FactorValue(Base):
    """
    Unified SQLAlchemy ORM model for all factor values.
    All factor value types are stored in this single table with entity type tracking.
    """
    __tablename__ = 'factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Generic entity reference
    entity_type = Column(String(50), nullable=True, index=True)  # Track entity type for clarity
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("Factor", back_populates="factor_values")

    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, entity_type={self.entity_type}, date={self.date}, value={self.value})>"


# Polymorphic factor subclasses for specific asset types
class BondFactor(Factor):
    """Bond-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'bond'}


class CompanyShareFactor(Factor):
    """Company share-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'company_share'}


class EquityFactor(Factor):
    """Equity-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'equity'}


class CurrencyFactor(Factor):
    """Currency-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'currency'}


class CommodityFactor(Factor):
    """Commodity-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'commodity'}


class ETFShareFactor(Factor):
    """ETF share-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'etf_share'}


class FuturesFactor(Factor):
    """Futures-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'futures'}


class IndexFactor(Factor):
    """Index-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'index'}


class OptionsFactor(Factor):
    """Options-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'options'}


class SecurityFactor(Factor):
    """Security-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'security'}


class ShareFactor(Factor):
    """Share-specific factor model using polymorphic inheritance."""
    __mapper_args__ = {'polymorphic_identity': 'share'}


