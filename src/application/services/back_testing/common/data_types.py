"""
Core data types for market data handling.
Based on QuantConnect's data structure patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from .symbol import Symbol
from .enums import MarketDataType, TickType


@dataclass
class BaseData:
    """
    Base class for all market data types.
    All market data must inherit from this class.
    """
    symbol: Symbol
    time: datetime
    end_time: datetime
    value: float = 0.0
    data_type: MarketDataType = MarketDataType.BASE
    
    def __post_init__(self):
        if self.end_time is None:
            self.end_time = self.time
    
    @property
    def price(self) -> float:
        """Alias for value - the most representative price for this data"""
        return self.value


@dataclass
class TradeBar(BaseData):
    """
    Represents aggregated trade data over a time period (OHLCV)
    """
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    data_type: MarketDataType = field(default=MarketDataType.TRADE_BAR, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # Set value to close price by default
        if self.value == 0.0:
            self.value = self.close
    
    @property
    def price(self) -> float:
        """Returns the close price"""
        return self.close
    
    def update(self, time: datetime, price: float, volume: int):
        """Updates the trade bar with new trade data"""
        if not hasattr(self, '_initialized') or not self._initialized:
            self.open = self.high = self.low = self.close = price
            self._initialized = True
        else:
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            self.close = price
        
        self.volume += volume
        self.time = time
        self.value = self.close


@dataclass
class QuoteBar(BaseData):
    """
    Represents aggregated quote data over a time period (bid/ask OHLC)
    """
    # Bid data
    bid_open: float = 0.0
    bid_high: float = 0.0
    bid_low: float = 0.0
    bid_close: float = 0.0
    bid_size: int = 0
    
    # Ask data
    ask_open: float = 0.0
    ask_high: float = 0.0
    ask_low: float = 0.0
    ask_close: float = 0.0
    ask_size: int = 0
    
    data_type: MarketDataType = field(default=MarketDataType.QUOTE_BAR, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # Set value to mid-price by default
        if self.value == 0.0 and self.bid_close > 0 and self.ask_close > 0:
            self.value = (self.bid_close + self.ask_close) / 2.0
    
    @property
    def price(self) -> float:
        """Returns the mid price between bid and ask"""
        if self.bid_close > 0 and self.ask_close > 0:
            return (self.bid_close + self.ask_close) / 2.0
        return self.bid_close if self.bid_close > 0 else self.ask_close
    
    @property
    def spread(self) -> float:
        """Returns the bid-ask spread"""
        return self.ask_close - self.bid_close if self.ask_close > self.bid_close else 0.0


@dataclass
class Tick(BaseData):
    """
    Represents individual tick data (trade or quote)
    """
    quantity: int = 0
    exchange: str = ""
    sale_condition: str = ""
    suspicious: bool = False
    tick_type: TickType = TickType.TRADE
    
    # Bid/Ask specific fields
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    
    data_type: MarketDataType = field(default=MarketDataType.TICK, init=False)
    
    @property
    def price(self) -> float:
        """Returns the most appropriate price for this tick"""
        if self.tick_type == TickType.TRADE:
            return self.value
        elif self.tick_type == TickType.QUOTE:
            return (self.bid_price + self.ask_price) / 2.0 if self.bid_price > 0 and self.ask_price > 0 else self.value
        return self.value


class TradeBars(Dict[Symbol, TradeBar]):
    """
    Collection of TradeBar objects keyed by Symbol
    """
    def __init__(self, data: Optional[Dict[Symbol, TradeBar]] = None):
        super().__init__(data or {})
    
    def get_value(self, symbol: Symbol) -> Optional[float]:
        """Gets the close price for a symbol"""
        bar = self.get(symbol)
        return bar.close if bar else None
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Checks if symbol exists in the collection"""
        return symbol in self


class QuoteBars(Dict[Symbol, QuoteBar]):
    """
    Collection of QuoteBar objects keyed by Symbol
    """
    def __init__(self, data: Optional[Dict[Symbol, QuoteBar]] = None):
        super().__init__(data or {})
    
    def get_value(self, symbol: Symbol) -> Optional[float]:
        """Gets the mid price for a symbol"""
        bar = self.get(symbol)
        return bar.price if bar else None
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Checks if symbol exists in the collection"""
        return symbol in self


class Ticks(Dict[Symbol, List[Tick]]):
    """
    Collection of Tick lists keyed by Symbol
    """
    def __init__(self, data: Optional[Dict[Symbol, List[Tick]]] = None):
        super().__init__(data or {})
    
    def get_value(self, symbol: Symbol) -> Optional[float]:
        """Gets the most recent tick price for a symbol"""
        ticks = self.get(symbol, [])
        return ticks[-1].price if ticks else None


@dataclass
class Slice:
    """
    Container for all market data at a specific time point.
    This is the main data structure passed to OnData() method.
    """
    time: datetime
    
    # Data collections
    bars: TradeBars = field(default_factory=TradeBars)
    quote_bars: QuoteBars = field(default_factory=QuoteBars)
    ticks: Ticks = field(default_factory=Ticks)
    
    # Additional data
    splits: Dict[Symbol, Any] = field(default_factory=dict)
    dividends: Dict[Symbol, Any] = field(default_factory=dict)
    delisting: Dict[Symbol, Any] = field(default_factory=dict)
    symbol_changed_events: Dict[Symbol, Any] = field(default_factory=dict)
    
    # Custom data storage
    _data: Dict[str, Any] = field(default_factory=dict)
    
    def __getitem__(self, symbol: Union[Symbol, str]) -> Optional[BaseData]:
        """Gets data for a symbol, trying different data types"""
        if isinstance(symbol, str):
            # Try to find symbol by string value
            for sym in self.bars.keys():
                if sym.value == symbol:
                    symbol = sym
                    break
            else:
                return None
        
        # Try bars first, then quote bars, then ticks
        if symbol in self.bars:
            return self.bars[symbol]
        elif symbol in self.quote_bars:
            return self.quote_bars[symbol]
        elif symbol in self.ticks and self.ticks[symbol]:
            return self.ticks[symbol][-1]  # Return most recent tick
        
        return None
    
    def __contains__(self, symbol: Union[Symbol, str]) -> bool:
        """Checks if data exists for a symbol"""
        if isinstance(symbol, str):
            # Try to find symbol by string value
            for sym in self.bars.keys():
                if sym.value == symbol:
                    symbol = sym
                    break
            else:
                return False
        
        return (symbol in self.bars or 
                symbol in self.quote_bars or 
                symbol in self.ticks)
    
    def get(self, symbol: Union[Symbol, str], default=None) -> Optional[BaseData]:
        """Gets data for a symbol with default fallback"""
        try:
            return self[symbol] or default
        except (KeyError, TypeError):
            return default
    
    def keys(self):
        """Returns all symbols in this slice"""
        all_symbols = set()
        all_symbols.update(self.bars.keys())
        all_symbols.update(self.quote_bars.keys())
        all_symbols.update(self.ticks.keys())
        return all_symbols
    
    def values(self):
        """Returns all data values in this slice"""
        for bar in self.bars.values():
            yield bar
        for quote_bar in self.quote_bars.values():
            yield quote_bar
        for tick_list in self.ticks.values():
            for tick in tick_list:
                yield tick
    
    def items(self):
        """Returns all symbol-data pairs in this slice"""
        for symbol, bar in self.bars.items():
            yield symbol, bar
        for symbol, quote_bar in self.quote_bars.items():
            yield symbol, quote_bar
        for symbol, tick_list in self.ticks.items():
            for tick in tick_list:
                yield symbol, tick
    
    @property
    def has_data(self) -> bool:
        """Returns True if this slice contains any data"""
        return bool(self.bars or self.quote_bars or self.ticks)