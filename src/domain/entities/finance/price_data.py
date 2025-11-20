"""
Price data domain entity for factor calculations.
"""

from typing import List, Optional
from datetime import date
from dataclasses import dataclass


@dataclass
class PriceData:
    """
    Domain entity representing price data for factor calculations.
    
    This class encapsulates price information extracted from the database
    and provides a clean interface for factor calculations.
    """
    prices: List[float]
    dates: List[date]
    ticker: str
    entity_id: int
    
    def __post_init__(self):
        """Validate price data consistency."""
        if len(self.prices) != len(self.dates):
            raise ValueError("Prices and dates lists must have the same length")
        
        if not self.prices:
            raise ValueError("Price data cannot be empty")
    
    def get_historical_prices(self, lookback_periods: Optional[int] = None) -> List[float]:
        """
        Get historical prices, optionally limited to a specific number of periods.
        
        Args:
            lookback_periods: Number of periods to look back (None for all prices)
            
        Returns:
            List of historical prices
        """
        if lookback_periods is None:
            return self.prices
        
        return self.prices[-lookback_periods:] if len(self.prices) >= lookback_periods else self.prices
    
    def get_latest_price(self) -> float:
        """Get the most recent price."""
        return self.prices[-1] if self.prices else 0.0
    
    def get_price_at_date(self, target_date: date) -> Optional[float]:
        """
        Get price at a specific date.
        
        Args:
            target_date: Date to get price for
            
        Returns:
            Price at the date or None if not found
        """
        try:
            index = self.dates.index(target_date)
            return self.prices[index]
        except ValueError:
            return None
    
    def get_date_range(self) -> tuple[date, date]:
        """Get the date range of the price data."""
        return (min(self.dates), max(self.dates)) if self.dates else (None, None)
    
    def __len__(self) -> int:
        """Return the number of price observations."""
        return len(self.prices)