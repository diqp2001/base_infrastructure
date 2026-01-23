"""
Market Data Service - Provides real-time and backtest market data slices.
Part of the DDD architecture for market data management.
"""

from datetime import datetime
from typing import Dict, List, Optional, Iterator, Callable, Any
from abc import ABC, abstractmethod

from ..common.data_types import Slice, BaseData, TradeBar, QuoteBar, Tick
from ..common.symbol import Symbol
from ..common.enums import Resolution
from ...data.entities.entity_service import EntityService
from .market_data_history_service import MarketDataHistoryService


class MarketDataProvider(ABC):
    """
    Abstract base class for different market data providers.
    Can be implemented for different data sources (files, APIs, etc.).
    """
    
    @abstractmethod
    def get_slice_data(self, time: datetime, symbols: List[Symbol]) -> Dict[Symbol, List[BaseData]]:
        """Get market data for specified symbols at a given time."""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the data provider."""
        pass
    
    @abstractmethod
    def dispose(self):
        """Clean up resources."""
        pass


class FileSystemMarketDataProvider(MarketDataProvider):
    """
    File system based market data provider for backtesting.
    """
    
    def __init__(self, data_folder: str):
        self.data_folder = data_folder
        self._initialized = False
        self._data_cache: Dict[str, List[BaseData]] = {}
    
    def initialize(self) -> bool:
        """Initialize the file system provider."""
        try:
            # In a real implementation, this would scan the data folder
            # and build an index of available data files
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing FileSystemMarketDataProvider: {e}")
            return False
    
    def get_slice_data(self, time: datetime, symbols: List[Symbol]) -> Dict[Symbol, List[BaseData]]:
        """Get data slice from file system."""
        if not self._initialized:
            return {}
        
        slice_data = {}
        
        for symbol in symbols:
            # In a real implementation, this would read from data files
            # For now, we'll return empty data or mock data
            try:
                # Mock implementation - replace with actual file reading
                bar_data = self._create_mock_bar_data(symbol, time)
                if bar_data:
                    slice_data[symbol] = [bar_data]
            except Exception as e:
                print(f"Error getting data for {symbol}: {e}")
        
        return slice_data
    
    def _create_mock_bar_data(self, symbol: Symbol, time: datetime) -> Optional[TradeBar]:
        """Create mock bar data for testing purposes."""
        # This is just for demonstration - replace with actual data reading
        return TradeBar(
            symbol=symbol,
            time=time,
            end_time=time,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=1000,
            value=101.0
        )
    
    def dispose(self):
        """Clean up resources."""
        self._data_cache.clear()


class LiveMarketDataProvider(MarketDataProvider):
    """
    Live market data provider for real-time trading.
    """
    
    def __init__(self, broker_connection=None):
        self.broker_connection = broker_connection
        self._initialized = False
        self._subscriptions: Dict[Symbol, bool] = {}
    
    def initialize(self) -> bool:
        """Initialize the live data provider."""
        try:
            # In a real implementation, this would connect to the broker API
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing LiveMarketDataProvider: {e}")
            return False
    
    def get_slice_data(self, time: datetime, symbols: List[Symbol]) -> Dict[Symbol, List[BaseData]]:
        """Get live market data slice."""
        if not self._initialized:
            return {}
        
        slice_data = {}
        
        for symbol in symbols:
            try:
                # In a real implementation, this would get live data from the broker
                # For now, we'll return mock real-time data
                current_data = self._get_live_data(symbol, time)
                if current_data:
                    slice_data[symbol] = [current_data]
            except Exception as e:
                print(f"Error getting live data for {symbol}: {e}")
        
        return slice_data
    
    def _get_live_data(self, symbol: Symbol, time: datetime) -> Optional[BaseData]:
        """Get live data for a symbol."""
        # Mock implementation - replace with actual broker API calls
        return Tick(
            symbol=symbol,
            time=time,
            end_time=time,
            value=100.5,
            quantity=100,
            exchange="NASDAQ"
        )
    
    def dispose(self):
        """Clean up resources."""
        self._subscriptions.clear()


class MarketDataService:
    """
    Main market data service that provides data slices to the trading engine.
    Supports both real-time and backtest scenarios through different providers.
    """
    
    def __init__(self, entity_service: EntityService):
        self.entity_service = entity_service
        self._provider: Optional[MarketDataProvider] = None
        self._history_service: Optional[MarketDataHistoryService] = None
        self._subscribed_symbols: List[Symbol] = []
        
        # Event callbacks
        self.on_data_slice: Optional[Callable[[Slice], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Configuration
        self._resolution = Resolution.MINUTE
        self._current_time = datetime.utcnow()
        
        # Statistics
        self._slices_generated = 0
        self._errors_count = 0
    
    def initialize_backtest(self, data_folder: str, start_time: datetime, end_time: datetime) -> bool:
        """
        Initialize for backtesting with file system data.
        
        Args:
            data_folder: Path to historical data files
            start_time: Backtest start time
            end_time: Backtest end time
            
        Returns:
            True if initialization successful
        """
        try:
            # Create file system provider
            self._provider = FileSystemMarketDataProvider(data_folder)
            
            if not self._provider.initialize():
                return False
            
            # Create and initialize history service
            self._history_service = MarketDataHistoryService(self)
            self._history_service.initialize_for_backtest(start_time, end_time)
            
            self._current_time = start_time
            return True
            
        except Exception as e:
            self._handle_error(f"Error initializing backtest: {e}")
            return False
    
    def initialize_live_trading(self, broker_connection=None) -> bool:
        """
        Initialize for live trading.
        
        Args:
            broker_connection: Optional broker connection for live data
            
        Returns:
            True if initialization successful
        """
        try:
            # Create live data provider
            self._provider = LiveMarketDataProvider(broker_connection)
            
            if not self._provider.initialize():
                return False
            
            # Create and initialize history service
            self._history_service = MarketDataHistoryService(self)
            self._history_service.initialize_for_live_trading()
            
            self._current_time = datetime.utcnow()
            return True
            
        except Exception as e:
            self._handle_error(f"Error initializing live trading: {e}")
            return False
    
    def add_symbol(self, symbol: Symbol):
        """Add a symbol to the subscription list."""
        if symbol not in self._subscribed_symbols:
            self._subscribed_symbols.append(symbol)
    
    def remove_symbol(self, symbol: Symbol):
        """Remove a symbol from the subscription list."""
        if symbol in self._subscribed_symbols:
            self._subscribed_symbols.remove(symbol)
    
    def get_current_slice(self) -> Optional[Slice]:
        """
        Get current market data slice for all subscribed symbols.
        
        Returns:
            Slice containing current market data or None if no data available
        """
        if not self._provider or not self._subscribed_symbols:
            return None
        
        try:
            # Get raw data from provider
            raw_data = self._provider.get_slice_data(self._current_time, self._subscribed_symbols)
            
            if not raw_data:
                return None
            
            # Create slice from raw data
            slice_obj = self._create_slice(raw_data, self._current_time)
            self._slices_generated += 1
            
            return slice_obj
            
        except Exception as e:
            self._handle_error(f"Error getting current slice: {e}")
            return None
    
    def advance_time(self, new_time: datetime) -> Optional[Slice]:
        """
        Advance to a new time and get the corresponding data slice.
        Used primarily in backtesting.
        
        Args:
            new_time: The new current time
            
        Returns:
            Slice for the new time or None if no data
        """
        if new_time < self._current_time:
            self._handle_error(f"Cannot go backwards in time: {new_time} < {self._current_time}")
            return None
        
        self._current_time = new_time
        
        # Update history service frontier
        if self._history_service:
            self._history_service._advance_frontier(new_time)
        
        return self.get_current_slice()
    
    def get_history_service(self) -> Optional[MarketDataHistoryService]:
        """Get the associated history service."""
        return self._history_service
    
    def resolve_symbol(self, symbol_string: str) -> Optional[Symbol]:
        """
        Resolve a symbol string to a Symbol object using the EntityService.
        
        Args:
            symbol_string: String representation of the symbol
            
        Returns:
            Symbol object or None if not found
        """
        try:
            # Use EntityService to resolve the symbol
            # This is a simplified implementation - the actual resolution
            # would depend on the specific entity types and repositories
            from ...domain.entities.finance.financial_assets.share import Share
            entity = self.entity_service.get_by_symbol(Share, symbol_string)
            
            if entity:
                return Symbol(symbol_string, entity.market if hasattr(entity, 'market') else 'USA')
            else:
                # Create a default symbol if not found in database
                return Symbol(symbol_string, 'USA')
                
        except Exception as e:
            self._handle_error(f"Error resolving symbol {symbol_string}: {e}")
            return None
    
    def _create_slice(self, raw_data: Dict[Symbol, List[BaseData]], slice_time: datetime) -> Slice:
        """
        Create a Slice object from raw data.
        
        Args:
            raw_data: Raw data organized by symbol
            slice_time: Time for the slice
            
        Returns:
            Properly formatted Slice object
        """
        from ..common.data_types import TradeBars, QuoteBars, Ticks
        
        slice_obj = Slice(time=slice_time)
        
        for symbol, data_list in raw_data.items():
            for data_point in data_list:
                if isinstance(data_point, TradeBar):
                    slice_obj.bars[symbol] = data_point
                elif isinstance(data_point, QuoteBar):
                    slice_obj.quote_bars[symbol] = data_point
                elif isinstance(data_point, Tick):
                    if symbol not in slice_obj.ticks:
                        slice_obj.ticks[symbol] = []
                    slice_obj.ticks[symbol].append(data_point)
        
        return slice_obj
    
    def _handle_error(self, error_message: str):
        """Handle errors."""
        self._errors_count += 1
        print(f"MarketDataService Error: {error_message}")
        
        if self.on_error:
            try:
                self.on_error(error_message)
            except Exception as e:
                print(f"Error in error callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            'slices_generated': self._slices_generated,
            'errors_count': self._errors_count,
            'subscribed_symbols': len(self._subscribed_symbols),
            'current_time': self._current_time,
            'provider_type': type(self._provider).__name__ if self._provider else None,
            'has_history_service': self._history_service is not None
        }
    
    def dispose(self):
        """Clean up resources."""
        if self._provider:
            self._provider.dispose()
        
        if self._history_service:
            self._history_service.dispose()
        
        self._subscribed_symbols.clear()
    
    @property
    def current_time(self) -> datetime:
        """Get current time."""
        return self._current_time
    
    @property
    def subscribed_symbols(self) -> List[Symbol]:
        """Get list of subscribed symbols."""
        return self._subscribed_symbols.copy()