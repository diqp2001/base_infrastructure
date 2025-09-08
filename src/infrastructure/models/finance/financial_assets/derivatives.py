"""
ORM model for Derivatives - separate from domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class UnderlyingAsset(Base):
    """
    SQLAlchemy ORM model for Underlying Asset.
    Represents the asset that a derivative is based on.
    """
    __tablename__ = 'underlying_assets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Asset identification
    symbol = Column(String(20), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # 'STOCK', 'INDEX', 'COMMODITY', etc.
    
    # Pricing
    current_price = Column(Numeric(20, 8), nullable=True)
    last_price_update = Column(DateTime, nullable=True)
    
    # Additional info
    currency = Column(String(3), nullable=False, default='USD')
    exchange = Column(String(50), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    derivatives = relationship("Derivative", back_populates="underlying_asset")

    def __repr__(self):
        return f"<UnderlyingAsset(id={self.id}, symbol={self.symbol}, type={self.asset_type}, price={self.current_price})>"


class Derivative(Base):
    """
    SQLAlchemy ORM model for Derivative securities.
    Base class for all derivative instruments.
    """
    __tablename__ = 'derivatives'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Symbol information
    ticker = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    security_type = Column(String(50), nullable=False)  # 'option', 'future', 'swap', etc.
    derivative_type = Column(String(50), nullable=True)  # More specific type
    
    # Underlying asset
    underlying_asset_id = Column(Integer, ForeignKey('underlying_assets.id'), nullable=False)
    
    # Contract details
    expiration_date = Column(Date, nullable=False)
    contract_size = Column(Numeric(15, 4), nullable=False, default=1)
    
    # Pricing and valuation
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    intrinsic_value = Column(Numeric(20, 8), nullable=True, default=0)
    time_value = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Time-related metrics
    days_to_expiry = Column(Integer, nullable=True)
    time_to_expiry_years = Column(Numeric(10, 6), nullable=True)  # For calculations
    
    # Trading properties
    is_tradeable = Column(Boolean, default=True)
    is_expired = Column(Boolean, default=False)
    is_exercised = Column(Boolean, default=False)
    is_assigned = Column(Boolean, default=False)
    
    # Holdings information
    holdings_quantity = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_average_cost = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_market_value = Column(Numeric(20, 8), nullable=True, default=0)
    holdings_unrealized_pnl = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Risk metrics
    leverage = Column(Numeric(15, 4), nullable=True)
    margin_requirement_rate = Column(Numeric(5, 4), nullable=True, default=0.2)  # 20%
    
    # Greeks (for options-like derivatives)
    delta = Column(Numeric(10, 6), nullable=True)
    gamma = Column(Numeric(10, 6), nullable=True)
    theta = Column(Numeric(10, 6), nullable=True)
    vega = Column(Numeric(10, 6), nullable=True)
    rho = Column(Numeric(10, 6), nullable=True)
    
    # Volatility metrics
    implied_volatility = Column(Numeric(10, 6), nullable=True)
    historical_volatility = Column(Numeric(10, 6), nullable=True)
    
    # Moneyness and classification
    moneyness = Column(String(10), nullable=True)  # 'ITM', 'OTM', 'ATM'
    moneyness_value = Column(Numeric(10, 6), nullable=True)  # Numeric moneyness
    
    # Market data cache (JSON)
    market_data_cache = Column(Text, nullable=True)
    
    # Status and timestamps
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_valuation_date = Column(DateTime, nullable=True)
    expiration_processed = Column(Boolean, default=False)

    # Relationships
    underlying_asset = relationship("UnderlyingAsset", back_populates="derivatives")

    def __repr__(self):
        return f"<Derivative(id={self.id}, ticker={self.ticker}, type={self.security_type}, exp={self.expiration_date})>"