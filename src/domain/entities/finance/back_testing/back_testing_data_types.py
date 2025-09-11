"""
Domain entities for back testing data types.
Pure domain entities following DDD principles.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from .enums import TickType, DataType
from .symbol import Symbol


@dataclass
class Bar:
    """Represents OHLC bar data."""
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    
    def __post_init__(self):
        """Validate bar data integrity."""
        if not all(isinstance(x, (Decimal, int, float)) for x in [self.open, self.high, self.low, self.close]):
            raise ValueError("All OHLC values must be numeric")
        
        # Convert to Decimal for precision
        self.open = Decimal(str(self.open))
        self.high = Decimal(str(self.high))
        self.low = Decimal(str(self.low))
        self.close = Decimal(str(self.close))
        
        # Validate OHLC relationships
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("Invalid OHLC relationships: high must be >= max(open,close) and low must be <= min(open,close)")


class BackTestingBaseData(ABC):
    """Abstract base class for all market data."""
    
    def __init__(self, symbol: Symbol, time: datetime, data_type: DataType):
        self.symbol = symbol
        self.time = time
        self.data_type = data_type
        self._value: Optional[Decimal] = None
    
    @property
    def value(self) -> Decimal:
        """Get the primary value of this data point."""
        return self._value or self.price
    
    @value.setter
    def value(self, val: Union[Decimal, float, int]):
        """Set the primary value of this data point."""
        self._value = Decimal(str(val))
    
    @property
    def end_time(self) -> datetime:
        """Get the end time of this data point."""
        return self.time
    
    @property
    @abstractmethod
    def price(self) -> Decimal:
        """Get the price value of this data point."""
        pass
    
    def clone(self) -> "BackTestingBaseData":
        """Create a deep copy of this data point."""
        # This would need to be implemented by subclasses
        raise NotImplementedError("Subclasses must implement clone method")


class TradeBar(BackTestingBaseData):
    """Represents OHLCV trade bar data."""
    
    def __init__(self, symbol: Symbol, time: datetime, open_price: Decimal, high: Decimal, 
                 low: Decimal, close: Decimal, volume: int, period: timedelta = None):
        super().__init__(symbol, time, DataType.TRADE_BAR)
        self.open = Decimal(str(open_price))
        self.high = Decimal(str(high))
        self.low = Decimal(str(low))
        self.close = Decimal(str(close))
        self.volume = volume
        self.period = period or timedelta(minutes=1)
        
        # Validate OHLC relationships
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("Invalid OHLC relationships")
    
    @property
    def price(self) -> Decimal:
        """Returns the close price as the primary price."""
        return self.close
    
    @property
    def end_time(self) -> datetime:
        """Get the end time of this trade bar."""
        return self.time + self.period
    
    def clone(self) -> 'TradeBar':
        """Create a deep copy of this trade bar."""
        return TradeBar(
            symbol=self.symbol,
            time=self.time,
            open_price=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            period=self.period
        )


class QuoteBar(BackTestingBaseData):
    """Represents bid/ask quote bar data."""
    
    def __init__(self, symbol: Symbol, time: datetime, bid: Bar = None, ask: Bar = None,
                 last_bid_size: int = 0, last_ask_size: int = 0, period: timedelta = None):
        super().__init__(symbol, time, DataType.QUOTE_BAR)
        self.bid = bid
        self.ask = ask
        self.last_bid_size = last_bid_size
        self.last_ask_size = last_ask_size
        self.period = period or timedelta(minutes=1)
    
    @property
    def price(self) -> Decimal:
        """Returns the mid price between bid and ask."""
        if self.bid and self.ask:
            return (self.bid.close + self.ask.close) / 2
        elif self.bid:
            return self.bid.close
        elif self.ask:
            return self.ask.close
        else:
            return Decimal('0')
    
    @property
    def end_time(self) -> datetime:
        """Get the end time of this quote bar."""
        return self.time + self.period
    
    def clone(self) -> 'QuoteBar':
        """Create a deep copy of this quote bar."""
        return QuoteBar(
            symbol=self.symbol,
            time=self.time,
            bid=self.bid,
            ask=self.ask,
            last_bid_size=self.last_bid_size,
            last_ask_size=self.last_ask_size,
            period=self.period
        )


class Tick(BackTestingBaseData):
    """Represents individual tick data."""
    
    def __init__(self, symbol: Symbol, time: datetime, tick_type: TickType, 
                 quantity: int = 0, exchange: str = "", sale_condition: str = "",
                 suspicious: bool = False, bid_price: Decimal = None, 
                 ask_price: Decimal = None, bid_size: int = 0, ask_size: int = 0):
        super().__init__(symbol, time, DataType.TICK)
        self.tick_type = tick_type
        self.quantity = quantity
        self.exchange = exchange
        self.sale_condition = sale_condition
        self.suspicious = suspicious
        self.bid_price = Decimal(str(bid_price)) if bid_price else None
        self.ask_price = Decimal(str(ask_price)) if ask_price else None
        self.bid_size = bid_size
        self.ask_size = ask_size
    
    @property
    def price(self) -> Decimal:
        """Returns the appropriate price based on tick type."""
        if self.tick_type == TickType.TRADE:
            return self.value or Decimal('0')
        elif self.tick_type == TickType.QUOTE:
            if self.bid_price and self.ask_price:
                return (self.bid_price + self.ask_price) / 2
            return self.bid_price or self.ask_price or Decimal('0')
        return self.value or Decimal('0')
    
    def clone(self) -> 'Tick':
        """Create a deep copy of this tick."""
        return Tick(
            symbol=self.symbol,
            time=self.time,
            tick_type=self.tick_type,
            quantity=self.quantity,
            exchange=self.exchange,
            sale_condition=self.sale_condition,
            suspicious=self.suspicious,
            bid_price=self.bid_price,
            ask_price=self.ask_price,
            bid_size=self.bid_size,
            ask_size=self.ask_size
        )


class Slice:
    """Organizes market data by symbol for a specific point in time."""
    
    def __init__(self, time: datetime):
        self.time = time
        self.data: Dict[Symbol, BackTestingBaseData] = {}
        self.bars: Dict[Symbol, TradeBar] = {}
        self.quote_bars: Dict[Symbol, QuoteBar] = {}
        self.ticks: Dict[Symbol, List[Tick]] = {}
    
    def add_data(self, data: BackTestingBaseData):
        """Add data to the slice."""
        self.data[data.symbol] = data
        
        if isinstance(data, TradeBar):
            self.bars[data.symbol] = data
        elif isinstance(data, QuoteBar):
            self.quote_bars[data.symbol] = data
        elif isinstance(data, Tick):
            if data.symbol not in self.ticks:
                self.ticks[data.symbol] = []
            self.ticks[data.symbol].append(data)
    
    def get(self, symbol: Symbol) -> Optional[BackTestingBaseData]:
        """Get data for a specific symbol."""
        return self.data.get(symbol)
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Check if slice contains data for a symbol."""
        return symbol in self.data
    
    def keys(self) -> List[Symbol]:
        """Get all symbols in this slice."""
        return list(self.data.keys())
    
    def values(self) -> List[BackTestingBaseData]:
        """Get all data values in this slice."""
        return list(self.data.values())
    
    def items(self) -> List[tuple]:
        """Get all symbol-data pairs in this slice."""
        return list(self.data.items())


@dataclass
class SubscriptionDataConfig:
    """Configuration for data subscriptions."""
    symbol: Symbol
    data_type: DataType
    resolution: str
    time_zone: str
    market: str
    fill_forward: bool = True
    extended_market_hours: bool = False
    is_custom_data: bool = False
    data_normalization_mode: str = "Adjusted"
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.symbol:
            raise ValueError("Symbol is required")
        if not self.resolution:
            raise ValueError("Resolution is required")


@dataclass 
class DataFeedPacket:
    """Represents a packet of market data from a data feed."""
    security: 'Security'  # Forward reference
    data: List[BackTestingBaseData]
    configuration: SubscriptionDataConfig
    is_universe_selection: bool = False


@dataclass
class MarketDataPoint:
    """Represents a single point of market data with metadata."""
    symbol: Symbol
    time: datetime
    price: Decimal
    volume: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    data_type: DataType = DataType.TRADE_BAR
    
    def __post_init__(self):
        """Ensure price precision."""
        self.price = Decimal(str(self.price))
        if self.bid:
            self.bid = Decimal(str(self.bid))
        if self.ask:
            self.ask = Decimal(str(self.ask))