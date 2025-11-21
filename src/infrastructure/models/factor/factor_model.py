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
    entity_type = Column(String(50), nullable=False, index=True)  # For clarity and querying

    # Geographic factor columns
    continent_code = Column(String(10), nullable=True)
    geographic_zone = Column(String(50), nullable=True)
    country_code = Column(String(10), nullable=True)
    currency = Column(String(10), nullable=True)
    is_developed = Column(String(10), nullable=True)  # 'true'/'false' string

    # Financial asset columns
    asset_class = Column(String(50), nullable=True)
    market = Column(String(100), nullable=True)
    security_type = Column(String(50), nullable=True)
    isin = Column(String(20), nullable=True)
    cusip = Column(String(20), nullable=True)

    # Equity/Share specific columns
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap_category = Column(String(20), nullable=True)
    ticker_symbol = Column(String(20), nullable=True)
    share_class = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)

    # Share factor specialized columns
    period = Column(Integer, nullable=True)
    momentum_type = Column(String(50), nullable=True)
    indicator_type = Column(String(50), nullable=True)
    smoothing_factor = Column(Float, nullable=True)
    target_type = Column(String(50), nullable=True)
    forecast_horizon = Column(Integer, nullable=True)
    is_scaled = Column(String(10), nullable=True)  # 'true'/'false' string
    scaling_method = Column(String(50), nullable=True)
    volatility_type = Column(String(50), nullable=True)
    annualization_factor = Column(Float, nullable=True)

    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type
    }



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

class BondFactor(FactorModel):
    """Bond-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'bond'}

class CommodityFactor(FactorModel):
    """Commodity-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'commodity'}

class CompanyShareFactor(FactorModel):
    """Company-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'company'}

class CurrencyFactor(FactorModel):
    """CurrencyFactor-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'currency'}

class ETFShareFactor(FactorModel):
    """ETFShare-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'ETF'}

class FuturesFactor(FactorModel):
    """Futures-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'futures'}

class IndexFactor(FactorModel):
    """index-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'index'}

class OptionsFactor(FactorModel):
    """Option-specific factor."""
    __mapper_args__ = {'polymorphic_identity': 'option'}

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
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 8), nullable=False)

    # Relationships
    factor = relationship("FactorModel", back_populates="factor_values")

    def __repr__(self):
        return f"<FactorValue(id={self.id}, factor_id={self.factor_id}, entity_id={self.entity_id}, entity_type={self.entity_type}, date={self.date}, value={self.value})>"


