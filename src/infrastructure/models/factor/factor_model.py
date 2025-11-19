"""
Generic SQLAlchemy ORM models for Factor entities with discriminator support.
These are base models used by the BaseFactorRepository.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FactorModel(Base):
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

    # Additional columns for specialized factor types (nullable for base factors)
    # Geographic factors
    continent_code = Column(String(5), nullable=True)  # ContinentFactor
    geographic_zone = Column(String(50), nullable=True)  # ContinentFactor
    country_code = Column(String(2), nullable=True)  # CountryFactor
    is_developed = Column(String(10), nullable=True)  # CountryFactor
    
    # Financial asset factors
    asset_class = Column(String(50), nullable=True)  # FinancialAssetFactor
    market = Column(String(100), nullable=True)  # FinancialAssetFactor
    currency = Column(String(3), nullable=True)  # FinancialAssetFactor, CountryFactor
    
    # Security factors
    security_type = Column(String(50), nullable=True)  # SecurityFactor
    isin = Column(String(12), nullable=True)  # SecurityFactor
    cusip = Column(String(9), nullable=True)  # SecurityFactor
    
    # Equity factors
    sector = Column(String(100), nullable=True)  # EquityFactor
    industry = Column(String(100), nullable=True)  # EquityFactor
    market_cap_category = Column(String(20), nullable=True)  # EquityFactor
    
    # Share factors
    ticker_symbol = Column(String(10), nullable=True, index=True)  # ShareFactor
    share_class = Column(String(10), nullable=True)  # ShareFactor
    exchange = Column(String(20), nullable=True)  # ShareFactor
    
    # Share momentum factors
    period = Column(Integer, nullable=True)  # ShareMomentumFactor, ShareTechnicalFactor, ShareVolatilityFactor
    momentum_type = Column(String(20), nullable=True)  # ShareMomentumFactor
    
    # Share technical factors
    indicator_type = Column(String(30), nullable=True)  # ShareTechnicalFactor
    smoothing_factor = Column(Float, nullable=True)  # ShareTechnicalFactor
    
    # Share target factors
    target_type = Column(String(20), nullable=True)  # ShareTargetFactor
    forecast_horizon = Column(Integer, nullable=True)  # ShareTargetFactor
    is_scaled = Column(String(10), nullable=True)  # ShareTargetFactor
    scaling_method = Column(String(20), nullable=True)  # ShareTargetFactor
    
    # Share volatility factors
    volatility_type = Column(String(20), nullable=True)  # ShareVolatilityFactor
    annualization_factor = Column(Float, nullable=True)  # ShareVolatilityFactor

    # Relationships
    factor_values = relationship("FactorValue", back_populates="factor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Factor(id={self.id}, factor_type={self.factor_type}, name={self.name}, group={self.group})>"


# Polymorphic factor subclasses - all inherit from FactorModel with specialized columns

class ContinentFactor(FactorModel):
    """Continent-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'continent'}


class CountryFactor(FactorModel):
    """Country-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'country'}


class FinancialAssetFactor(FactorModel):
    """Base financial asset factor."""
    __mapper_args__ = {'polymorphic_identity': 'financial_asset'}


class SecurityFactor(FactorModel):
    """Security-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'security'}


class EquityFactor(FactorModel):
    """Equity-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'equity'}


class ShareFactor(FactorModel):
    """Share-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'share'}


class ShareMomentumFactor(FactorModel):
    """Share momentum factor with period parameter."""
    __mapper_args__ = {'polymorphic_identity': 'share_momentum'}


class ShareTechnicalFactor(FactorModel):
    """Share technical indicator factor."""
    __mapper_args__ = {'polymorphic_identity': 'share_technical'}


class ShareTargetFactor(FactorModel):
    """Share target variable factor for model training."""
    __mapper_args__ = {'polymorphic_identity': 'share_target'}


class ShareVolatilityFactor(FactorModel):
    """Share volatility factor."""
    __mapper_args__ = {'polymorphic_identity': 'share_volatility'}


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


