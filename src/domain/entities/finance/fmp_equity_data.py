"""
Domain entity for FMP (Financial Modeling Prep) Equity Data.
Represents financial data retrieved from FMP API for equity securities.
"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import datetime


@dataclass
class FmpEquityData:
    """
    Domain entity representing equity data from Financial Modeling Prep API.
    Contains both market data and fundamental information.
    """
    
    # Primary identifiers
    id: Optional[int] = None
    symbol: str = ""
    
    # Market data
    price: Optional[Decimal] = None
    change: Optional[Decimal] = None
    changes_percentage: Optional[Decimal] = None
    day_low: Optional[Decimal] = None
    day_high: Optional[Decimal] = None
    year_high: Optional[Decimal] = None
    year_low: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    price_avg_50: Optional[Decimal] = None
    price_avg_200: Optional[Decimal] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    
    # Company information
    exchange: Optional[str] = None
    name: Optional[str] = None
    
    # Fundamental data
    pe: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    
    # Timestamps
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation and processing."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def __str__(self):
        return f"FmpEquityData(symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})"
    
    def __repr__(self):
        return (
            f"FmpEquityData(id={self.id}, symbol='{self.symbol}', "
            f"price={self.price}, market_cap={self.market_cap})"
        )