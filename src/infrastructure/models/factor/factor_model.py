"""
Generic SQLAlchemy ORM models for Factor entities with discriminator support.
These are base models used by the BaseFactorRepository.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class Factor(Base):
    """
    Unified SQLAlchemy ORM model for factors with discriminator column.
    This is used as a base model in the BaseFactorRepository.
    Supports polymorphic inheritance for different factor types.
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
        'polymorphic_on': factor_type
    }

    # Relationships
    factor_values = relationship("FactorValue", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Factor(id={self.id}, factor_type={self.factor_type}, name={self.name}, group={self.group})>"


# Polymorphic factor subclasses
class FinancialAssetFactor(Factor):
    """Base financial asset factor."""
    __mapper_args__ = {'polymorphic_identity': 'financial_asset'}


class SecurityFactor(Factor):
    """Security-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'security'}


class EquityFactor(Factor):
    """Equity-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'equity'}


class ShareFactor(Factor):
    """Share-specific factor."""
    equity_specific = Column(String(100), nullable=True)  # e.g. "return", "volatility"
    __mapper_args__ = {'polymorphic_identity': 'share'}


class ShareMomentumFactor(Factor):
    """Share momentum factor with period parameter."""
    period = Column(Integer, nullable=True)  # Time period for momentum calculation
    __mapper_args__ = {'polymorphic_identity': 'share_momentum'}


class ShareTechnicalFactor(Factor):
    """Share technical indicator factor."""
    indicator_type = Column(String(50), nullable=True)  # e.g., 'RSI', 'Bollinger', 'Stochastic'
    period = Column(Integer, nullable=True)  # Period for technical calculation
    __mapper_args__ = {'polymorphic_identity': 'share_technical'}


class ShareTargetFactor(Factor):
    """Share target variable factor for model training."""
    target_type = Column(String(50), nullable=True)  # 'target_returns', 'target_returns_nonscaled'
    forecast_horizon = Column(Integer, nullable=True)  # number of periods ahead to predict
    is_scaled = Column(String(10), default='true')  # whether target is normalized/scaled
    __mapper_args__ = {'polymorphic_identity': 'share_target'}


class ShareVolatilityFactor(Factor):
    """Share volatility factor."""
    volatility_type = Column(String(50), nullable=True)  # 'daily_vol', 'monthly_vol', 'vol_of_vol', 'realized_vol'
    period = Column(Integer, nullable=True)  # window size for volatility calculation
    annualization_factor = Column(Float, nullable=True)  # e.g., sqrt(252) for annualizing
    __mapper_args__ = {'polymorphic_identity': 'share_volatility'}


class CountryFactor(Factor):
    """Country-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'country'}


class ContinentFactor(Factor):
    """Continent-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'continent'}


class FactorValue(Base):
    """
    Generic SQLAlchemy ORM model for factor values with entity type tracking.
    This is used as a base model in the BaseFactorRepository.
    """
    __tablename__ = 'factor_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Generic entity reference
    entity_type = Column(String(50), nullable=False, index=True)  # For clarity and querying
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("Factor", back_populates="factor_values")

    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, entity_type={self.entity_type}, date={self.date}, value={self.value})>"


