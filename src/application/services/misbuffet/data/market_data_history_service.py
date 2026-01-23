"""
Market Data History Service - Provides historical data with frontier enforcement.
Ensures no look-ahead bias by maintaining a frontier that can only move forward in time.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
from abc import ABC, abstractmethod

from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick
from ..common.symbol import Symbol
from ..common.enums import Resolution

if TYPE_CHECKING:
    from .market_data_service import MarketDataService


class Frontier:
    """
    Maintains a time frontier to prevent look-ahead bias.
    The frontier can only advance forward in time, never backwards.
    """
    
    def __init__(self, frontier: datetime):
        self.frontier = frontier
    
    def advance(self, new_time: datetime):
        """
        Advance the frontier to a new time.
        
        Args:
            new_time: New frontier time
            
        Raises:
            ValueError: If new_time is before current frontier
        """
        if new_time < self.frontier:
            raise ValueError(f"Cannot go backwards: {new_time} < {self.frontier}")
        self.frontier = new_time
    
    def can_access(self, time: datetime) -> bool:
        """
        Check if data at given time can be accessed.
        
        Args:
            time: Time to check
            
        Returns:
            True if time is at or before the frontier
        """
        return time <= self.frontier
    
    def __str__(self) -> str:
        return f"Frontier({self.frontier})"
    
    def __repr__(self) -> str:
        return self.__str__()


class HistoryDataProvider(ABC):
    """
    Abstract base class for historical data providers.
    """
    
    @abstractmethod
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: Resolution) -> List[BaseData]:
        """Get historical data for a symbol within the specified time range."""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the history provider."""
        pass
    
    @abstractmethod
    def dispose(self):
        """Clean up resources."""
        pass


class FileSystemHistoryProvider(HistoryDataProvider):
    """
    File system based historical data provider.
    """
    
    def __init__(self, data_folder: str):
        self.data_folder = data_folder
        self._initialized = False
        self._data_cache: Dict[str, List[BaseData]] = {}
    
    def initialize(self) -> bool:
        """Initialize the file system history provider."""
        try:
            # In a real implementation, this would index available historical data files
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing FileSystemHistoryProvider: {e}")
            return False
    
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: Resolution) -> List[BaseData]:
        """Get historical data from file system."""
        if not self._initialized:
            return []
        
        try:
            # Generate cache key
            cache_key = f"{symbol.value}_{start}_{end}_{resolution.name}"
            
            # Check cache first
            if cache_key in self._data_cache:
                return self._data_cache[cache_key]
            
            # In a real implementation, this would read from data files
            # For now, generate mock historical data
            data = self._generate_mock_history(symbol, start, end, resolution)
            
            # Cache the result
            self._data_cache[cache_key] = data
            
            return data
            
        except Exception as e:
            print(f"Error getting history for {symbol}: {e}")
            return []
    
    def _generate_mock_history(self, symbol: Symbol, start: datetime, end: datetime, 
                             resolution: Resolution) -> List[BaseData]:
        """Generate mock historical data for testing."""
        data = []
        current_time = start
        base_price = 100.0
        
        # Determine time increment based on resolution
        if resolution == Resolution.MINUTE:
            increment = timedelta(minutes=1)
        elif resolution == Resolution.HOUR:
            increment = timedelta(hours=1)
        elif resolution == Resolution.DAILY:
            increment = timedelta(days=1)
        else:
            increment = timedelta(minutes=1)  # Default
        
        # Generate data points
        while current_time <= end:
            # Create mock trade bar
            price_variation = (hash(str(current_time)) % 200 - 100) / 100.0  # Random-like variation
            price = base_price + price_variation
            
            bar = TradeBar(
                symbol=symbol,
                time=current_time,
                end_time=current_time + increment,
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1000 + (hash(str(current_time)) % 5000),
                value=price
            )
            
            data.append(bar)
            current_time += increment
        
        return data
    
    def dispose(self):
        """Clean up resources."""
        self._data_cache.clear()


class DatabaseHistoryProvider(HistoryDataProvider):
    """
    Database based historical data provider.
    """
    
    def __init__(self, entity_service):
        self.entity_service = entity_service
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the database history provider."""
        try:
            # Verify database connection through entity service
            if self.entity_service and self.entity_service.database_service:
                self._initialized = True
                return True
            return False
        except Exception as e:
            print(f"Error initializing DatabaseHistoryProvider: {e}")
            return False
    
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: Resolution) -> List[BaseData]:
        """Get historical data from database."""
        if not self._initialized:
            return []
        
        try:
            # In a real implementation, this would query the database
            # through appropriate repositories via the entity service
            # For now, return empty list as we don't have the specific
            # historical data schema implemented
            return []
            
        except Exception as e:
            print(f"Error getting history from database for {symbol}: {e}")
            return []
    
    def dispose(self):
        """Clean up resources."""
        pass


class MarketDataHistoryService:
    """
    Provides historical market data with frontier enforcement to prevent look-ahead bias.
    This service ensures that algorithms can only access historical data up to the current
    simulation time, maintaining the integrity of backtesting.
    """
    
    def __init__(self, market_data_service: Optional['MarketDataService'] = None):
        self.market_data_service = market_data_service
        self._frontier: Optional[Frontier] = None
        self._history_provider: Optional[HistoryDataProvider] = None
        
        # Cache for recent history requests
        self._cache: Dict[str, List[BaseData]] = {}
        self._cache_max_size = 100
        
        # Statistics
        self._history_requests = 0
        self._cache_hits = 0
        self._errors_count = 0
        
        # Configuration
        self._max_history_days = 365 * 2  # Maximum 2 years of history per request
    
    def initialize_for_backtest(self, start_time: datetime, end_time: datetime):
        """
        Initialize for backtesting scenario.
        
        Args:
            start_time: Backtest start time (initial frontier)
            end_time: Backtest end time (not used for frontier, just for validation)
        """
        try:
            self._frontier = Frontier(start_time)
            
            # Create appropriate history provider
            if self.market_data_service and hasattr(self.market_data_service, '_provider'):
                provider = self.market_data_service._provider
                if hasattr(provider, 'data_folder'):
                    # Use file system provider
                    self._history_provider = FileSystemHistoryProvider(provider.data_folder)
                else:
                    # Use database provider
                    self._history_provider = DatabaseHistoryProvider(
                        self.market_data_service.entity_service
                    )
            else:
                # Default to database provider
                entity_service = (self.market_data_service.entity_service 
                                if self.market_data_service else None)
                self._history_provider = DatabaseHistoryProvider(entity_service)
            
            if self._history_provider:
                self._history_provider.initialize()
                
        except Exception as e:
            self._handle_error(f"Error initializing for backtest: {e}")
    
    def initialize_for_live_trading(self):
        """Initialize for live trading scenario."""
        try:
            self._frontier = Frontier(datetime.utcnow())
            
            # Use database provider for live trading
            entity_service = (self.market_data_service.entity_service 
                            if self.market_data_service else None)
            self._history_provider = DatabaseHistoryProvider(entity_service)
            
            if self._history_provider:
                self._history_provider.initialize()
                
        except Exception as e:
            self._handle_error(f"Error initializing for live trading: {e}")
    
    def get_history(self, symbol: Union[Symbol, str], periods: int, 
                   resolution: Resolution = Resolution.DAILY) -> List[BaseData]:
        """
        Get historical data for a symbol, respecting the frontier.
        
        Args:
            symbol: Symbol to get history for
            periods: Number of periods to retrieve
            resolution: Data resolution (daily, hourly, minute, etc.)
            
        Returns:
            List of historical data points, respecting the frontier
        """
        if not self._frontier or not self._history_provider:
            self._handle_error("History service not properly initialized")
            return []
        
        # Convert string to Symbol if needed
        if isinstance(symbol, str):
            if self.market_data_service:
                symbol_obj = self.market_data_service.resolve_symbol(symbol)
                if not symbol_obj:
                    self._handle_error(f"Could not resolve symbol: {symbol}")
                    return []
            else:
                # Create default symbol
                symbol_obj = Symbol(symbol, 'USA')
        else:
            symbol_obj = symbol
        
        try:
            self._history_requests += 1
            
            # Calculate time range
            end_time = self._frontier.frontier
            start_time = self._calculate_start_time(end_time, periods, resolution)
            
            # Check cache
            cache_key = f"{symbol_obj.value}_{start_time}_{end_time}_{resolution.name}"
            if cache_key in self._cache:
                self._cache_hits += 1
                return self._cache[cache_key]
            
            # Validate time range
            if (end_time - start_time).days > self._max_history_days:
                self._handle_error(f"History request too large: {(end_time - start_time).days} days")
                return []
            
            # Get data from provider
            data = self._history_provider.get_history(symbol_obj, start_time, end_time, resolution)
            
            # Filter data to respect frontier (extra safety)
            filtered_data = [d for d in data if d.time <= self._frontier.frontier]
            
            # Cache the result
            self._update_cache(cache_key, filtered_data)
            
            return filtered_data
            
        except Exception as e:
            self._handle_error(f"Error getting history for {symbol_obj}: {e}")
            return []
    
    def get_history_range(self, symbol: Union[Symbol, str], start: datetime, end: datetime, 
                         resolution: Resolution = Resolution.DAILY) -> List[BaseData]:
        """
        Get historical data for a specific date range, respecting the frontier.
        
        Args:
            symbol: Symbol to get history for
            start: Start datetime
            end: End datetime (will be capped at frontier)
            resolution: Data resolution
            
        Returns:
            List of historical data points within the range
        """
        if not self._frontier or not self._history_provider:
            self._handle_error("History service not properly initialized")
            return []
        
        # Ensure end time doesn't exceed frontier
        end_capped = min(end, self._frontier.frontier)
        
        if start > end_capped:
            self._handle_error(f"Invalid time range: start {start} > end {end_capped}")
            return []
        
        # Convert string to Symbol if needed
        if isinstance(symbol, str):
            if self.market_data_service:
                symbol_obj = self.market_data_service.resolve_symbol(symbol)
                if not symbol_obj:
                    self._handle_error(f"Could not resolve symbol: {symbol}")
                    return []
            else:
                symbol_obj = Symbol(symbol, 'USA')
        else:
            symbol_obj = symbol
        
        try:
            self._history_requests += 1
            
            # Check cache
            cache_key = f"{symbol_obj.value}_{start}_{end_capped}_{resolution.name}"
            if cache_key in self._cache:
                self._cache_hits += 1
                return self._cache[cache_key]
            
            # Get data from provider
            data = self._history_provider.get_history(symbol_obj, start, end_capped, resolution)
            
            # Cache the result
            self._update_cache(cache_key, data)
            
            return data
            
        except Exception as e:
            self._handle_error(f"Error getting history range for {symbol_obj}: {e}")
            return []
    
    def _advance_frontier(self, new_time: datetime):
        """
        Advance the frontier to a new time.
        Called by MarketDataService when time advances.
        
        Args:
            new_time: New frontier time
        """
        if self._frontier:
            try:
                self._frontier.advance(new_time)
                # Clear cache when frontier advances significantly
                if len(self._cache) > self._cache_max_size:
                    self._cache.clear()
            except ValueError as e:
                self._handle_error(f"Frontier advance error: {e}")
    
    def _calculate_start_time(self, end_time: datetime, periods: int, 
                            resolution: Resolution) -> datetime:
        """Calculate start time based on periods and resolution."""
        if resolution == Resolution.MINUTE:
            return end_time - timedelta(minutes=periods)
        elif resolution == Resolution.HOUR:
            return end_time - timedelta(hours=periods)
        elif resolution == Resolution.DAILY:
            return end_time - timedelta(days=periods)
        elif resolution == Resolution.WEEKLY:
            return end_time - timedelta(weeks=periods)
        else:
            # Default to daily
            return end_time - timedelta(days=periods)
    
    def _update_cache(self, key: str, data: List[BaseData]):
        """Update the cache with new data."""
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = data
    
    def _handle_error(self, error_message: str):
        """Handle errors."""
        self._errors_count += 1
        print(f"MarketDataHistoryService Error: {error_message}")
    
    def get_frontier_time(self) -> Optional[datetime]:
        """Get current frontier time."""
        return self._frontier.frontier if self._frontier else None
    
    def can_access_time(self, time: datetime) -> bool:
        """Check if data at given time can be accessed."""
        return self._frontier.can_access(time) if self._frontier else False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            'history_requests': self._history_requests,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': self._cache_hits / max(1, self._history_requests),
            'errors_count': self._errors_count,
            'cache_size': len(self._cache),
            'frontier_time': self.get_frontier_time(),
            'provider_type': type(self._history_provider).__name__ if self._history_provider else None
        }
    
    def dispose(self):
        """Clean up resources."""
        if self._history_provider:
            self._history_provider.dispose()
        
        self._cache.clear()
        self._frontier = None
    
    @property
    def frontier(self) -> Optional[Frontier]:
        """Get the frontier object."""
        return self._frontier