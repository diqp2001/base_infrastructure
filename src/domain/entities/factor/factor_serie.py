"""
Price data domain entity for factor calculations.
"""

from typing import List, Optional
from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class FactorSerie:
    """
    Domain entity representing price data for factor calculations.
    
    This class encapsulates price information extracted from the database
    and provides a clean interface for factor calculations.
    """
    values: List[float]
    dates: List[date]
    ticker: str
    entity_id: int
    
    def __post_init__(self):
        """Validate value data consistency."""
        if len(self.values) != len(self.dates):
            raise ValueError("values and dates lists must have the same length")
        
        if not self.values:
            raise ValueError("value data cannot be empty")
    
    def get_historical_values(self, lookback_periods: Optional[int] = None) -> List[float]:
        """
        Get historical values, optionally limited to a specific number of periods.
        
        Args:
            lookback_periods: Number of periods to look back (None for all values)
            
        Returns:
            List of historical values
        """
        if lookback_periods is None:
            return self.values
        
        return self.values[-lookback_periods:] if len(self.values) >= lookback_periods else self.values
    
    def get_historical_values_by_date_range(self, current_date: date, period_delta: timedelta) -> List[float]:
        """
        Get historical values within a specific date range from current_date.
        
        Args:
            current_date: The reference date for the calculation
            period_delta: Time delta to look back from current_date
            
        Returns:
            List of historical values within the date range
        """
        start_date = current_date - period_delta
        
        historical_values = []
        for i, value_date in enumerate(self.dates):
            if start_date <= value_date <= current_date:
                historical_values.append(self.values[i])
        
        return historical_values
    
    def get_historical_dates_and_values(self, current_date: date, period_delta: timedelta) -> tuple[List[date], List[float]]:
        """
        Get historical dates and values within a specific date range from current_date.
        
        Args:
            current_date: The reference date for the calculation
            period_delta: Time delta to look back from current_date
            
        Returns:
            Tuple of (dates, values) within the date range
        """
        start_date = current_date - period_delta
        
        historical_dates = []
        historical_values = []
        for i, value_date in enumerate(self.dates):
            if start_date <= value_date <= current_date:
                historical_dates.append(value_date)
                historical_values.append(self.values[i])
        
        return historical_dates, historical_values
    
    def get_latest_values(self) -> float:
        """Get the most recent value."""
        return self.values[-1] if self.values else 0.0
    
    def get_value_at_date(self, target_date: date) -> Optional[float]:
        """
        Get value at a specific date.
        
        Args:
            target_date: Date to get value for
            
        Returns:
            value at the date or None if not found
        """
        try:
            index = self.dates.index(target_date)
            return self.values[index]
        except ValueError:
            return None
    
    def get_date_range(self) -> tuple[date, date]:
        """Get the date range of the value data."""
        return (min(self.dates), max(self.dates)) if self.dates else (None, None)
    
    def __len__(self) -> int:
        """Return the number of value observations."""
        return len(self.values)