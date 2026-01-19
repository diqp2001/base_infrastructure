"""
ORM model for Commodity - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class CommodityModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Commodity.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'commodities'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    ticker = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    market = Column(String(50), nullable=False)  # e.g., 'NYMEX', 'COMEX', 'CBOT'
    
    # Commodity-specific fields
    commodity_type = Column(String(50), nullable=False)  # 'Energy', 'Metals', 'Agricultural', 'Livestock'
    unit_of_measure = Column(String(20), nullable=False)  # 'barrel', 'ounce', 'bushel', etc.
    contract_size = Column(Numeric(15, 4), nullable=True)  # Size of standard contract
    tick_size = Column(Numeric(10, 6), nullable=True)  # Minimum price increment
    
    # Pricing data
    current_price = Column(Numeric(15, 4), nullable=True, default=0)
    currency = Column(String(3), nullable=False, default='USD')
    price_per_unit = Column(Numeric(15, 4), nullable=True)
    
    # Market data
    daily_volume = Column(Numeric(20, 0), nullable=True)
    open_interest = Column(Numeric(20, 0), nullable=True)
    price_change_24h = Column(Numeric(10, 4), nullable=True)
    volatility_30d = Column(Numeric(10, 4), nullable=True)
    
    # Contract information
    spot_price = Column(Numeric(15, 4), nullable=True)
    front_month_contract = Column(String(20), nullable=True)
    delivery_months = Column(String(100), nullable=True)  # JSON string of available delivery months
    
    # Physical properties
    storage_cost_rate = Column(Numeric(5, 4), nullable=True)  # Annual storage cost as % of value
    transportation_cost = Column(Numeric(10, 4), nullable=True)
    quality_specifications = Column(String(500), nullable=True)  # Quality requirements
    
    # Status and timestamps
    is_tradeable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, nullable=True)
    listing_date = Column(Date, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "commodity",
    }

    def __repr__(self):
        return f"<Commodity(id={self.id}, ticker={self.ticker}, name={self.name}, price={self.current_price})>"