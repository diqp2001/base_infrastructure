"""
Time utilities for handling time zones, market hours, and date/time operations.
"""

from datetime import datetime, timedelta, timezone, time
from typing import Dict, Optional, List
import pytz
from dataclasses import dataclass


class Time:
    """
    Static utility class for time operations and conversions.
    Handles time zone conversions and market hour calculations.
    """
    
    # Common time zones used in financial markets
    UTC = pytz.UTC
    NEW_YORK = pytz.timezone("America/New_York")
    CHICAGO = pytz.timezone("America/Chicago")
    LONDON = pytz.timezone("Europe/London")
    TOKYO = pytz.timezone("Asia/Tokyo")
    SYDNEY = pytz.timezone("Australia/Sydney")
    
    @staticmethod
    def now(time_zone: Optional[pytz.BaseTzInfo] = None) -> datetime:
        """Get current time in specified time zone (UTC by default)."""
        if time_zone is None:
            return datetime.now(Time.UTC)
        return datetime.now(time_zone)
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC time."""
        return datetime.now(Time.UTC)
    
    @staticmethod
    def convert_to_utc(dt: datetime, source_tz: pytz.BaseTzInfo) -> datetime:
        """Convert datetime from source timezone to UTC."""
        if dt.tzinfo is None:
            dt = source_tz.localize(dt)
        return dt.astimezone(Time.UTC)
    
    @staticmethod
    def convert_from_utc(dt: datetime, target_tz: pytz.BaseTzInfo) -> datetime:
        """Convert datetime from UTC to target timezone."""
        if dt.tzinfo is None:
            dt = Time.UTC.localize(dt)
        return dt.astimezone(target_tz)
    
    @staticmethod
    def to_time_zone(dt: datetime, time_zone: pytz.BaseTzInfo) -> datetime:
        """Convert datetime to specified time zone."""
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = Time.UTC.localize(dt)
        return dt.astimezone(time_zone)
    
    @staticmethod
    def parse_date_time(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S",
                       time_zone: Optional[pytz.BaseTzInfo] = None) -> datetime:
        """Parse date string to datetime with optional timezone."""
        dt = datetime.strptime(date_str, format_str)
        if time_zone:
            dt = time_zone.localize(dt)
        return dt
    
    @staticmethod
    def get_start_of_day(dt: datetime) -> datetime:
        """Get start of day (00:00:00) for the given datetime."""
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_end_of_day(dt: datetime) -> datetime:
        """Get end of day (23:59:59.999999) for the given datetime."""
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    @staticmethod
    def get_previous_trading_day(dt: datetime) -> datetime:
        """Get the previous trading day (skip weekends)."""
        prev_day = dt - timedelta(days=1)
        
        # Skip weekends (Saturday = 5, Sunday = 6)
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)
        
        return prev_day
    
    @staticmethod
    def get_next_trading_day(dt: datetime) -> datetime:
        """Get the next trading day (skip weekends)."""
        next_day = dt + timedelta(days=1)
        
        # Skip weekends (Saturday = 5, Sunday = 6)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        
        return next_day
    
    @staticmethod
    def is_trading_day(dt: datetime) -> bool:
        """Check if the given date is a trading day (weekday)."""
        return dt.weekday() < 5  # Monday=0, Friday=4
    
    @staticmethod
    def round_down(dt: datetime, minutes: int) -> datetime:
        """Round datetime down to the nearest specified minutes."""
        rounded_minute = (dt.minute // minutes) * minutes
        return dt.replace(minute=rounded_minute, second=0, microsecond=0)
    
    @staticmethod
    def round_up(dt: datetime, minutes: int) -> datetime:
        """Round datetime up to the nearest specified minutes."""
        if dt.minute % minutes == 0 and dt.second == 0 and dt.microsecond == 0:
            return dt
        
        rounded_minute = ((dt.minute // minutes) + 1) * minutes
        if rounded_minute >= 60:
            return dt.replace(hour=dt.hour + 1, minute=0, second=0, microsecond=0)
        else:
            return dt.replace(minute=rounded_minute, second=0, microsecond=0)


@dataclass
class MarketHours:
    """
    Represents market trading hours for a specific exchange.
    """
    market_open: time
    market_close: time
    time_zone: pytz.BaseTzInfo
    pre_market_open: Optional[time] = None
    post_market_close: Optional[time] = None
    
    def is_market_hours(self, dt: datetime) -> bool:
        """Check if the given datetime is within regular market hours."""
        # Convert to market timezone
        market_time = Time.to_time_zone(dt, self.time_zone).time()
        return self.market_open <= market_time <= self.market_close
    
    def is_extended_hours(self, dt: datetime) -> bool:
        """Check if the given datetime is within extended hours."""
        market_time = Time.to_time_zone(dt, self.time_zone).time()
        
        # Check pre-market
        if self.pre_market_open and self.pre_market_open <= market_time < self.market_open:
            return True
        
        # Check post-market
        if self.post_market_close and self.market_close < market_time <= self.post_market_close:
            return True
        
        return False
    
    def is_market_open(self, dt: datetime) -> bool:
        """Check if the market is open at the given datetime."""
        return self.is_market_hours(dt) or self.is_extended_hours(dt)
    
    def get_market_open_time(self, date: datetime) -> datetime:
        """Get the market open datetime for a specific date."""
        market_date = Time.to_time_zone(date, self.time_zone).date()
        market_open_dt = datetime.combine(market_date, self.market_open)
        return self.time_zone.localize(market_open_dt)
    
    def get_market_close_time(self, date: datetime) -> datetime:
        """Get the market close datetime for a specific date."""
        market_date = Time.to_time_zone(date, self.time_zone).date()
        market_close_dt = datetime.combine(market_date, self.market_close)
        return self.time_zone.localize(market_close_dt)


class MarketHoursDatabase:
    """
    Database of market hours for different exchanges and security types.
    """
    
    def __init__(self):
        self._market_hours: Dict[str, MarketHours] = {}
        self._initialize_default_hours()
    
    def _initialize_default_hours(self):
        """Initialize with common market hours."""
        
        # US Equity Markets (NYSE, NASDAQ)
        self._market_hours["USA_EQUITY"] = MarketHours(
            market_open=time(9, 30),
            market_close=time(16, 0),
            time_zone=Time.NEW_YORK,
            pre_market_open=time(4, 0),
            post_market_close=time(20, 0)
        )
        
        # Forex (24/5 market)
        self._market_hours["FOREX"] = MarketHours(
            market_open=time(0, 0),
            market_close=time(23, 59, 59),
            time_zone=Time.UTC
        )
        
        # Crypto (24/7 market)
        self._market_hours["CRYPTO"] = MarketHours(
            market_open=time(0, 0),
            market_close=time(23, 59, 59),
            time_zone=Time.UTC
        )
        
        # London Stock Exchange
        self._market_hours["EUROPE_EQUITY"] = MarketHours(
            market_open=time(8, 0),
            market_close=time(16, 30),
            time_zone=Time.LONDON
        )
        
        # Tokyo Stock Exchange
        self._market_hours["ASIA_EQUITY"] = MarketHours(
            market_open=time(9, 0),
            market_close=time(15, 0),
            time_zone=Time.TOKYO
        )
    
    def get_market_hours(self, market: str, security_type: str = "EQUITY") -> Optional[MarketHours]:
        """Get market hours for a specific market and security type."""
        key = f"{market.upper()}_{security_type.upper()}"
        
        # Try exact match first
        if key in self._market_hours:
            return self._market_hours[key]
        
        # Try security type only (for global markets like FOREX, CRYPTO)
        if security_type.upper() in self._market_hours:
            return self._market_hours[security_type.upper()]
        
        # Default to US equity hours if no match
        return self._market_hours.get("USA_EQUITY")
    
    def add_market_hours(self, market: str, security_type: str, market_hours: MarketHours):
        """Add custom market hours."""
        key = f"{market.upper()}_{security_type.upper()}"
        self._market_hours[key] = market_hours
    
    def is_market_open(self, market: str, security_type: str, dt: datetime) -> bool:
        """Check if a specific market is open at the given datetime."""
        market_hours = self.get_market_hours(market, security_type)
        if market_hours is None:
            return False
        
        # Check if it's a trading day
        if not Time.is_trading_day(dt):
            # Forex and crypto markets are open on weekends
            if security_type.upper() not in ["FOREX", "CRYPTO"]:
                return False
        
        return market_hours.is_market_open(dt)


# Global market hours database
_market_hours_db = MarketHoursDatabase()


def get_market_hours_database() -> MarketHoursDatabase:
    """Get the global market hours database."""
    return _market_hours_db


class TradingCalendar:
    """
    Trading calendar that handles holidays and special trading days.
    """
    
    def __init__(self, market: str):
        self.market = market.upper()
        self._holidays: List[datetime] = []
        self._early_closes: Dict[datetime, time] = {}
        self._initialize_holidays()
    
    def _initialize_holidays(self):
        """Initialize with common market holidays."""
        # This is simplified - in a real implementation, you'd load from a comprehensive holiday database
        current_year = datetime.now().year
        
        if self.market == "USA":
            # Add some common US holidays (simplified)
            self._holidays.extend([
                datetime(current_year, 1, 1),   # New Year's Day
                datetime(current_year, 7, 4),   # Independence Day
                datetime(current_year, 12, 25), # Christmas Day
            ])
    
    def is_holiday(self, dt: datetime) -> bool:
        """Check if the given date is a market holiday."""
        date_only = dt.date()
        return any(holiday.date() == date_only for holiday in self._holidays)
    
    def is_early_close(self, dt: datetime) -> bool:
        """Check if the given date has an early market close."""
        date_only = dt.date()
        return any(early_date.date() == date_only for early_date in self._early_closes.keys())
    
    def get_early_close_time(self, dt: datetime) -> Optional[time]:
        """Get the early close time for the given date."""
        date_only = dt.date()
        for early_date, close_time in self._early_closes.items():
            if early_date.date() == date_only:
                return close_time
        return None
    
    def is_trading_day(self, dt: datetime) -> bool:
        """Check if the given date is a valid trading day."""
        return (Time.is_trading_day(dt) and 
                not self.is_holiday(dt))
    
    def add_holiday(self, dt: datetime):
        """Add a custom holiday."""
        if dt not in self._holidays:
            self._holidays.append(dt)
    
    def add_early_close(self, dt: datetime, close_time: time):
        """Add a custom early close."""
        self._early_closes[dt] = close_time