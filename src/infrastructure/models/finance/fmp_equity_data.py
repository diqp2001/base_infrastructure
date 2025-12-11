"""
SQLAlchemy ORM model for FMP Equity Data.
Maps to domain entity FmpEquityData following DDD principles.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, BigInteger
)
from src.infrastructure.models import ModelBase as Base


class FmpEquityDataModel(Base):
    """
    SQLAlchemy ORM model for FMP Equity Data.
    Stores equity data retrieved from Financial Modeling Prep API.
    """
    __tablename__ = "fmp_equity_data"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Primary identifiers
    symbol = Column(String(20), nullable=False, index=True)
    
    # Market data - using Numeric for precision with financial data
    price = Column(Numeric(20, 8), nullable=True)
    change = Column(Numeric(20, 8), nullable=True)
    changes_percentage = Column(Numeric(10, 4), nullable=True)
    day_low = Column(Numeric(20, 8), nullable=True)
    day_high = Column(Numeric(20, 8), nullable=True)
    year_high = Column(Numeric(20, 8), nullable=True)
    year_low = Column(Numeric(20, 8), nullable=True)
    market_cap = Column(Numeric(25, 2), nullable=True)  # Larger for market cap values
    price_avg_50 = Column(Numeric(20, 8), nullable=True)
    price_avg_200 = Column(Numeric(20, 8), nullable=True)
    volume = Column(BigInteger, nullable=True)  # Volume can be very large
    avg_volume = Column(BigInteger, nullable=True)
    
    # Company information
    exchange = Column(String(20), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    
    # Fundamental data
    pe = Column(Numeric(10, 4), nullable=True)  # P/E ratio
    eps = Column(Numeric(10, 4), nullable=True)  # Earnings per share
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<FmpEquityDataModel(symbol={self.symbol}, "
            f"price={self.price}, timestamp={self.timestamp})>"
        )