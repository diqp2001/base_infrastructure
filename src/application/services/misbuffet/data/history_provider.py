"""
History provider implementations for historical data retrieval.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Iterator
from pathlib import Path

from ..common.interfaces import IHistoryProvider
from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick, SubscriptionDataConfig
from ..common.symbol import Symbol
from ..common.enums import Resolution, SecurityType
from ..common.time_utils import Time
from .data_reader import BaseDataReader, LeanDataReader, CsvDataReader, MemoryDataReader


class HistoryProvider(IHistoryProvider):
    """
    Base class for historical data providers.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[BaseData]] = {}
        self._cache_max_size = 10000  # Maximum cached data points per symbol
        self._cache_expiry = timedelta(hours=1)  # Cache expiry time
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: Resolution) -> List[BaseData]:
        """Get historical data for the specified parameters."""
        cache_key = self._get_cache_key(symbol, start, end, resolution)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            cached_data = self._cache.get(cache_key, [])
            if cached_data:
                return self._filter_data_by_time(cached_data, start, end)
        
        # Fetch data from source
        try:
            data = self._fetch_history(symbol, start, end, resolution)
            
            # Cache the data
            self._cache_data(cache_key, data)
            
            return data
            
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return []
    
    @abstractmethod
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch historical data from the underlying source."""
        pass
    
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """Initialize the history provider with configuration parameters."""
        self._cache_max_size = parameters.get('cache_max_size', self._cache_max_size)
        cache_expiry_minutes = parameters.get('cache_expiry_minutes', 60)
        self._cache_expiry = timedelta(minutes=cache_expiry_minutes)
    
    def _get_cache_key(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> str:
        """Generate cache key for the request."""
        return f"{symbol}_{resolution.value}_{start.isoformat()}_{end.isoformat()}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        return datetime.utcnow() - cache_time < self._cache_expiry
    
    def _cache_data(self, cache_key: str, data: List[BaseData]):
        """Cache the data with size limits."""
        if len(data) <= self._cache_max_size:
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            # Clean up old cache entries if cache is getting too large
            if len(self._cache) > 100:  # Arbitrary limit
                self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove old cache entries."""
        current_time = datetime.utcnow()
        keys_to_remove = []
        
        for key, timestamp in self._cache_timestamps.items():
            if current_time - timestamp > self._cache_expiry:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    def _filter_data_by_time(self, data: List[BaseData], start: datetime, 
                           end: datetime) -> List[BaseData]:
        """Filter data by time range."""
        return [d for d in data if start <= d.time <= end]
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        total_data_points = sum(len(data) for data in self._cache.values())
        
        return {
            'total_entries': total_entries,
            'total_data_points': total_data_points,
            'cache_hit_ratio': 0.0  # Could be implemented with hit/miss tracking
        }


class FileSystemHistoryProvider(HistoryProvider):
    """
    History provider that reads data from the file system.
    """
    
    def __init__(self, data_folder: str):
        super().__init__()
        self.data_folder = Path(data_folder)
        self._data_readers: Dict[str, BaseDataReader] = {}
        self._initialize_readers()
    
    def _initialize_readers(self):
        """Initialize data readers."""
        self._data_readers['lean'] = LeanDataReader(str(self.data_folder))
        self._data_readers['csv'] = CsvDataReader(str(self.data_folder))
    
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch historical data from file system."""
        # Create subscription config
        config = SubscriptionDataConfig(
            symbol=symbol,
            data_type=TradeBar,  # Default to TradeBar
            resolution=resolution,
            time_zone="UTC",
            market=symbol.market.value
        )
        
        # Try different readers in order of preference
        readers_to_try = ['lean', 'csv']
        
        for reader_name in readers_to_try:
            reader = self._data_readers.get(reader_name)
            if reader and reader.supports_resolution(resolution):
                try:
                    data_iterator = reader.read_data(config, start, end)
                    data = list(data_iterator)
                    
                    if data:
                        return sorted(data, key=lambda x: x.time)
                        
                except Exception as e:
                    print(f"Error with {reader_name} reader for {symbol}: {e}")
                    continue
        
        # No data found
        return []
    
    def get_available_symbols(self, security_type: SecurityType = None, 
                            market: str = None) -> List[Symbol]:
        """Get list of available symbols in the data folder."""
        symbols = []
        
        try:
            if security_type:
                security_folders = [self.data_folder / security_type.value]
            else:
                security_folders = [f for f in self.data_folder.iterdir() if f.is_dir()]
            
            for sec_folder in security_folders:
                if not sec_folder.is_dir():
                    continue
                
                # Get security type from folder name
                try:
                    sec_type = SecurityType(sec_folder.name)
                except ValueError:
                    continue
                
                # Look for market folders
                market_folders = [f for f in sec_folder.iterdir() if f.is_dir()]
                
                for market_folder in market_folders:
                    if market and market_folder.name != market:
                        continue
                    
                    # Look for resolution folders
                    resolution_folders = [f for f in market_folder.iterdir() if f.is_dir()]
                    
                    for res_folder in resolution_folders:
                        # Look for symbol folders
                        symbol_folders = [f for f in res_folder.iterdir() if f.is_dir()]
                        
                        for symbol_folder in symbol_folders:
                            # Check if folder contains data files
                            data_files = (list(symbol_folder.glob("*.zip")) + 
                                        list(symbol_folder.glob("*.csv")) +
                                        list(symbol_folder.glob("*.json")))
                            
                            if data_files:
                                symbol = Symbol(
                                    value=symbol_folder.name.upper(),
                                    id=f"{symbol_folder.name.upper()}-{market_folder.name.upper()}",
                                    security_type=sec_type,
                                    market=market_folder.name
                                )
                                
                                if symbol not in symbols:
                                    symbols.append(symbol)
        
        except Exception as e:
            print(f"Error scanning for available symbols: {e}")
        
        return symbols
    
    def get_available_resolutions(self, symbol: Symbol) -> List[Resolution]:
        """Get available resolutions for a symbol."""
        resolutions = []
        
        try:
            symbol_base_path = (self.data_folder / 
                              symbol.security_type.value / 
                              symbol.market.value)
            
            if symbol_base_path.exists():
                for res_folder in symbol_base_path.iterdir():
                    if res_folder.is_dir():
                        try:
                            resolution = Resolution(res_folder.name)
                            
                            # Check if symbol folder exists with data
                            symbol_folder = res_folder / symbol.value.lower()
                            if symbol_folder.exists():
                                data_files = (list(symbol_folder.glob("*.zip")) + 
                                            list(symbol_folder.glob("*.csv")))
                                if data_files:
                                    resolutions.append(resolution)
                                    
                        except ValueError:
                            continue
        
        except Exception as e:
            print(f"Error getting available resolutions for {symbol}: {e}")
        
        return resolutions


class BrokerageHistoryProvider(HistoryProvider):
    """
    History provider that fetches data from a brokerage API.
    """
    
    def __init__(self, brokerage_api):
        super().__init__()
        self.brokerage_api = brokerage_api
        self._rate_limiter = None  # Could implement rate limiting
    
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """Initialize with brokerage-specific parameters."""
        super().initialize(parameters)
        
        # Initialize brokerage API if needed
        if hasattr(self.brokerage_api, 'initialize'):
            self.brokerage_api.initialize(parameters)
    
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch historical data from brokerage API."""
        try:
            # Convert our types to brokerage API format
            api_symbol = self._convert_symbol_to_api_format(symbol)
            api_resolution = self._convert_resolution_to_api_format(resolution)
            
            # Make API request
            if hasattr(self.brokerage_api, 'get_historical_data'):
                api_data = self.brokerage_api.get_historical_data(
                    symbol=api_symbol,
                    start_time=start,
                    end_time=end,
                    resolution=api_resolution
                )
                
                # Convert API data to our format
                return self._convert_api_data_to_base_data(api_data, symbol)
            
            else:
                print("Brokerage API does not support historical data")
                return []
                
        except Exception as e:
            print(f"Error fetching data from brokerage API: {e}")
            return []
    
    def _convert_symbol_to_api_format(self, symbol: Symbol) -> str:
        """Convert Symbol to brokerage API format."""
        # This would be implemented based on specific brokerage requirements
        return symbol.value
    
    def _convert_resolution_to_api_format(self, resolution: Resolution) -> str:
        """Convert Resolution to brokerage API format."""
        # Map our resolutions to brokerage API resolutions
        resolution_mapping = {
            Resolution.TICK: "1T",
            Resolution.SECOND: "1S", 
            Resolution.MINUTE: "1M",
            Resolution.HOUR: "1H",
            Resolution.DAILY: "1D"
        }
        
        return resolution_mapping.get(resolution, "1D")
    
    def _convert_api_data_to_base_data(self, api_data: List[Dict[str, Any]], 
                                     symbol: Symbol) -> List[BaseData]:
        """Convert brokerage API data to BaseData objects."""
        data_points = []
        
        for item in api_data:
            try:
                # This would be implemented based on specific API response format
                time = self._parse_api_timestamp(item.get('timestamp') or item.get('time'))
                
                if 'open' in item and 'high' in item and 'low' in item and 'close' in item:
                    # OHLCV data
                    trade_bar = TradeBar(
                        symbol=symbol,
                        time=time,
                        value=item['close'],
                        open=item['open'],
                        high=item['high'],
                        low=item['low'],
                        close=item['close'],
                        volume=item.get('volume', 0)
                    )
                    data_points.append(trade_bar)
                    
                else:
                    # Simple price data
                    price = item.get('price') or item.get('value') or item.get('close')
                    if price:
                        data_point = BaseData(
                            symbol=symbol,
                            time=time,
                            value=price
                        )
                        data_points.append(data_point)
                        
            except Exception as e:
                print(f"Error converting API data item: {e}")
                continue
        
        return sorted(data_points, key=lambda x: x.time)
    
    def _parse_api_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from API response."""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, (int, float)):
            # Unix timestamp
            return datetime.utcfromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # Try to parse string timestamp
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.utcnow()


class SubscriptionHistoryProvider(HistoryProvider):
    """
    History provider that uses active subscriptions to build historical data.
    """
    
    def __init__(self, subscription_manager):
        super().__init__()
        self.subscription_manager = subscription_manager
        self._history_buffer: Dict[Symbol, List[BaseData]] = {}
        self._buffer_max_size = 10000
    
    def add_data_point(self, data: BaseData):
        """Add a data point to the history buffer."""
        symbol = data.symbol
        
        if symbol not in self._history_buffer:
            self._history_buffer[symbol] = []
        
        self._history_buffer[symbol].append(data)
        
        # Maintain buffer size
        buffer = self._history_buffer[symbol]
        if len(buffer) > self._buffer_max_size:
            # Keep only the most recent data
            self._history_buffer[symbol] = buffer[-self._buffer_max_size // 2:]
    
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch historical data from subscription buffer."""
        if symbol not in self._history_buffer:
            return []
        
        buffer = self._history_buffer[symbol]
        
        # Filter by time range and resolution
        filtered_data = []
        for data_point in buffer:
            if start <= data_point.time <= end:
                # For now, return all data regardless of resolution
                # In a more sophisticated implementation, we would aggregate data
                # to match the requested resolution
                filtered_data.append(data_point)
        
        return sorted(filtered_data, key=lambda x: x.time)
    
    def get_buffer_size(self, symbol: Symbol) -> int:
        """Get the size of the history buffer for a symbol."""
        return len(self._history_buffer.get(symbol, []))
    
    def clear_buffer(self, symbol: Symbol = None):
        """Clear history buffer for a symbol or all symbols."""
        if symbol:
            self._history_buffer.pop(symbol, None)
        else:
            self._history_buffer.clear()


class CompositeHistoryProvider(HistoryProvider):
    """
    History provider that combines multiple providers with fallback logic.
    """
    
    def __init__(self, providers: List[HistoryProvider]):
        super().__init__()
        self.providers = providers
        self._provider_priorities = list(range(len(providers)))  # Default priorities
    
    def set_provider_priorities(self, priorities: List[int]):
        """Set provider priorities (lower number = higher priority)."""
        if len(priorities) == len(self.providers):
            self._provider_priorities = priorities
    
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch historical data using provider fallback logic."""
        # Sort providers by priority
        sorted_providers = sorted(
            zip(self.providers, self._provider_priorities),
            key=lambda x: x[1]
        )
        
        for provider, _ in sorted_providers:
            try:
                data = provider.get_history(symbol, start, end, resolution)
                if data:
                    return data
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
        
        # No provider succeeded
        return []
    
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """Initialize all providers."""
        super().initialize(parameters)
        
        for provider in self.providers:
            try:
                provider.initialize(parameters)
            except Exception as e:
                print(f"Failed to initialize provider {provider.__class__.__name__}: {e}")


class MockHistoryProvider(HistoryProvider):
    """
    Mock history provider for testing purposes.
    """
    
    def __init__(self):
        super().__init__()
        self._mock_data: Dict[Symbol, List[BaseData]] = {}
    
    def add_mock_data(self, symbol: Symbol, data: List[BaseData]):
        """Add mock data for a symbol."""
        self._mock_data[symbol] = sorted(data, key=lambda x: x.time)
    
    def _fetch_history(self, symbol: Symbol, start: datetime, end: datetime, 
                      resolution: Resolution) -> List[BaseData]:
        """Fetch mock historical data."""
        if symbol not in self._mock_data:
            return []
        
        data = self._mock_data[symbol]
        return [d for d in data if start <= d.time <= end]
    
    def clear_mock_data(self):
        """Clear all mock data."""
        self._mock_data.clear()