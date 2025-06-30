"""
Data feed implementations for QuantConnect Lean Engine Python implementation.
Handles data delivery for backtesting and live trading.
"""

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Iterator
from pathlib import Path
import csv
import json

from .interfaces import IDataFeed, IAlgorithm
from .engine_node_packet import EngineNodePacket
from .enums import ComponentState, DataFeedMode

# Import from common and data modules using relative imports
from ..common import BaseData, Symbol, Resolution, SecurityType
from ..data import SubscriptionManager, DataReader


class BaseDataFeed(IDataFeed, ABC):
    """Base class for all data feed implementations."""
    
    def __init__(self):
        """Initialize the base data feed."""
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._subscription_manager: Optional[SubscriptionManager] = None
        self._state = ComponentState.CREATED
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Data tracking
        self._subscriptions: Dict[str, 'SubscriptionDataConfig'] = {}
        self._data_queue: List[BaseData] = []
        self._last_data_time: Optional[datetime] = None
        self._is_active = False
        
        self._logger.info(f"Initialized {self.__class__.__name__}")
    
    def initialize(self, algorithm: IAlgorithm, job: EngineNodePacket) -> bool:
        """Initialize the data feed with algorithm and job parameters."""
        try:
            with self._lock:
                if self._state != ComponentState.CREATED:
                    self._logger.warning(f"Data feed already initialized with state: {self._state}")
                    return False
                
                self._state = ComponentState.INITIALIZING
                self._algorithm = algorithm
                self._job = job
                
                self._logger.info("Initializing data feed")
                
                # Initialize subscription manager
                self._subscription_manager = SubscriptionManager()
                
                # Perform specific initialization
                success = self._initialize_specific()
                
                if success:
                    self._state = ComponentState.INITIALIZED
                    self._is_active = True
                    self._logger.info("Data feed initialization completed")
                else:
                    self._state = ComponentState.ERROR
                    self._logger.error("Data feed initialization failed")
                
                return success
                
        except Exception as e:
            self._logger.error(f"Error during data feed initialization: {e}")
            self._state = ComponentState.ERROR
            return False
    
    def create_subscription(self, symbol: Symbol, resolution: Resolution) -> 'SubscriptionDataConfig':
        """Create a data subscription for the given symbol and resolution."""
        try:
            with self._lock:
                subscription_key = f"{symbol.value}_{resolution.name}"
                
                if subscription_key in self._subscriptions:
                    self._logger.info(f"Subscription already exists: {subscription_key}")
                    return self._subscriptions[subscription_key]
                
                # Create subscription config
                config = SubscriptionDataConfig(
                    symbol=symbol,
                    resolution=resolution,
                    data_type=BaseData,
                    security_type=symbol.security_type if hasattr(symbol, 'security_type') else SecurityType.EQUITY
                )
                
                self._subscriptions[subscription_key] = config
                
                # Perform specific subscription setup
                self._setup_subscription(config)
                
                self._logger.info(f"Created subscription: {subscription_key}")
                return config
                
        except Exception as e:
            self._logger.error(f"Error creating subscription: {e}")
            raise
    
    def remove_subscription(self, config: 'SubscriptionDataConfig') -> bool:
        """Remove a data subscription."""
        try:
            with self._lock:
                subscription_key = f"{config.symbol.value}_{config.resolution.name}"
                
                if subscription_key not in self._subscriptions:
                    self._logger.warning(f"Subscription not found: {subscription_key}")
                    return False
                
                # Perform specific cleanup
                self._cleanup_subscription(config)
                
                # Remove from tracking
                del self._subscriptions[subscription_key]
                
                self._logger.info(f"Removed subscription: {subscription_key}")
                return True
                
        except Exception as e:
            self._logger.error(f"Error removing subscription: {e}")
            return False
    
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of data ticks."""
        try:
            with self._lock:
                if not self._is_active:
                    return []
                
                # Get data from specific implementation
                data_points = self._get_next_data_points()
                
                # Update tracking
                if data_points:
                    self._last_data_time = max(dp.end_time for dp in data_points)
                
                return data_points
                
        except Exception as e:
            self._logger.error(f"Error getting next ticks: {e}")
            return []
    
    def is_active(self) -> bool:
        """Check if the data feed is active and running."""
        return self._is_active and self._state == ComponentState.INITIALIZED
    
    def exit(self) -> None:
        """Exit and cleanup the data feed."""
        try:
            with self._lock:
                if self._state == ComponentState.DISPOSED:
                    return
                
                self._logger.info("Exiting data feed")
                self._is_active = False
                
                # Cleanup subscriptions
                for config in list(self._subscriptions.values()):
                    self._cleanup_subscription(config)
                
                self._subscriptions.clear()
                
                # Perform specific cleanup
                self._cleanup_specific()
                
                self._state = ComponentState.DISPOSED
                self._logger.info("Data feed exited")
                
        except Exception as e:
            self._logger.error(f"Error during data feed exit: {e}")
    
    # Abstract methods for specific implementations
    
    @abstractmethod
    def _initialize_specific(self) -> bool:
        """Perform specific initialization. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_next_data_points(self) -> List[BaseData]:
        """Get next data points. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _setup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Setup a specific subscription. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cleanup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Cleanup a specific subscription. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cleanup_specific(self) -> None:
        """Perform specific cleanup. Must be implemented by subclasses."""
        pass


class FileSystemDataFeed(BaseDataFeed):
    """File system data feed for backtesting with historical data."""
    
    def __init__(self):
        """Initialize the file system data feed."""
        super().__init__()
        self._data_readers: Dict[str, DataReader] = {}
        self._data_files: Dict[str, Path] = {}
        self._current_data_index: Dict[str, int] = {}
        self._all_data: Dict[str, List[BaseData]] = {}
    
    def _initialize_specific(self) -> bool:
        """Initialize file system specific components."""
        try:
            if not self._job:
                return False
            
            # Verify data folder exists
            data_folder = Path(self._job.data_folder)
            if not data_folder.exists():
                self._logger.warning(f"Data folder does not exist: {data_folder}")
                # Create it for now
                data_folder.mkdir(parents=True, exist_ok=True)
            
            self._logger.info(f"Using data folder: {data_folder}")
            return True
            
        except Exception as e:
            self._logger.error(f"File system data feed initialization failed: {e}")
            return False
    
    def _get_next_data_points(self) -> List[BaseData]:
        """Get next data points from file system."""
        try:
            data_points = []
            
            # Get next data point from each subscription
            for subscription_key, config in self._subscriptions.items():
                if subscription_key in self._all_data:
                    data_list = self._all_data[subscription_key]
                    index = self._current_data_index.get(subscription_key, 0)
                    
                    if index < len(data_list):
                        data_points.append(data_list[index])
                        self._current_data_index[subscription_key] = index + 1
            
            # Sort by time
            data_points.sort(key=lambda x: x.end_time)
            
            return data_points
            
        except Exception as e:
            self._logger.error(f"Error getting file system data points: {e}")
            return []
    
    def _setup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Setup a file system subscription."""
        try:
            subscription_key = f"{config.symbol.value}_{config.resolution.name}"
            
            # Find data file for this symbol
            data_file = self._find_data_file(config.symbol, config.resolution)
            if not data_file:
                self._logger.warning(f"No data file found for {config.symbol.value}")
                return
            
            self._data_files[subscription_key] = data_file
            
            # Load data from file
            data_points = self._load_data_from_file(data_file, config)
            self._all_data[subscription_key] = data_points
            self._current_data_index[subscription_key] = 0
            
            self._logger.info(f"Loaded {len(data_points)} data points for {subscription_key}")
            
        except Exception as e:
            self._logger.error(f"Error setting up file subscription: {e}")
    
    def _cleanup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Cleanup a file system subscription."""
        try:
            subscription_key = f"{config.symbol.value}_{config.resolution.name}"
            
            # Remove from tracking
            self._data_files.pop(subscription_key, None)
            self._all_data.pop(subscription_key, None)  
            self._current_data_index.pop(subscription_key, None)
            
        except Exception as e:
            self._logger.error(f"Error cleaning up file subscription: {e}")
    
    def _cleanup_specific(self) -> None:
        """Cleanup file system specific resources."""
        try:
            self._data_readers.clear()
            self._data_files.clear()
            self._current_data_index.clear()
            self._all_data.clear()
            
        except Exception as e:
            self._logger.error(f"Error in file system cleanup: {e}")
    
    def _find_data_file(self, symbol: Symbol, resolution: Resolution) -> Optional[Path]:
        """Find data file for the given symbol and resolution."""
        try:
            data_folder = Path(self._job.data_folder)
            
            # Try common file naming patterns
            possible_names = [
                f"{symbol.value}_{resolution.name.lower()}.csv",
                f"{symbol.value}.csv",
                f"{symbol.value}_{resolution.name}.csv",
                f"{symbol.value.lower()}_{resolution.name.lower()}.csv"
            ]
            
            for name in possible_names:
                file_path = data_folder / name
                if file_path.exists():
                    return file_path
            
            # Look in subdirectories
            for subdir in data_folder.iterdir():
                if subdir.is_dir():
                    for name in possible_names:
                        file_path = subdir / name
                        if file_path.exists():
                            return file_path
            
            return None
            
        except Exception as e:
            self._logger.error(f"Error finding data file: {e}")
            return None
    
    def _load_data_from_file(self, file_path: Path, config: 'SubscriptionDataConfig') -> List[BaseData]:
        """Load data from a file."""
        try:
            data_points = []
            
            if file_path.suffix.lower() == '.csv':
                data_points = self._load_csv_data(file_path, config)
            elif file_path.suffix.lower() == '.json':
                data_points = self._load_json_data(file_path, config)
            else:
                self._logger.warning(f"Unsupported file format: {file_path.suffix}")
            
            return data_points
            
        except Exception as e:
            self._logger.error(f"Error loading data from file {file_path}: {e}")
            return []
    
    def _load_csv_data(self, file_path: Path, config: 'SubscriptionDataConfig') -> List[BaseData]:
        """Load data from CSV file."""
        try:
            data_points = []
            
            with open(file_path, 'r') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        # Parse common CSV formats
                        data_point = self._parse_csv_row(row, config)
                        if data_point:
                            data_points.append(data_point)
                    except Exception as e:
                        self._logger.warning(f"Error parsing CSV row: {e}")
                        continue
            
            # Sort by time
            data_points.sort(key=lambda x: x.end_time)
            return data_points
            
        except Exception as e:
            self._logger.error(f"Error loading CSV data: {e}")
            return []
    
    def _parse_csv_row(self, row: Dict[str, str], config: 'SubscriptionDataConfig') -> Optional[BaseData]:
        """Parse a CSV row into a BaseData object."""
        try:
            # Common field mappings
            time_fields = ['time', 'timestamp', 'date', 'datetime']
            value_fields = ['value', 'price', 'close', 'last']
            
            # Find time field
            time_str = None
            for field in time_fields:
                if field in row and row[field]:
                    time_str = row[field]
                    break
            
            if not time_str:
                return None
            
            # Parse time
            try:
                end_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except:
                try:
                    end_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        end_time = datetime.strptime(time_str, '%Y-%m-%d')
                    except:
                        self._logger.warning(f"Could not parse time: {time_str}")
                        return None
            
            # Find value field
            value = None
            for field in value_fields:
                if field in row and row[field]:
                    try:
                        value = float(row[field])
                        break
                    except:
                        continue
            
            if value is None:
                return None
            
            # Create BaseData object
            data_point = BaseData(
                symbol=config.symbol,
                time=end_time,
                end_time=end_time,
                value=value
            )
            
            return data_point
            
        except Exception as e:
            self._logger.warning(f"Error parsing CSV row: {e}")
            return None
    
    def _load_json_data(self, file_path: Path, config: 'SubscriptionDataConfig') -> List[BaseData]:
        """Load data from JSON file."""
        try:
            data_points = []
            
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                if isinstance(data, list):
                    for item in data:
                        data_point = self._parse_json_item(item, config)
                        if data_point:
                            data_points.append(data_point)
                elif isinstance(data, dict) and 'data' in data:
                    for item in data['data']:
                        data_point = self._parse_json_item(item, config)
                        if data_point:
                            data_points.append(data_point)
            
            # Sort by time
            data_points.sort(key=lambda x: x.end_time)
            return data_points
            
        except Exception as e:
            self._logger.error(f"Error loading JSON data: {e}")
            return []
    
    def _parse_json_item(self, item: Dict, config: 'SubscriptionDataConfig') -> Optional[BaseData]:
        """Parse a JSON item into a BaseData object."""
        try:
            # This is a simplified implementation
            # In practice, you'd need to handle various JSON formats
            
            time_str = item.get('time') or item.get('timestamp') or item.get('date')
            value = item.get('value') or item.get('price') or item.get('close')
            
            if not time_str or value is None:
                return None
            
            end_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            data_point = BaseData(
                symbol=config.symbol,
                time=end_time,
                end_time=end_time,
                value=float(value)
            )
            
            return data_point
            
        except Exception as e:
            self._logger.warning(f"Error parsing JSON item: {e}")
            return None


class BacktestingDataFeed(FileSystemDataFeed):
    """Specialized data feed for backtesting with additional features."""
    
    def __init__(self):
        """Initialize the backtesting data feed."""
        super().__init__()
        self._backtest_start_time: Optional[datetime] = None
        self._backtest_end_time: Optional[datetime] = None
        self._current_backtest_time: Optional[datetime] = None
    
    def _initialize_specific(self) -> bool:
        """Initialize backtesting specific components."""
        try:
            if not super()._initialize_specific():
                return False
            
            if self._job:
                self._backtest_start_time = self._job.start_date
                self._backtest_end_time = self._job.end_date
                self._current_backtest_time = self._backtest_start_time
            
            self._logger.info(f"Backtesting period: {self._backtest_start_time} to {self._backtest_end_time}")
            return True
            
        except Exception as e:
            self._logger.error(f"Backtesting data feed initialization failed: {e}")
            return False
    
    def _get_next_data_points(self) -> List[BaseData]:
        """Get next data points for backtesting with time filtering."""
        try:
            # Get data points from parent
            data_points = super()._get_next_data_points()
            
            # Filter by backtest time range
            if self._backtest_start_time and self._backtest_end_time:
                data_points = [
                    dp for dp in data_points 
                    if self._backtest_start_time <= dp.end_time <= self._backtest_end_time
                ]
            
            # Update current backtest time
            if data_points:
                self._current_backtest_time = max(dp.end_time for dp in data_points)
            
            return data_points
            
        except Exception as e:
            self._logger.error(f"Error getting backtesting data points: {e}")
            return []


class LiveDataFeed(BaseDataFeed):
    """Live data feed for real-time trading."""
    
    def __init__(self):
        """Initialize the live data feed."""
        super().__init__()
        self._data_provider: Optional[Any] = None
        self._streaming_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._live_data_queue: List[BaseData] = []
        self._queue_lock = threading.Lock()
    
    def _initialize_specific(self) -> bool:
        """Initialize live data feed specific components."""
        try:
            # Initialize live data provider (placeholder)
            # In practice, this would connect to a live data source
            self._logger.info("Initializing live data provider")
            
            # Start streaming thread
            self._start_streaming()
            
            return True
            
        except Exception as e:
            self._logger.error(f"Live data feed initialization failed: {e}")
            return False
    
    def _get_next_data_points(self) -> List[BaseData]:
        """Get next data points from live stream."""
        try:
            with self._queue_lock:
                data_points = self._live_data_queue.copy()
                self._live_data_queue.clear()
                return data_points
                
        except Exception as e:
            self._logger.error(f"Error getting live data points: {e}")
            return []
    
    def _setup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Setup a live data subscription."""
        try:
            # In practice, this would subscribe to live data for the symbol
            self._logger.info(f"Setting up live subscription for {config.symbol.value}")
            
        except Exception as e:
            self._logger.error(f"Error setting up live subscription: {e}")
    
    def _cleanup_subscription(self, config: 'SubscriptionDataConfig') -> None:
        """Cleanup a live data subscription."""
        try:
            # In practice, this would unsubscribe from live data
            self._logger.info(f"Cleaning up live subscription for {config.symbol.value}")
            
        except Exception as e:
            self._logger.error(f"Error cleaning up live subscription: {e}")
    
    def _cleanup_specific(self) -> None:
        """Cleanup live data feed specific resources."""
        try:
            self._stop_streaming()
            
        except Exception as e:
            self._logger.error(f"Error in live data feed cleanup: {e}")
    
    def _start_streaming(self) -> None:
        """Start the live data streaming thread."""
        try:
            self._shutdown_event.clear()
            self._streaming_thread = threading.Thread(
                target=self._streaming_loop,
                name="LiveDataStreamingThread"
            )
            self._streaming_thread.daemon = True
            self._streaming_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting streaming: {e}")
    
    def _stop_streaming(self) -> None:
        """Stop the live data streaming thread."""
        try:
            self._shutdown_event.set()
            
            if self._streaming_thread and self._streaming_thread.is_alive():
                self._streaming_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping streaming: {e}")
    
    def _streaming_loop(self) -> None:
        """Main streaming loop for live data."""
        try:
            self._logger.info("Live data streaming started")
            
            while not self._shutdown_event.is_set():
                try:
                    # Simulate receiving live data
                    # In practice, this would receive data from a real data provider
                    time.sleep(1.0)  # Simulate data frequency
                    
                    # Generate sample data for each subscription
                    for subscription_key, config in self._subscriptions.items():
                        sample_data = self._create_sample_data(config)
                        if sample_data:
                            with self._queue_lock:
                                self._live_data_queue.append(sample_data)
                    
                except Exception as e:
                    self._logger.error(f"Error in streaming loop: {e}")
                    time.sleep(5.0)  # Back off on error
            
            self._logger.info("Live data streaming stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in streaming loop: {e}")
    
    def _create_sample_data(self, config: 'SubscriptionDataConfig') -> Optional[BaseData]:
        """Create sample data for testing (replace with real data source)."""
        try:
            import random
            
            # Generate sample price data
            current_time = datetime.utcnow()
            sample_price = 100.0 + random.uniform(-5.0, 5.0)
            
            data_point = BaseData(
                symbol=config.symbol,
                time=current_time,
                end_time=current_time,
                value=sample_price
            )
            
            return data_point
            
        except Exception as e:
            self._logger.warning(f"Error creating sample data: {e}")
            return None


# Helper class for subscription configuration
class SubscriptionDataConfig:
    """Configuration for data subscriptions."""
    
    def __init__(self, symbol: Symbol, resolution: Resolution, 
                 data_type: type, security_type: SecurityType):
        """Initialize subscription configuration."""
        self.symbol = symbol
        self.resolution = resolution
        self.data_type = data_type
        self.security_type = security_type
        self.is_custom_data = False
        self.fill_forward = True
        self.extended_market_hours = False
        
        # Unique identifier
        self.id = f"{symbol.value}_{resolution.name}_{data_type.__name__}"
    
    def __str__(self) -> str:
        """String representation."""
        return f"SubscriptionDataConfig({self.symbol.value}, {self.resolution.name})"
    
    def __repr__(self) -> str:
        """String representation."""
        return self.__str__()