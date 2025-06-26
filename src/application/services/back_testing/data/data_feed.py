"""
Data feed implementations for live and backtesting scenarios.
"""

import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Iterator, Any, Callable
from queue import Queue, Empty
from pathlib import Path

from ..common.interfaces import IDataFeed
from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick, Slice, SubscriptionDataConfig
from ..common.symbol import Symbol
from ..common.enums import Resolution, SecurityType
from ..common.time_utils import Time
from .data_reader import BaseDataReader, LeanDataReader, CsvDataReader
from .subscription_manager import SubscriptionManager


class DataFeed(IDataFeed):
    """
    Base implementation of data feed.
    Manages data subscriptions and provides data to the algorithm.
    """
    
    def __init__(self):
        self.subscription_manager = SubscriptionManager()
        self._data_readers: Dict[str, BaseDataReader] = {}
        self._is_active = False
        self._current_time = datetime.utcnow()
        
        # Event handlers
        self.new_data_available: Optional[Callable[[Slice], None]] = None
    
    def initialize(self) -> bool:
        """Initialize the data feed."""
        try:
            self._initialize_data_readers()
            self._is_active = True
            return True
        except Exception as e:
            print(f"Failed to initialize data feed: {e}")
            return False
    
    def _initialize_data_readers(self):
        """Initialize available data readers."""
        self._data_readers['lean'] = LeanDataReader()
        self._data_readers['csv'] = CsvDataReader()
    
    def create_subscription(self, symbol: Symbol, resolution: Resolution) -> SubscriptionDataConfig:
        """Create a data subscription for the given symbol and resolution."""
        config = SubscriptionDataConfig(
            symbol=symbol,
            data_type=TradeBar,  # Default to TradeBar
            resolution=resolution,
            time_zone="UTC",
            market=symbol.market.value,
            fill_forward=True
        )
        
        self.subscription_manager.add_subscription(config)
        return config
    
    def remove_subscription(self, config: SubscriptionDataConfig) -> bool:
        """Remove a data subscription."""
        return self.subscription_manager.remove_subscription(config)
    
    @abstractmethod
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of data ticks."""
        pass
    
    def dispose(self):
        """Clean up resources."""
        self._is_active = False
        self.subscription_manager.clear()


class FileSystemDataFeed(DataFeed):
    """
    Data feed for backtesting that reads data from the file system.
    """
    
    def __init__(self, data_folder: str):
        super().__init__()
        self.data_folder = Path(data_folder)
        self._file_readers: Dict[Symbol, Iterator[BaseData]] = {}
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._current_slice: Optional[Slice] = None
        
        # Synchronization for multiple data streams
        self._data_queue: Queue = Queue()
        self._is_finished = False
    
    def set_time_range(self, start_time: datetime, end_time: datetime):
        """Set the time range for backtesting."""
        self._start_time = start_time
        self._end_time = end_time
        self._current_time = start_time
    
    def initialize(self) -> bool:
        """Initialize the file system data feed."""
        if not super().initialize():
            return False
        
        try:
            self._initialize_file_readers()
            return True
        except Exception as e:
            print(f"Failed to initialize file system data feed: {e}")
            return False
    
    def _initialize_file_readers(self):
        """Initialize file readers for all subscriptions."""
        for config in self.subscription_manager.get_subscriptions():
            try:
                reader = self._get_data_reader_for_config(config)
                if reader:
                    data_iterator = reader.read_data(config, self._start_time, self._end_time)
                    self._file_readers[config.symbol] = data_iterator
            except Exception as e:
                print(f"Failed to initialize reader for {config.symbol}: {e}")
    
    def _get_data_reader_for_config(self, config: SubscriptionDataConfig) -> Optional[BaseDataReader]:
        """Get the appropriate data reader for a subscription configuration."""
        # Try to find data files for this symbol
        symbol_folder = self._get_symbol_folder(config.symbol, config.resolution)
        
        if symbol_folder.exists():
            # Check for different file formats
            lean_files = list(symbol_folder.glob("*.zip"))
            if lean_files:
                return self._data_readers.get('lean')
            
            csv_files = list(symbol_folder.glob("*.csv"))
            if csv_files:
                return self._data_readers.get('csv')
        
        return None
    
    def _get_symbol_folder(self, symbol: Symbol, resolution: Resolution) -> Path:
        """Get the folder path for a symbol's data."""
        # Standard QuantConnect folder structure
        # data/{security_type}/{market}/{resolution}/{symbol}/
        return (self.data_folder / 
                symbol.security_type.value / 
                symbol.market.value / 
                resolution.value / 
                symbol.value.lower())
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of data ticks for backtesting."""
        if self._is_finished or not self._is_active:
            return []
        
        # Collect data from all readers for the current time
        current_data: Dict[Symbol, BaseData] = {}
        min_next_time = None
        
        for symbol, reader in list(self._file_readers.items()):
            try:
                data_point = next(reader)
                if data_point and data_point.time >= self._current_time:
                    current_data[symbol] = data_point
                    
                    # Track the minimum next time across all data sources
                    if min_next_time is None or data_point.time < min_next_time:
                        min_next_time = data_point.time
                        
            except StopIteration:
                # This reader is finished
                del self._file_readers[symbol]
            except Exception as e:
                print(f"Error reading data for {symbol}: {e}")
                # Remove problematic reader
                if symbol in self._file_readers:
                    del self._file_readers[symbol]
        
        # Update current time
        if min_next_time:
            self._current_time = min_next_time
        elif not self._file_readers:
            # All readers are finished
            self._is_finished = True
        
        # Check if we've reached the end time
        if self._end_time and self._current_time >= self._end_time:
            self._is_finished = True
        
        return list(current_data.values())
    
    def create_slice(self, data: List[BaseData]) -> Slice:
        """Create a data slice from the provided data."""
        if not data:
            return Slice(self._current_time, {})
        
        # Group data by symbol
        data_by_symbol: Dict[Symbol, List[BaseData]] = {}
        slice_time = data[0].time
        
        for data_point in data:
            if data_point.symbol not in data_by_symbol:
                data_by_symbol[data_point.symbol] = []
            data_by_symbol[data_point.symbol].append(data_point)
            
            # Use the latest time
            if data_point.time > slice_time:
                slice_time = data_point.time
        
        return Slice(slice_time, data_by_symbol)
    
    @property
    def is_finished(self) -> bool:
        """Returns true if the data feed has finished providing data."""
        return self._is_finished


class LiveTradingDataFeed(DataFeed):
    """
    Data feed for live trading that receives real-time market data.
    """
    
    def __init__(self, data_queue_handler):
        super().__init__()
        self.data_queue_handler = data_queue_handler
        self._data_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_requested = False
        
        # Real-time data processing
        self._last_slice_time: Optional[datetime] = None
        self._slice_timeout = timedelta(seconds=1)  # 1 second timeout for slice creation
    
    def initialize(self) -> bool:
        """Initialize the live trading data feed."""
        if not super().initialize():
            return False
        
        try:
            # Initialize the data queue handler
            if hasattr(self.data_queue_handler, 'initialize'):
                self.data_queue_handler.initialize()
            
            # Start the data processing thread
            self._start_data_thread()
            return True
            
        except Exception as e:
            print(f"Failed to initialize live trading data feed: {e}")
            return False
    
    def _start_data_thread(self):
        """Start the background thread for data processing."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_requested = False
            self._worker_thread = threading.Thread(target=self._data_thread_worker, daemon=True)
            self._worker_thread.start()
    
    def _data_thread_worker(self):
        """Background thread worker for processing real-time data."""
        while not self._stop_requested and self._is_active:
            try:
                # Get data from the queue handler
                if hasattr(self.data_queue_handler, 'get_next_ticks'):
                    ticks = self.data_queue_handler.get_next_ticks()
                    if ticks:
                        for tick in ticks:
                            self._data_queue.put(tick)
                
                # Small sleep to prevent busy waiting
                time.sleep(0.001)  # 1ms
                
            except Exception as e:
                print(f"Error in data thread worker: {e}")
                time.sleep(0.1)  # Longer sleep on error
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of data ticks for live trading."""
        if not self._is_active:
            return []
        
        ticks = []
        current_time = Time.utc_now()
        
        # Collect ticks for a short time window or until queue is empty
        timeout = 0.1  # 100ms timeout
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                tick = self._data_queue.get_nowait()
                ticks.append(tick)
                
                # Limit the number of ticks per batch
                if len(ticks) >= 1000:
                    break
                    
            except Empty:
                break
        
        return ticks
    
    def create_slice(self, data: List[BaseData]) -> Slice:
        """Create a data slice from real-time data."""
        if not data:
            return Slice(Time.utc_now(), {})
        
        # Group data by symbol
        data_by_symbol: Dict[Symbol, List[BaseData]] = {}
        latest_time = data[0].time
        
        for data_point in data:
            if data_point.symbol not in data_by_symbol:
                data_by_symbol[data_point.symbol] = []
            data_by_symbol[data_point.symbol].append(data_point)
            
            if data_point.time > latest_time:
                latest_time = data_point.time
        
        self._last_slice_time = latest_time
        return Slice(latest_time, data_by_symbol)
    
    def dispose(self):
        """Clean up resources."""
        self._stop_requested = True
        super().dispose()
        
        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        
        # Clean up data queue handler
        if hasattr(self.data_queue_handler, 'dispose'):
            self.data_queue_handler.dispose()


class UniverseDataFeed(DataFeed):
    """
    Data feed that handles dynamic universe selection.
    """
    
    def __init__(self, base_feed: DataFeed):
        super().__init__()
        self.base_feed = base_feed
        self._universe_symbols: List[Symbol] = []
        self._universe_selection_callback: Optional[Callable[[List[BaseData]], List[Symbol]]] = None
    
    def set_universe_selection(self, callback: Callable[[List[BaseData]], List[Symbol]]):
        """Set the universe selection callback."""
        self._universe_selection_callback = callback
    
    def add_universe_symbol(self, symbol: Symbol):
        """Add a symbol to the universe."""
        if symbol not in self._universe_symbols:
            self._universe_symbols.append(symbol)
    
    def remove_universe_symbol(self, symbol: Symbol):
        """Remove a symbol from the universe."""
        if symbol in self._universe_symbols:
            self._universe_symbols.remove(symbol)
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get next ticks with universe selection applied."""
        # Get base data
        base_ticks = self.base_feed.get_next_ticks()
        
        # Apply universe selection if callback is set
        if self._universe_selection_callback and base_ticks:
            try:
                selected_symbols = self._universe_selection_callback(base_ticks)
                self._update_universe(selected_symbols)
            except Exception as e:
                print(f"Error in universe selection: {e}")
        
        # Filter ticks to only include universe symbols
        filtered_ticks = [tick for tick in base_ticks if tick.symbol in self._universe_symbols]
        
        return filtered_ticks
    
    def _update_universe(self, new_symbols: List[Symbol]):
        """Update the universe with new symbols."""
        # Remove symbols that are no longer in the universe
        symbols_to_remove = [s for s in self._universe_symbols if s not in new_symbols]
        for symbol in symbols_to_remove:
            self.remove_universe_symbol(symbol)
        
        # Add new symbols
        for symbol in new_symbols:
            if symbol not in self._universe_symbols:
                self.add_universe_symbol(symbol)
                # Create subscription for new symbol
                self.create_subscription(symbol, Resolution.DAILY)  # Default resolution
    
    def initialize(self) -> bool:
        """Initialize the universe data feed."""
        return self.base_feed.initialize()
    
    def create_subscription(self, symbol: Symbol, resolution: Resolution) -> SubscriptionDataConfig:
        """Create subscription through base feed."""
        return self.base_feed.create_subscription(symbol, resolution)
    
    def remove_subscription(self, config: SubscriptionDataConfig) -> bool:
        """Remove subscription through base feed."""
        return self.base_feed.remove_subscription(config)
    
    def dispose(self):
        """Clean up resources."""
        super().dispose()
        self.base_feed.dispose()