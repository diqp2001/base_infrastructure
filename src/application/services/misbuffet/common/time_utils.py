from datetime import datetime, time, timedelta
from typing import Dict, Tuple
from src.application.services.misbuffet.common.enums import Resolution


class Time:
    """
    Utility class for time management in backtesting and data processing.
    Provides helper methods for date arithmetic, alignment, and resolution-based adjustments.
    """

    def __init__(self):
        # Market hours database as instance variable
        self.market_hours_db: Dict[str, Tuple[time, time]] = {
            "NYSE": (time(9, 30), time(16, 0)),
            "NASDAQ": (time(9, 30), time(16, 0)),
            "BATS": (time(9, 30), time(16, 0)),
            "ARCA": (time(9, 30), time(16, 0)),
            "FXCM": (time(0, 0), time(23, 59)),
            "OANDA": (time(0, 0), time(23, 59)),
            "BINANCE": (time(0, 0), time(23, 59)),
            "BITFINEX": (time(0, 0), time(23, 59)),
            "COINBASE": (time(0, 0), time(23, 59)),
            "CME": (time(8, 30), time(15, 15)),
            "CBOT": (time(8, 30), time(15, 15)),
            "ICE": (time(8, 0), time(17, 0))
        }

    def now(self) -> datetime:
        """Returns the current system time."""
        return datetime.utcnow()

    def add_resolution(self, dt: datetime, resolution: Resolution, count: int = 1) -> datetime:
        """Adds a number of time units to a datetime based on resolution."""
        if resolution == Resolution.TICK:
            return dt
        elif resolution == Resolution.SECOND:
            return dt + timedelta(seconds=count)
        elif resolution == Resolution.MINUTE:
            return dt + timedelta(minutes=count)
        elif resolution == Resolution.HOUR:
            return dt + timedelta(hours=count)
        elif resolution == Resolution.DAILY:
            return dt + timedelta(days=count)
        elif resolution == Resolution.WEEKLY:
            return dt + timedelta(weeks=count)
        elif resolution == Resolution.MONTHLY:
            return dt + timedelta(days=30 * count)  # Approximation
        else:
            raise ValueError(f"Unsupported resolution: {resolution}")

    def start_of_day(self, dt: datetime) -> datetime:
        """Returns datetime aligned to the start of the day."""
        return datetime(dt.year, dt.month, dt.day)

    def end_of_day(self, dt: datetime) -> datetime:
        """Returns datetime aligned to the end of the day."""
        return datetime(dt.year, dt.month, dt.day, 23, 59, 59, 999999)

    def to_utc(self, dt: datetime) -> datetime:
        """Converts a naive datetime to UTC (if not already)."""
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(tz=None)

    def days_between(self, start: datetime, end: datetime) -> int:
        """Returns the number of days between two datetimes."""
        return (end - start).days

    def is_trading_day(self, dt: datetime) -> bool:
        """Checks if the given datetime falls on a trading day (Mon-Fri)."""
        return dt.weekday() < 5

    def floor_to_resolution(self, dt: datetime, resolution: Resolution) -> datetime:
        """Floors a datetime to the nearest resolution boundary."""
        if resolution == Resolution.DAILY:
            return self.start_of_day(dt)
        elif resolution == Resolution.HOUR:
            return datetime(dt.year, dt.month, dt.day, dt.hour)
        elif resolution == Resolution.MINUTE:
            return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
        elif resolution == Resolution.SECOND:
            return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        else:
            return dt

    def get_market_hours_database(self) -> Dict[str, Tuple[time, time]]:
        """Returns a copy of the market hours database."""
        return self.market_hours_db.copy()
