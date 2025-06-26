"""
Core data types for market data representation.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from decimal import Decimal
from dataclasses import dataclass

from .enums import Resolution, TickType, DataType
from .symbol import Symbol


@dataclass
class BaseData(ABC):
    """
    Abstract base class for all market data types.
    Provides common properties and methods for all data.
    """
    symbol: Symbol
    time: datetime
    value: Decimal
    data_type: DataType
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.value, Decimal):
            self.value = Decimal(str(self.value))
    
    @property
    def end_time(self) -> datetime:
        """Gets the end time of this data."""
        return self.time
    
    @property
    def price(self) -> Decimal:
        """Gets the price of this data point."""
        return self.value
    
    def clone(self) -> 'BaseData':
        """Create a deep copy of this data point."""
        return self.__class__(
            symbol=self.symbol,
            time=self.time,
            value=self.value,
            data_type=self.data_type
        )


@dataclass
class TradeBar(BaseData):
    """
    Represents a trade bar (OHLCV) data point.
    Contains open, high, low, close prices and volume.
    """
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    period: Optional[Resolution] = None
    
    def __post_init__(self):
        super().__post_init__()
        # Convert all price fields to Decimal
        self.open = Decimal(str(self.open))
        self.high = Decimal(str(self.high))
        self.low = Decimal(str(self.low))
        self.close = Decimal(str(self.close))
        # Value is typically the close price for trade bars
        self.value = self.close
        self.data_type = DataType.TRADE_BAR
    
    @property
    def price(self) -> Decimal:
        """Gets the price (close) of this trade bar."""
        return self.close
    
    def clone(self) -> 'TradeBar':
        """Create a deep copy of this trade bar."""
        return TradeBar(
            symbol=self.symbol,
            time=self.time,
            value=self.value,
            data_type=self.data_type,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            period=self.period
        )


@dataclass
class QuoteBar(BaseData):
    """
    Represents a quote bar (bid/ask OHLC) data point.
    Contains bid and ask open, high, low, close prices.
    """
    bid: Optional['Bar'] = None
    ask: Optional['Bar'] = None
    last_bid_size: int = 0
    last_ask_size: int = 0
    period: Optional[Resolution] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.data_type = DataType.QUOTE_BAR
        # Value is typically the mid-price
        if self.bid and self.ask:
            self.value = (self.bid.close + self.ask.close) / 2
        elif self.bid:
            self.value = self.bid.close
        elif self.ask:
            self.value = self.ask.close
    
    @property
    def price(self) -> Decimal:
        """Gets the mid-price of this quote bar."""
        return self.value
    
    def clone(self) -> 'QuoteBar':
        """Create a deep copy of this quote bar."""
        return QuoteBar(
            symbol=self.symbol,
            time=self.time,
            value=self.value,
            data_type=self.data_type,
            bid=self.bid.clone() if self.bid else None,
            ask=self.ask.clone() if self.ask else None,
            last_bid_size=self.last_bid_size,
            last_ask_size=self.last_ask_size,
            period=self.period
        )


@dataclass
class Bar:
    """
    Represents OHLC data (used within QuoteBar for bid/ask).
    """
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    
    def __post_init__(self):
        # Convert all price fields to Decimal
        self.open = Decimal(str(self.open))
        self.high = Decimal(str(self.high))
        self.low = Decimal(str(self.low))
        self.close = Decimal(str(self.close))
    
    def clone(self) -> 'Bar':
        """Create a deep copy of this bar."""
        return Bar(
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close
        )


@dataclass
class Tick(BaseData):
    """
    Represents a single tick data point.
    Contains individual trade or quote information.
    """
    tick_type: TickType
    quantity: int = 0
    exchange: str = ""
    sale_condition: str = ""
    suspicious: bool = False
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_size: int = 0
    ask_size: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.data_type = DataType.TICK
        if self.bid_price is not None:
            self.bid_price = Decimal(str(self.bid_price))
        if self.ask_price is not None:
            self.ask_price = Decimal(str(self.ask_price))
    
    @property
    def price(self) -> Decimal:
        """Gets the price of this tick."""
        return self.value
    
    def clone(self) -> 'Tick':
        """Create a deep copy of this tick."""
        return Tick(
            symbol=self.symbol,
            time=self.time,
            value=self.value,
            data_type=self.data_type,
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
    """
    Contains all market data for a specific point in time.
    Organizes data by symbol and provides easy access methods.
    """
    
    def __init__(self, time: datetime, data: Optional[Dict[Symbol, List[BaseData]]] = None):
        self.time = time
        self.data = data or {}
        
        # Organize data by type for easy access
        self.bars: Dict[Symbol, TradeBar] = {}
        self.quote_bars: Dict[Symbol, QuoteBar] = {}
        self.ticks: Dict[Symbol, List[Tick]] = {}
        
        # Process the input data
        if data:
            self._organize_data()
    
    def _organize_data(self) -> None:
        """Organize data by type for efficient access."""
        for symbol, data_list in self.data.items():
            for data_point in data_list:
                if isinstance(data_point, TradeBar):
                    self.bars[symbol] = data_point
                elif isinstance(data_point, QuoteBar):
                    self.quote_bars[symbol] = data_point
                elif isinstance(data_point, Tick):
                    if symbol not in self.ticks:
                        self.ticks[symbol] = []
                    self.ticks[symbol].append(data_point)
    
    def get(self, symbol: Symbol, data_type: type = None) -> Optional[BaseData]:
        """
        Get data for a specific symbol and optionally a specific data type.
        """
        if symbol not in self.data:
            return None
        
        data_list = self.data[symbol]
        if not data_list:
            return None
        
        if data_type is None:
            return data_list[0]  # Return first available data
        
        for data_point in data_list:
            if isinstance(data_point, data_type):
                return data_point
        
        return None
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Check if the slice contains data for the specified symbol."""
        return symbol in self.data and len(self.data[symbol]) > 0
    
    def keys(self) -> List[Symbol]:
        """Get all symbols that have data in this slice."""
        return list(self.data.keys())
    
    def values(self) -> List[BaseData]:
        """Get all data points in this slice."""
        all_data = []
        for data_list in self.data.values():
            all_data.extend(data_list)
        return all_data
    
    def get_all_data(self) -> List[BaseData]:
        """Get all data points in this slice."""
        return self.values()
    
    def has_data(self) -> bool:
        """Check if this slice has any data."""
        return len(self.data) > 0
    
    def __getitem__(self, symbol: Symbol) -> Optional[BaseData]:
        """Allow dictionary-style access to data."""
        return self.get(symbol)
    
    def __contains__(self, symbol: Symbol) -> bool:
        """Allow 'in' operator to check for symbol presence."""
        return self.contains_key(symbol)
    
    def __len__(self) -> int:
        """Return the number of symbols with data."""
        return len(self.data)
    
    def __str__(self) -> str:
        """String representation of the slice."""
        symbol_count = len(self.data)
        total_points = sum(len(data_list) for data_list in self.data.values())
        return f"Slice({self.time}, {symbol_count} symbols, {total_points} data points)"


@dataclass
class SubscriptionDataConfig:
    """
    Configuration for data subscriptions.
    Contains all parameters needed to request data for a specific symbol.
    """
    symbol: Symbol
    data_type: type
    resolution: Resolution
    time_zone: str = "UTC"
    market: str = "USA"
    fill_forward: bool = True
    extended_market_hours: bool = False
    is_internal_feed: bool = False
    is_custom_data: bool = False
    price_scale_factor: Decimal = Decimal('1.0')
    data_normalization_mode: str = "Raw"
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.price_scale_factor, Decimal):
            self.price_scale_factor = Decimal(str(self.price_scale_factor))
    
    @property
    def sid(self) -> str:
        """Gets the subscription ID (unique identifier)."""
        return f"{self.symbol}_{self.data_type.__name__}_{self.resolution.value}"
    
    def clone(self) -> 'SubscriptionDataConfig':
        """Create a deep copy of this configuration."""
        return SubscriptionDataConfig(
            symbol=self.symbol,
            data_type=self.data_type,
            resolution=self.resolution,
            time_zone=self.time_zone,
            market=self.market,
            fill_forward=self.fill_forward,
            extended_market_hours=self.extended_market_hours,
            is_internal_feed=self.is_internal_feed,
            is_custom_data=self.is_custom_data,
            price_scale_factor=self.price_scale_factor,
            data_normalization_mode=self.data_normalization_mode
        )