"""
Data manager for orchestrating data feeds and subscriptions.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from queue import Queue, Empty

from ..common.data_types import BaseData, Slice, SubscriptionDataConfig
from ..common.symbol import Symbol
from ..common.enums import Resolution
from ..common.time_utils import Time
from .data_feed import DataFeed, FileSystemDataFeed, LiveTradingDataFeed
from .subscription_manager import SubscriptionManager, SubscriptionSynchronizer
from .history_provider import HistoryProvider, FileSystemHistoryProvider


class DataManager:
    """
    Central manager for all data operations.
    Orchestrates data feeds, subscriptions, and history providers.
    """
    
    def __init__(self):
        self.subscription_manager = SubscriptionManager()
        self.synchronizer = SubscriptionSynchronizer()
        
        self._data_feed: Optional[DataFeed] = None
        self._history_provider: Optional[HistoryProvider] = None
        
        # Data processing
        self._data_queue: Queue = Queue()
        self._processed_data_queue: Queue = Queue()
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = False
        
        # Event handlers
        self.new_data_callback: Optional[Callable[[Slice], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
        # Configuration
        self._slice_creation_interval = timedelta(seconds=1)
        self._max_queue_size = 10000
        
        # Statistics
        self._data_points_processed = 0
        self._slices_created = 0
        self._errors_count = 0
    
    def initialize(self, data_feed: DataFeed, history_provider: HistoryProvider = None):
        """Initialize the data manager with a data feed and optional history provider."""
        self._data_feed = data_feed
        self._history_provider = history_provider
        
        # Initialize components
        if not self._data_feed.initialize():
            raise RuntimeError("Failed to initialize data feed")
        
        if self._history_provider:
            self._history_provider.initialize({})
        
        # Set up data feed callback
        self._data_feed.new_data_available = self._handle_new_data
        
        # Start data processing thread
        self._start_processing_thread()
    
    def add_subscription(self, symbol: Symbol, resolution: Resolution, 
                        data_type: type = None, **kwargs) -> SubscriptionDataConfig:
        """Add a data subscription."""
        # Create subscription config
        from ..common.data_types import TradeBar
        
        config = SubscriptionDataConfig(
            symbol=symbol,
            data_type=data_type or TradeBar,
            resolution=resolution,
            time_zone=kwargs.get('time_zone', 'UTC'),
            market=kwargs.get('market', symbol.market.value),
            fill_forward=kwargs.get('fill_forward', True),
            extended_market_hours=kwargs.get('extended_market_hours', False)
        )
        
        # Add to subscription manager
        if self.subscription_manager.add_subscription(config):
            # Add to data feed if possible
            if self._data_feed:
                self._data_feed.create_subscription(symbol, resolution)
            
            return config
        else:
            raise ValueError(f"Failed to add subscription for {symbol}")
    
    def remove_subscription(self, symbol: Symbol, resolution: Resolution = None):
        """Remove subscription(s) for a symbol."""
        if resolution:
            # Remove specific subscription
            configs = self.subscription_manager.get_subscriptions_for_symbol(symbol)
            configs_to_remove = [c for c in configs if c.resolution == resolution]
            
            for config in configs_to_remove:
                self.subscription_manager.remove_subscription(config)
                if self._data_feed:
                    self._data_feed.remove_subscription(config)
        else:
            # Remove all subscriptions for symbol
            self.subscription_manager.remove_symbol(symbol)
    
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: Resolution) -> List[BaseData]:
        """Get historical data for a symbol."""
        if not self._history_provider:
            return []
        
        try:
            return self._history_provider.get_history(symbol, start, end, resolution)
        except Exception as e:
            self._handle_error(f"Error getting history for {symbol}: {e}")
            return []
    
    def get_current_slice(self) -> Optional[Slice]:
        """Get the most recent data slice."""
        try:
            return self._processed_data_queue.get_nowait()
        except Empty:
            return None
    
    def _start_processing_thread(self):
        """Start the data processing thread."""
        if self._processing_thread is None or not self._processing_thread.is_alive():
            self._stop_processing = False
            self._processing_thread = threading.Thread(
                target=self._data_processing_worker,
                daemon=True
            )
            self._processing_thread.start()
    
    def _data_processing_worker(self):
        """Data processing worker thread."""
        last_slice_time = datetime.utcnow()
        pending_data: Dict[Symbol, BaseData] = {}
        
        while not self._stop_processing:
            try:
                current_time = datetime.utcnow()
                
                # Process incoming data
                self._process_incoming_data(pending_data)
                
                # Create slice if enough time has passed or we have enough data
                if (current_time - last_slice_time >= self._slice_creation_interval or 
                    len(pending_data) >= 100):
                    
                    if pending_data:
                        slice_obj = self._create_slice(pending_data, current_time)
                        self._processed_data_queue.put(slice_obj)
                        
                        # Notify callback
                        if self.new_data_callback:
                            try:
                                self.new_data_callback(slice_obj)
                            except Exception as e:
                                self._handle_error(f"Error in data callback: {e}")
                        
                        # Clear pending data and update timestamp
                        pending_data.clear()
                        last_slice_time = current_time
                        self._slices_created += 1
                
                # Small sleep to prevent busy waiting
                time.sleep(0.001)  # 1ms
                
            except Exception as e:
                self._handle_error(f"Error in data processing worker: {e}")
                time.sleep(0.1)  # Longer sleep on error
    
    def _process_incoming_data(self, pending_data: Dict[Symbol, BaseData]):
        """Process incoming data from the data feed."""
        if not self._data_feed:
            return
        
        try:
            # Get new data from feed
            new_data = self._data_feed.get_next_ticks()
            
            for data_point in new_data:
                # Check if we should process this data
                if self.subscription_manager.should_process_data(data_point, datetime.utcnow()):
                    # Add to synchronizer
                    subscription_id = f"{data_point.symbol}_{data_point.data_type.__name__}"
                    self.synchronizer.add_data(subscription_id, data_point)
                    
                    # Store in pending data (latest data per symbol)
                    pending_data[data_point.symbol] = data_point
                    self._data_points_processed += 1
                    
        except Exception as e:
            self._handle_error(f"Error processing incoming data: {e}")
    
    def _create_slice(self, data: Dict[Symbol, BaseData], slice_time: datetime) -> Slice:
        """Create a data slice from pending data."""
        # Convert to the format expected by Slice
        slice_data: Dict[Symbol, List[BaseData]] = {}
        
        for symbol, data_point in data.items():
            slice_data[symbol] = [data_point]
        
        return Slice(slice_time, slice_data)
    
    def _handle_new_data(self, slice_obj: Slice):
        """Handle new data from the data feed."""
        # This could be used for additional processing if needed
        pass
    
    def _handle_error(self, error_message: str):
        """Handle errors."""
        self._errors_count += 1
        print(f"DataManager Error: {error_message}")
        
        if self.error_callback:
            try:
                self.error_callback(error_message)
            except Exception as e:
                print(f"Error in error callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data manager statistics."""
        return {
            'data_points_processed': self._data_points_processed,
            'slices_created': self._slices_created,
            'errors_count': self._errors_count,
            'active_subscriptions': len(self.subscription_manager),
            'queue_size': self._data_queue.qsize(),
            'processed_queue_size': self._processed_data_queue.qsize(),
            'subscription_stats': self.subscription_manager.get_subscription_statistics()
        }
    
    def stop(self):
        """Stop the data manager."""
        self._stop_processing = True
        
        # Wait for processing thread to finish
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=5.0)
        
        # Clean up data feed
        if self._data_feed:
            self._data_feed.dispose()
    
    def dispose(self):
        """Clean up resources."""
        self.stop()
        
        # Clear queues
        while not self._data_queue.empty():
            try:
                self._data_queue.get_nowait()
            except Empty:
                break
        
        while not self._processed_data_queue.empty():
            try:
                self._processed_data_queue.get_nowait()
            except Empty:
                break
        
        # Clear managers
        self.subscription_manager.clear()
        self.synchronizer.clear()


class BacktestDataManager(DataManager):
    """
    Data manager specifically for backtesting scenarios.
    """
    
    def __init__(self, data_folder: str):
        super().__init__()
        self.data_folder = data_folder
        self._current_time = datetime.utcnow()
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._time_step = timedelta(minutes=1)  # Default time step
    
    def initialize_backtest(self, start_time: datetime, end_time: datetime, 
                           time_step: timedelta = None):
        """Initialize for backtesting with specific time range."""
        self._start_time = start_time
        self._end_time = end_time
        self._current_time = start_time
        
        if time_step:
            self._time_step = time_step
        
        # Create file system data feed
        data_feed = FileSystemDataFeed(self.data_folder)
        data_feed.set_time_range(start_time, end_time)
        
        # Create file system history provider
        history_provider = FileSystemHistoryProvider(self.data_folder)
        
        # Initialize base data manager
        self.initialize(data_feed, history_provider)
    
    def step_forward(self) -> Optional[Slice]:
        """Step forward in time and get the next data slice."""
        if not self._data_feed or not isinstance(self._data_feed, FileSystemDataFeed):
            return None
        
        if self._end_time and self._current_time >= self._end_time:
            return None  # Backtest finished
        
        # Get data for current time
        data = self._data_feed.get_next_ticks()
        
        if data:
            slice_obj = self._data_feed.create_slice(data)
            self._current_time = slice_obj.time
            return slice_obj
        elif self._data_feed.is_finished:
            return None  # No more data
        else:
            # Advance time and try again
            self._current_time += self._time_step
            return self.step_forward()
    
    @property
    def current_time(self) -> datetime:
        """Get current backtest time."""
        return self._current_time
    
    @property
    def is_finished(self) -> bool:
        """Check if backtest is finished."""
        if self._end_time and self._current_time >= self._end_time:
            return True
        
        if self._data_feed and isinstance(self._data_feed, FileSystemDataFeed):
            return self._data_feed.is_finished
        
        return False


class LiveDataManager(DataManager):
    """
    Data manager specifically for live trading scenarios.
    """
    
    def __init__(self, data_queue_handler):
        super().__init__()
        self.data_queue_handler = data_queue_handler
        self._heartbeat_interval = timedelta(seconds=30)
        self._last_heartbeat = datetime.utcnow()
    
    def initialize_live_trading(self, history_provider: HistoryProvider = None):
        """Initialize for live trading."""
        # Create live trading data feed
        data_feed = LiveTradingDataFeed(self.data_queue_handler)
        
        # Initialize base data manager
        self.initialize(data_feed, history_provider)
    
    def _data_processing_worker(self):
        """Override data processing worker for live trading specifics."""
        super()._data_processing_worker()
        
        # Additional live trading logic could go here
        # Such as connection monitoring, heartbeat checks, etc.
    
    def check_connection_health(self) -> bool:
        """Check if the data connection is healthy."""
        current_time = datetime.utcnow()
        
        # Check if we've received data recently
        if current_time - self._last_heartbeat > self._heartbeat_interval:
            return False
        
        # Additional health checks could go here
        return True
    
    def reconnect(self) -> bool:
        """Attempt to reconnect the data feed."""
        try:
            if self._data_feed:
                self._data_feed.dispose()
            
            # Recreate data feed
            data_feed = LiveTradingDataFeed(self.data_queue_handler)
            if data_feed.initialize():
                self._data_feed = data_feed
                self._data_feed.new_data_available = self._handle_new_data
                return True
            
        except Exception as e:
            self._handle_error(f"Reconnection failed: {e}")
        
        return False