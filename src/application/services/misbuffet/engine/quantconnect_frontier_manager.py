"""
QuantConnect-style Frontier Time Manager for Misbuffet Service

Manages algorithm frontier time progression and coordinates with existing misbuffet 
engine handlers to provide QuantConnect-compatible time management functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from threading import Lock

from ..common.enums import Resolution
from ..common.symbol import Symbol  
from ..common.data_types import Slice
from .interfaces import ITimeProvider
from ..data.quantconnect_data_manager import QuantConnectDataManager
from ..data.quantconnect_history_provider import QuantConnectHistoryProvider, QuantConnectSliceBuilder


class FrontierTimeManager:
    """
    Manages algorithm frontier time progression for QuantConnect-style backtesting.
    
    Coordinates with existing misbuffet engine components to provide:
    - Time-based data slice creation  
    - Market time validation
    - Algorithm time synchronization
    - Event scheduling and callbacks
    """
    
    def __init__(self, data_manager: Optional[QuantConnectDataManager] = None,
                 history_provider: Optional[QuantConnectHistoryProvider] = None,
                 time_provider: Optional[ITimeProvider] = None):
        """
        Initialize the frontier time manager.
        
        Args:
            data_manager: QuantConnect data manager for subscriptions
            history_provider: History provider for backfill data
            time_provider: Time provider interface
        """
        self._logger = logging.getLogger("misbuffet.frontier_time_manager")
        
        # Core components
        self._data_manager = data_manager
        self._history_provider = history_provider
        self._time_provider = time_provider
        self._slice_builder = QuantConnectSliceBuilder(history_provider)
        
        # Time management
        self._frontier_time: Optional[datetime] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._current_resolution: Resolution = Resolution.DAILY
        
        # Event system  
        self._time_callbacks: Dict[datetime, List[Callable]] = {}
        self._recurring_callbacks: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        # Market calendar integration
        self._market_open_times: Dict[str, str] = {
            "USA": "09:30:00",
            "NYSE": "09:30:00", 
            "NASDAQ": "09:30:00"
        }
        self._market_close_times: Dict[str, str] = {
            "USA": "16:00:00",
            "NYSE": "16:00:00",
            "NASDAQ": "16:00:00"
        }
        
        # Performance tracking
        self._slice_count = 0
        self._callback_count = 0
        
        self._logger.info("Frontier time manager initialized")
    
    def initialize(self, start_time: datetime, end_time: datetime, 
                  resolution: Resolution = Resolution.DAILY) -> bool:
        """
        Initialize the frontier time manager for backtesting.
        
        Args:
            start_time: Backtest start time
            end_time: Backtest end time  
            resolution: Time resolution for progression
            
        Returns:
            True if initialization successful
        """
        try:
            with self._lock:
                self._start_time = start_time
                self._end_time = end_time
                self._frontier_time = start_time
                self._current_resolution = resolution
                
                # Clear existing callbacks
                self._time_callbacks.clear()
                self._recurring_callbacks.clear()
                
                self._logger.info(f"Frontier time manager initialized: {start_time} to {end_time} "
                                f"at {resolution.value} resolution")
                return True
                
        except Exception as e:
            self._logger.error(f"Error initializing frontier time manager: {e}")
            return False
    
    def get_frontier_time(self) -> Optional[datetime]:
        """Get current algorithm frontier time."""
        return self._frontier_time
    
    def set_frontier_time(self, time: datetime) -> None:
        """Set algorithm frontier time."""
        with self._lock:
            self._frontier_time = time
            if self._data_manager:
                self._data_manager.set_frontier_time(time)
    
    def advance_time(self, universe: Optional[List[str]] = None) -> Optional[Slice]:
        """
        Advance frontier time by one resolution period and create data slice.
        
        Args:
            universe: List of symbols to include in slice
            
        Returns:
            Data slice for the new frontier time, None if end reached
        """
        try:
            with self._lock:
                if not self._frontier_time or not self._end_time:
                    return None
                
                # Check if we've reached the end
                if self._frontier_time >= self._end_time:
                    self._logger.info("Frontier time reached end of backtest period")
                    return None
                
                # Advance time by resolution
                next_time = self._calculate_next_time(self._frontier_time, self._current_resolution)
                
                # Validate trading time
                if not self.is_market_open_time(next_time):
                    # Skip to next trading time
                    next_time = self._find_next_trading_time(next_time)
                
                if next_time > self._end_time:
                    return None
                
                # Update frontier time
                previous_time = self._frontier_time
                self._frontier_time = next_time
                
                # Update data manager
                if self._data_manager:
                    self._data_manager.set_frontier_time(next_time)
                
                # Process scheduled callbacks
                self._process_time_callbacks(next_time)
                
                # Create data slice
                slice_obj = self.create_current_slice(universe)
                self._slice_count += 1
                
                if self._slice_count % 100 == 0:
                    self._logger.debug(f"Processed {self._slice_count} time slices, "
                                     f"current time: {next_time}")
                
                return slice_obj
                
        except Exception as e:
            self._logger.error(f"Error advancing time: {e}")
            return None
    
    def create_current_slice(self, universe: Optional[List[str]] = None) -> Slice:
        """
        Create data slice for current frontier time.
        
        Args:
            universe: List of symbols to include
            
        Returns:
            Data slice for current time
        """
        try:
            if not self._frontier_time:
                return Slice(time=datetime.now())
            
            # Use data manager if available
            if self._data_manager:
                return self._data_manager.create_data_slice(self._frontier_time, universe)
            
            # Fallback to slice builder with history provider
            if self._history_provider and universe:
                symbols = [Symbol.create_equity(ticker) for ticker in universe]
                return self._slice_builder.build_slice_from_history(self._frontier_time, symbols)
            
            # Return empty slice
            return Slice(time=self._frontier_time)
            
        except Exception as e:
            self._logger.error(f"Error creating current slice: {e}")
            return Slice(time=self._frontier_time or datetime.now())
    
    def is_market_open_time(self, time: datetime, market: str = "USA") -> bool:
        """
        Check if a given time is during market hours.
        
        Args:
            time: Time to check
            market: Market identifier
            
        Returns:
            True if market is open
        """
        try:
            # Check if it's a trading day
            if not self.is_trading_day(time.date()):
                return False
            
            # Get market hours
            market_open_str = self._market_open_times.get(market, "09:30:00")
            market_close_str = self._market_close_times.get(market, "16:00:00")
            
            # Create datetime objects for market open/close
            market_open = datetime.combine(time.date(), 
                                         datetime.strptime(market_open_str, "%H:%M:%S").time())
            market_close = datetime.combine(time.date(),
                                          datetime.strptime(market_close_str, "%H:%M:%S").time())
            
            return market_open <= time <= market_close
            
        except Exception:
            return False
    
    def is_trading_day(self, date) -> bool:
        """
        Check if a date is a valid trading day.
        
        Args:
            date: Date to check (datetime.date object)
            
        Returns:
            True if it's a trading day
        """
        try:
            # Weekend check
            if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Major holidays (simplified - could be enhanced with market calendar)
            major_holidays = {
                (1, 1),    # New Year's Day
                (7, 4),    # Independence Day
                (12, 25),  # Christmas
            }
            
            if (date.month, date.day) in major_holidays:
                return False
            
            return True
            
        except Exception:
            return False
    
    def schedule_callback(self, time: datetime, callback: Callable) -> str:
        """
        Schedule a callback to be executed at a specific time.
        
        Args:
            time: Time to execute callback
            callback: Function to call
            
        Returns:
            Callback ID for cancellation
        """
        try:
            with self._lock:
                if time not in self._time_callbacks:
                    self._time_callbacks[time] = []
                
                self._time_callbacks[time].append(callback)
                callback_id = f"scheduled_{time.timestamp()}_{len(self._time_callbacks[time])}"
                
                self._logger.debug(f"Scheduled callback {callback_id} for {time}")
                return callback_id
                
        except Exception as e:
            self._logger.error(f"Error scheduling callback: {e}")
            return ""
    
    def schedule_recurring_callback(self, interval: timedelta, callback: Callable, 
                                  start_time: Optional[datetime] = None) -> str:
        """
        Schedule a recurring callback.
        
        Args:
            interval: Time interval between calls
            callback: Function to call
            start_time: First execution time (default: current frontier time)
            
        Returns:
            Callback ID for cancellation
        """
        try:
            with self._lock:
                start_time = start_time or self._frontier_time or datetime.now()
                callback_id = f"recurring_{start_time.timestamp()}_{len(self._recurring_callbacks)}"
                
                self._recurring_callbacks[callback_id] = {
                    'callback': callback,
                    'interval': interval,
                    'next_time': start_time,
                    'active': True
                }
                
                self._logger.debug(f"Scheduled recurring callback {callback_id} "
                                 f"every {interval} starting at {start_time}")
                return callback_id
                
        except Exception as e:
            self._logger.error(f"Error scheduling recurring callback: {e}")
            return ""
    
    def cancel_callback(self, callback_id: str) -> bool:
        """Cancel a scheduled callback."""
        try:
            with self._lock:
                if callback_id.startswith("recurring_"):
                    if callback_id in self._recurring_callbacks:
                        self._recurring_callbacks[callback_id]['active'] = False
                        self._logger.debug(f"Cancelled recurring callback {callback_id}")
                        return True
                else:
                    # Handle scheduled callbacks (more complex - would need reverse lookup)
                    pass
                
                return False
                
        except Exception as e:
            self._logger.error(f"Error cancelling callback: {e}")
            return False
    
    def get_market_hours(self, date: datetime, market: str = "USA") -> Dict[str, datetime]:
        """
        Get market open/close times for a specific date.
        
        Args:
            date: Date to get hours for
            market: Market identifier
            
        Returns:
            Dictionary with 'open' and 'close' datetime objects
        """
        try:
            market_open_str = self._market_open_times.get(market, "09:30:00")
            market_close_str = self._market_close_times.get(market, "16:00:00")
            
            market_open = datetime.combine(date.date(),
                                         datetime.strptime(market_open_str, "%H:%M:%S").time())
            market_close = datetime.combine(date.date(), 
                                          datetime.strptime(market_close_str, "%H:%M:%S").time())
            
            return {
                'open': market_open,
                'close': market_close
            }
            
        except Exception as e:
            self._logger.error(f"Error getting market hours: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get frontier time manager statistics."""
        return {
            'current_frontier_time': self._frontier_time,
            'start_time': self._start_time,
            'end_time': self._end_time,
            'current_resolution': self._current_resolution.value if self._current_resolution else None,
            'slices_created': self._slice_count,
            'callbacks_executed': self._callback_count,
            'scheduled_callbacks': len(self._time_callbacks),
            'recurring_callbacks': len(self._recurring_callbacks),
            'progress_percentage': self._calculate_progress_percentage()
        }
    
    def dispose(self) -> None:
        """Clean up resources."""
        try:
            with self._lock:
                self._time_callbacks.clear()
                self._recurring_callbacks.clear()
                
            self._logger.info("Frontier time manager disposed")
            
        except Exception as e:
            self._logger.error(f"Error disposing frontier time manager: {e}")
    
    # Private methods
    
    def _calculate_next_time(self, current_time: datetime, resolution: Resolution) -> datetime:
        """Calculate the next time based on resolution."""
        try:
            if resolution == Resolution.SECOND:
                return current_time + timedelta(seconds=1)
            elif resolution == Resolution.MINUTE:
                return current_time + timedelta(minutes=1) 
            elif resolution == Resolution.HOUR:
                return current_time + timedelta(hours=1)
            elif resolution == Resolution.DAILY:
                return current_time + timedelta(days=1)
            elif resolution == Resolution.WEEKLY:
                return current_time + timedelta(weeks=1)
            else:
                return current_time + timedelta(days=1)  # Default to daily
                
        except Exception:
            return current_time + timedelta(days=1)
    
    def _find_next_trading_time(self, time: datetime) -> datetime:
        """Find the next valid trading time."""
        try:
            # If it's a weekend, skip to Monday
            while not self.is_trading_day(time.date()):
                time += timedelta(days=1)
            
            # Set to market open time if before market hours
            if not self.is_market_open_time(time):
                market_open_str = self._market_open_times.get("USA", "09:30:00")
                market_open_time = datetime.strptime(market_open_str, "%H:%M:%S").time()
                time = datetime.combine(time.date(), market_open_time)
            
            return time
            
        except Exception:
            return time
    
    def _process_time_callbacks(self, current_time: datetime) -> None:
        """Process scheduled and recurring callbacks."""
        try:
            # Process scheduled callbacks
            if current_time in self._time_callbacks:
                callbacks = self._time_callbacks[current_time]
                for callback in callbacks:
                    try:
                        callback()
                        self._callback_count += 1
                    except Exception as e:
                        self._logger.error(f"Error executing scheduled callback: {e}")
                
                # Remove executed callbacks
                del self._time_callbacks[current_time]
            
            # Process recurring callbacks
            for callback_id, callback_info in list(self._recurring_callbacks.items()):
                if not callback_info['active']:
                    continue
                
                if current_time >= callback_info['next_time']:
                    try:
                        callback_info['callback']()
                        self._callback_count += 1
                        
                        # Schedule next execution
                        callback_info['next_time'] = current_time + callback_info['interval']
                        
                    except Exception as e:
                        self._logger.error(f"Error executing recurring callback {callback_id}: {e}")
            
        except Exception as e:
            self._logger.error(f"Error processing time callbacks: {e}")
    
    def _calculate_progress_percentage(self) -> float:
        """Calculate backtest progress percentage."""
        try:
            if not self._start_time or not self._end_time or not self._frontier_time:
                return 0.0
            
            total_duration = (self._end_time - self._start_time).total_seconds()
            current_duration = (self._frontier_time - self._start_time).total_seconds()
            
            if total_duration <= 0:
                return 100.0
            
            return min(100.0, max(0.0, (current_duration / total_duration) * 100.0))
            
        except Exception:
            return 0.0


class AlgorithmTimeCoordinator:
    """
    Coordinates algorithm time with frontier time manager and existing engine handlers.
    """
    
    def __init__(self, frontier_manager: FrontierTimeManager, 
                 algorithm: Optional[Any] = None):
        """
        Initialize the time coordinator.
        
        Args:
            frontier_manager: Frontier time manager
            algorithm: Algorithm instance to coordinate with
        """
        self._logger = logging.getLogger("misbuffet.time_coordinator")
        self._frontier_manager = frontier_manager
        self._algorithm = algorithm
        
        # Time synchronization
        self._last_sync_time: Optional[datetime] = None
        self._sync_callbacks: List[Callable[[datetime], None]] = []
    
    def sync_algorithm_time(self) -> None:
        """Synchronize algorithm time with frontier time."""
        try:
            frontier_time = self._frontier_manager.get_frontier_time()
            if frontier_time and self._algorithm:
                # Update algorithm time property
                if hasattr(self._algorithm, 'time'):
                    self._algorithm.time = frontier_time
                
                # Execute sync callbacks
                for callback in self._sync_callbacks:
                    try:
                        callback(frontier_time)
                    except Exception as e:
                        self._logger.error(f"Error in sync callback: {e}")
                
                self._last_sync_time = frontier_time
                
        except Exception as e:
            self._logger.error(f"Error synchronizing algorithm time: {e}")
    
    def add_sync_callback(self, callback: Callable[[datetime], None]) -> None:
        """Add a callback to be executed on time sync."""
        self._sync_callbacks.append(callback)
    
    def remove_sync_callback(self, callback: Callable[[datetime], None]) -> None:
        """Remove a sync callback."""
        if callback in self._sync_callbacks:
            self._sync_callbacks.remove(callback)