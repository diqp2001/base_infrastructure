"""
SecurityExchangeHours class for managing trading hours.
"""

from datetime import time, datetime
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class SecurityExchangeHours:
    """
    Defines the trading hours for a security exchange.
    """
    market_open: time = time(9, 30)  # 9:30 AM
    market_close: time = time(16, 0)  # 4:00 PM
    extended_market_hours: bool = False
    early_close_time: Optional[time] = None
    
    def is_market_open(self, current_time: datetime) -> bool:
        """
        Check if the market is open at the given time.
        
        Args:
            current_time: The time to check
            
        Returns:
            True if the market is open
        """
        current_time_of_day = current_time.time()
        
        # Check if it's a weekend
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if it's within regular trading hours
        if self.market_open <= current_time_of_day <= self.market_close:
            return True
        
        # Check extended hours if enabled
        if self.extended_market_hours:
            # Extended hours: 4:00 AM to 9:30 AM and 4:00 PM to 8:00 PM
            extended_pre_open = time(4, 0)
            extended_post_close = time(20, 0)
            
            if (extended_pre_open <= current_time_of_day < self.market_open or
                self.market_close < current_time_of_day <= extended_post_close):
                return True
        
        return False
    
    def get_next_market_open(self, current_time: datetime) -> datetime:
        """
        Get the next market open time.
        
        Args:
            current_time: The current time
            
        Returns:
            The next market open datetime
        """
        # Simple implementation - just return next day at market open
        # In reality, this would handle weekends and holidays
        next_day = current_time.replace(hour=self.market_open.hour, 
                                       minute=self.market_open.minute,
                                       second=0, microsecond=0)
        
        if next_day <= current_time:
            # If market open time has passed today, move to next day
            next_day = next_day.replace(day=next_day.day + 1)
        
        return next_day
    
    def get_next_market_close(self, current_time: datetime) -> datetime:
        """
        Get the next market close time.
        
        Args:
            current_time: The current time
            
        Returns:
            The next market close datetime
        """
        close_time = self.early_close_time if self.early_close_time else self.market_close
        
        next_close = current_time.replace(hour=close_time.hour,
                                         minute=close_time.minute,
                                         second=0, microsecond=0)
        
        if next_close <= current_time:
            # If market close time has passed today, move to next day
            next_close = next_close.replace(day=next_close.day + 1)
        
        return next_close