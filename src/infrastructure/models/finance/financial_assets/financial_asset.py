"""
ORM model for Financial Asset - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, Text
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base


class FinancialAsset(Base):
    """
    SQLAlchemy ORM model for Financial Asset base class.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'financial_assets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic asset information
    asset_type = Column(String(50), nullable=False, index=True)  # Discriminator for asset type
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Date information
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Asset classification
    category = Column(String(50), nullable=True)  # 'Equity', 'Fixed Income', 'Derivative', etc.
    sub_category = Column(String(50), nullable=True)  # More specific classification
    
    # Identification codes
    isin = Column(String(12), nullable=True, unique=True)  # International Securities Identification Number
    cusip = Column(String(9), nullable=True)  # Committee on Uniform Securities Identification Procedures
    sedol = Column(String(7), nullable=True)  # Stock Exchange Daily Official List
    ticker = Column(String(20), nullable=True, index=True)
    
    # Basic pricing
    current_price = Column(Numeric(20, 8), nullable=True, default=0)
    currency = Column(String(3), nullable=False, default='USD')
    
    # Market information
    market = Column(String(100), nullable=True)
    exchange = Column(String(100), nullable=True)
    country_code = Column(String(3), nullable=True)
    
    # Status fields
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=True)
    is_liquid = Column(Boolean, default=True)
    
    # Risk classification
    risk_rating = Column(String(10), nullable=True)  # 'LOW', 'MEDIUM', 'HIGH'
    credit_rating = Column(String(10), nullable=True)  # 'AAA', 'AA+', etc.
    
    # Regulatory information
    regulatory_status = Column(String(50), nullable=True)
    compliance_flags = Column(Text, nullable=True)  # JSON for various compliance flags
    
    # Performance metrics
    ytd_return = Column(Numeric(10, 4), nullable=True)
    one_year_return = Column(Numeric(10, 4), nullable=True)
    volatility = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    
    # Additional metadata
    financial_asset_metadata = Column(String(100), nullable=True)  # JSON for additional properties
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_price_update = Column(DateTime, nullable=True)

    # Relationships
    instruments = relationship("Instrument", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FinancialAsset(id={self.id}, type={self.asset_type}, ticker={self.ticker}, price={self.current_price})>"