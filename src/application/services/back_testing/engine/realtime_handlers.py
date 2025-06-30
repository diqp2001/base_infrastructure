"""
Real-time handler implementations for QuantConnect Lean Engine Python implementation.
Handles time-based events and scheduling for backtesting and live trading.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
import heapq

from .interfaces import IRealTimeHandler, IAlgorithm
from .engine_node_packet import EngineNodePacket
from .enums import ComponentState, RealTimeMode, ScheduleEventType

# Import from common module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import Time


class EventPriority(Enum):
    """Priority levels for scheduled events."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class ScheduledEvent:
    """Represents a scheduled event in the algorithm."""
    
    name: str
    scheduled_time: datetime
    callback: Callable
    event_type: ScheduleEventType = ScheduleEventType.CUSTOM
    priority: EventPriority = EventPriority.NORMAL
    is_recurring: bool = False
    recurrence_period: Optional[timedelta] = None
    enabled: bool = True
    
    def __lt__(self, other):
        """Less than comparison for priority queue."""
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority.value < other.priority.value
    
    def __eq__(self, other):
        """Equality comparison."""
        return (self.name == other.name and 
                self.scheduled_time == other.scheduled_time)
    
    def __hash__(self):
        """Hash function for set operations."""
        return hash((self.name, self.scheduled_time))


class BaseRealTimeHandler(IRealTimeHandler, ABC):
    """Base class for all real-time handler implementations."""
    
    def __init__(self):
        """Initialize the base real-time handler."""
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._state = ComponentState.CREATED
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Time management
        self._current_time: Optional[datetime] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        
        # Event scheduling
        self._scheduled_events: List[ScheduledEvent] = []  # Min heap
        self._event_lookup: Dict[str, ScheduledEvent] = {}
        self._processing_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Time zones and market hours
        self._time_zone: str = "UTC"
        self._market_hours: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self._events_processed = 0
        self._events_skipped = 0
        
        self._logger.info(f"Initialized {self.__class__.__name__}")
    
    def initialize(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Initialize the real-time handler."""
        try:
            with self._lock:
                if self._state != ComponentState.CREATED:
                    self._logger.warning(f"Real-time handler already initialized with state: {self._state}")
                    return
                
                self._state = ComponentState.INITIALIZING
                self._algorithm = algorithm
                self._job = job
                
                self._logger.info("Initializing real-time handler")
                
                # Extract time configuration
                self._extract_time_configuration(job)
                
                # Initialize market hours
                self._initialize_market_hours()
                
                # Initialize specific components
                self._initialize_specific()
                
                # Start event processing
                self._start_event_processing()
                
                self._state = ComponentState.INITIALIZED
                self._logger.info("Real-time handler initialization completed")
                
        except Exception as e:
            self._logger.error(f"Error during real-time handler initialization: {e}")
            self._state = ComponentState.ERROR
            raise
    
    def set_time(self, time: datetime) -> None:
        """Set the current algorithm time."""
        try:
            with self._lock:
                old_time = self._current_time
                self._current_time = time
                
                # Update algorithm time if available
                if self._algorithm and hasattr(self._algorithm, 'time'):
                    self._algorithm.time = time
                
                # Process time-based events
                self._process_time_events(old_time, time)
                
        except Exception as e:
            self._logger.error(f"Error setting time: {e}")
    
    def scan_past_events(self, time: datetime) -> None:
        """Scan for past events that should be triggered."""
        try:
            with self._lock:
                events_to_process = []
                
                # Find events that should have been triggered
                for event in self._scheduled_events:
                    if event.enabled and event.scheduled_time <= time:
                        events_to_process.append(event)
                
                # Process past events
                for event in events_to_process:
                    self._trigger_event(event)
                
        except Exception as e:
            self._logger.error(f"Error scanning past events: {e}")
    
    def add(self, scheduled_event: ScheduledEvent) -> None:
        """Add a scheduled event."""
        try:
            with self._lock:
                # Check for duplicate names
                if scheduled_event.name in self._event_lookup:
                    self._logger.warning(f"Event with name '{scheduled_event.name}' already exists")
                    return
                
                # Add to heap and lookup
                heapq.heappush(self._scheduled_events, scheduled_event)
                self._event_lookup[scheduled_event.name] = scheduled_event
                
                self._logger.debug(f"Added scheduled event: {scheduled_event.name} at {scheduled_event.scheduled_time}")
                
        except Exception as e:
            self._logger.error(f"Error adding scheduled event: {e}")
    
    def remove(self, scheduled_event: ScheduledEvent) -> None:
        """Remove a scheduled event."""
        try:
            with self._lock:
                # Remove from lookup
                if scheduled_event.name in self._event_lookup:
                    del self._event_lookup[scheduled_event.name]
                
                # Mark as disabled (can't efficiently remove from heap)
                scheduled_event.enabled = False
                
                self._logger.debug(f"Removed scheduled event: {scheduled_event.name}")
                
        except Exception as e:
            self._logger.error(f"Error removing scheduled event: {e}")
    
    def is_active(self) -> bool:
        """Check if the real-time handler is active."""
        return self._state == ComponentState.INITIALIZED and not self._shutdown_event.is_set()
    
    def exit(self) -> None:
        """Exit and cleanup the real-time handler."""
        try:
            with self._lock:
                if self._state == ComponentState.DISPOSED:
                    return
                
                self._logger.info("Exiting real-time handler")
                
                # Stop event processing
                self._stop_event_processing()
                
                # Clear events
                self._scheduled_events.clear()
                self._event_lookup.clear()
                
                # Cleanup specific resources
                self._cleanup_specific()
                
                self._state = ComponentState.DISPOSED
                self._logger.info("Real-time handler exited")
                
        except Exception as e:
            self._logger.error(f"Error during real-time handler exit: {e}")
    
    # Market hours and trading calendar methods
    
    def is_market_open(self, symbol: Optional[str] = None, time: Optional[datetime] = None) -> bool:
        """Check if the market is open for the given symbol and time."""
        try:
            check_time = time or self._current_time
            if not check_time:
                return False
            
            market = symbol or "USA"  # Default to USA market
            
            if market not in self._market_hours:
                return True  # Assume open if no market hours configured
            
            hours = self._market_hours[market]
            
            # Simple implementation - in practice this would be more complex
            weekday = check_time.weekday()
            if weekday >= 5:  # Weekend
                return False
            
            market_open = hours.get('open', '09:30')
            market_close = hours.get('close', '16:00')
            
            current_time_str = check_time.strftime('%H:%M')
            
            return market_open <= current_time_str <= market_close
            
        except Exception as e:
            self._logger.error(f"Error checking market hours: {e}")
            return True  # Default to open on error
    
    def get_next_market_open(self, symbol: Optional[str] = None, time: Optional[datetime] = None) -> datetime:
        """Get the next market open time."""
        try:
            check_time = time or self._current_time or datetime.utcnow()
            
            # Simple implementation - next business day at 9:30 AM
            next_day = check_time.date() + timedelta(days=1)
            while next_day.weekday() >= 5:  # Skip weekends
                next_day += timedelta(days=1)
            
            return datetime.combine(next_day, datetime.strptime('09:30', '%H:%M').time())
            
        except Exception as e:
            self._logger.error(f"Error getting next market open: {e}")
            return check_time + timedelta(days=1)
    
    def get_next_market_close(self, symbol: Optional[str] = None, time: Optional[datetime] = None) -> datetime:
        """Get the next market close time."""
        try:
            check_time = time or self._current_time or datetime.utcnow()
            
            # Simple implementation - today at 4:00 PM if market is open, otherwise next business day
            if self.is_market_open(symbol, check_time):
                close_time = datetime.combine(check_time.date(), datetime.strptime('16:00', '%H:%M').time())
                if close_time > check_time:
                    return close_time
            
            # Next market close
            next_open = self.get_next_market_open(symbol, check_time)
            return datetime.combine(next_open.date(), datetime.strptime('16:00', '%H:%M').time())
            
        except Exception as e:
            self._logger.error(f"Error getting next market close: {e}")
            return check_time + timedelta(hours=1)
    
    # Event scheduling helper methods
    
    def schedule_function(self, name: str, callback: Callable, 
                         scheduled_time: datetime, 
                         priority: EventPriority = EventPriority.NORMAL) -> None:
        """Schedule a function to be called at a specific time."""
        try:
            event = ScheduledEvent(
                name=name,
                scheduled_time=scheduled_time,
                callback=callback,
                event_type=ScheduleEventType.CUSTOM,
                priority=priority
            )
            
            self.add(event)
            
        except Exception as e:
            self._logger.error(f"Error scheduling function: {e}")
    
    def schedule_recurring_function(self, name: str, callback: Callable,
                                  start_time: datetime, period: timedelta,
                                  priority: EventPriority = EventPriority.NORMAL) -> None:
        """Schedule a recurring function."""
        try:
            event = ScheduledEvent(
                name=name,
                scheduled_time=start_time,
                callback=callback,
                event_type=ScheduleEventType.CUSTOM,
                priority=priority,
                is_recurring=True,
                recurrence_period=period
            )
            
            self.add(event)
            
        except Exception as e:
            self._logger.error(f"Error scheduling recurring function: {e}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get real-time handler metrics."""
        with self._lock:
            return {
                'events_scheduled': len(self._scheduled_events),
                'events_processed': self._events_processed,
                'events_skipped': self._events_skipped,
                'active_events': len([e for e in self._scheduled_events if e.enabled])
            }
    
    # Abstract methods for specific implementations
    
    @abstractmethod
    def _initialize_specific(self) -> None:
        """Perform specific initialization. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cleanup_specific(self) -> None:
        """Perform specific cleanup. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _process_time_specific(self, old_time: Optional[datetime], new_time: datetime) -> None:
        """Process time change specific to implementation. Must be implemented by subclasses."""
        pass
    
    # Protected helper methods
    
    def _extract_time_configuration(self, job: EngineNodePacket) -> None:
        """Extract time configuration from job."""
        try:
            self._start_time = job.start_date
            self._end_time = job.end_date
            self._current_time = self._start_time
            
            # Set algorithm time
            if self._algorithm and hasattr(self._algorithm, 'time'):
                self._algorithm.time = self._start_time
            
            self._logger.info(f"Time configuration - Start: {self._start_time}, End: {self._end_time}")
            
        except Exception as e:
            self._logger.error(f"Error extracting time configuration: {e}")
    
    def _initialize_market_hours(self) -> None:
        """Initialize market hours configuration."""
        try:
            # Default market hours (simplified)
            self._market_hours = {
                'USA': {
                    'open': '09:30',
                    'close': '16:00',
                    'timezone': 'America/New_York'
                },
                'LONDON': {
                    'open': '08:00',
                    'close': '16:30',
                    'timezone': 'Europe/London'
                },
                'TOKYO': {
                    'open': '09:00',
                    'close': '15:00',
                    'timezone': 'Asia/Tokyo'
                }
            }
            
        except Exception as e:
            self._logger.error(f"Error initializing market hours: {e}")
    
    def _process_time_events(self, old_time: Optional[datetime], new_time: datetime) -> None:
        """Process time-based events."""
        try:
            # Process scheduled events
            events_to_trigger = []
            
            with self._lock:
                # Find events that should be triggered
                while (self._scheduled_events and 
                       self._scheduled_events[0].enabled and
                       self._scheduled_events[0].scheduled_time <= new_time):
                    
                    event = heapq.heappop(self._scheduled_events)
                    events_to_trigger.append(event)
            
            # Trigger events outside of lock
            for event in events_to_trigger:
                self._trigger_event(event)
            
            # Call specific time processing
            self._process_time_specific(old_time, new_time)
            
        except Exception as e:
            self._logger.error(f"Error processing time events: {e}")
    
    def _trigger_event(self, event: ScheduledEvent) -> None:
        """Trigger a scheduled event."""
        try:
            if not event.enabled:
                self._events_skipped += 1
                return
            
            # Call the event callback
            event.callback()
            self._events_processed += 1
            
            # Handle recurring events
            if event.is_recurring and event.recurrence_period:
                # Schedule next occurrence
                next_event = ScheduledEvent(
                    name=event.name,
                    scheduled_time=event.scheduled_time + event.recurrence_period,
                    callback=event.callback,
                    event_type=event.event_type,
                    priority=event.priority,
                    is_recurring=True,
                    recurrence_period=event.recurrence_period
                )
                
                with self._lock:
                    heapq.heappush(self._scheduled_events, next_event)
                    self._event_lookup[next_event.name] = next_event
            else:
                # Remove one-time event from lookup
                with self._lock:
                    self._event_lookup.pop(event.name, None)
            
            self._logger.debug(f"Triggered event: {event.name}")
            
        except Exception as e:
            self._logger.error(f"Error triggering event {event.name}: {e}")
            self._events_skipped += 1
    
    def _start_event_processing(self) -> None:
        """Start event processing thread."""
        try:
            self._shutdown_event.clear()
            self._processing_thread = threading.Thread(
                target=self._event_processing_loop,
                name="EventProcessingThread"
            )
            self._processing_thread.daemon = True
            self._processing_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting event processing: {e}")
    
    def _stop_event_processing(self) -> None:
        """Stop event processing thread."""
        try:
            self._shutdown_event.set()
            
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping event processing: {e}")
    
    def _event_processing_loop(self) -> None:
        """Main event processing loop."""
        try:
            self._logger.info("Event processing loop started")
            
            while not self._shutdown_event.is_set():
                try:
                    # Check for events to process
                    self._process_pending_events()
                    
                    # Sleep briefly
                    time.sleep(0.1)
                    
                except Exception as e:
                    self._logger.error(f"Error in event processing loop: {e}")
                    time.sleep(1.0)
            
            self._logger.info("Event processing loop stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in event processing loop: {e}")
    
    def _process_pending_events(self) -> None:
        """Process any pending events."""
        try:
            if not self._current_time:
                return
            
            # This is handled by _process_time_events when time is updated
            # This method could handle other types of pending events
            pass
            
        except Exception as e:
            self._logger.error(f"Error processing pending events: {e}")


class BacktestingRealTimeHandler(BaseRealTimeHandler):
    """Real-time handler for backtesting with simulated time progression."""
    
    def __init__(self):
        """Initialize the backtesting real-time handler."""
        super().__init__()
        self._time_step: timedelta = timedelta(days=1)  # Default daily steps
        self._simulation_speed: float = 1.0  # 1x speed
        self._auto_progress: bool = False
    
    def _initialize_specific(self) -> None:
        """Initialize backtesting specific components."""
        try:
            self._logger.info("Initializing backtesting real-time handler")
            
            # Configure time progression
            if self._job:
                # Extract time step from job parameters
                time_step_param = self._job.parameters.get('time_step', 'daily')
                if time_step_param == 'hourly':
                    self._time_step = timedelta(hours=1)
                elif time_step_param == 'minute':
                    self._time_step = timedelta(minutes=1)
                else:
                    self._time_step = timedelta(days=1)
                
                # Set simulation speed
                self._simulation_speed = float(self._job.parameters.get('simulation_speed', 1.0))
            
            self._logger.info(f"Backtesting time step: {self._time_step}, Speed: {self._simulation_speed}x")
            
        except Exception as e:
            self._logger.error(f"Backtesting real-time handler initialization failed: {e}")
            raise
    
    def _cleanup_specific(self) -> None:
        """Cleanup backtesting specific resources."""
        try:
            # No specific cleanup needed for backtesting
            pass
            
        except Exception as e:
            self._logger.error(f"Error in backtesting cleanup: {e}")
    
    def _process_time_specific(self, old_time: Optional[datetime], new_time: datetime) -> None:
        """Process time change for backtesting."""
        try:
            # Log time progression for backtesting
            if old_time:
                time_diff = new_time - old_time
                self._logger.debug(f"Time progressed by {time_diff} to {new_time}")
            
            # Check if we've reached the end time
            if self._end_time and new_time >= self._end_time:
                self._logger.info("Backtesting end time reached")
                # Could signal completion here
            
        except Exception as e:
            self._logger.error(f"Error in backtesting time processing: {e}")
    
    def advance_time(self, time_step: Optional[timedelta] = None) -> None:
        """Manually advance time in backtesting."""
        try:
            if not self._current_time:
                return
            
            step = time_step or self._time_step
            new_time = self._current_time + step
            
            # Don't go past end time
            if self._end_time and new_time > self._end_time:
                new_time = self._end_time
            
            self.set_time(new_time)
            
        except Exception as e:
            self._logger.error(f"Error advancing time: {e}")
    
    def set_simulation_speed(self, speed: float) -> None:
        """Set the simulation speed multiplier."""
        try:
            self._simulation_speed = max(0.1, min(speed, 100.0))  # Clamp between 0.1x and 100x
            self._logger.info(f"Simulation speed set to {self._simulation_speed}x")
            
        except Exception as e:
            self._logger.error(f"Error setting simulation speed: {e}")
    
    def enable_auto_progress(self, enabled: bool, step: Optional[timedelta] = None) -> None:
        """Enable or disable automatic time progression."""
        try:
            self._auto_progress = enabled
            if step:
                self._time_step = step
            
            self._logger.info(f"Auto progress {'enabled' if enabled else 'disabled'}")
            
        except Exception as e:
            self._logger.error(f"Error setting auto progress: {e}")


class LiveTradingRealTimeHandler(BaseRealTimeHandler):
    """Real-time handler for live trading with actual time progression."""
    
    def __init__(self):
        """Initialize the live trading real-time handler."""
        super().__init__()
        self._time_sync_interval = timedelta(minutes=1)
        self._last_sync_time: Optional[datetime] = None
        self._time_drift_tolerance = timedelta(seconds=5)
    
    def _initialize_specific(self) -> None:
        """Initialize live trading specific components."""
        try:
            self._logger.info("Initializing live trading real-time handler")
            
            # Set current time to now
            self._current_time = datetime.utcnow()
            
            # Setup time synchronization
            self._setup_time_sync()
            
            # Schedule market open/close events
            self._schedule_market_events()
            
        except Exception as e:
            self._logger.error(f"Live trading real-time handler initialization failed: {e}")
            raise
    
    def _cleanup_specific(self) -> None:
        """Cleanup live trading specific resources."""
        try:
            # Cleanup time sync resources
            pass
            
        except Exception as e:
            self._logger.error(f"Error in live trading cleanup: {e}")
    
    def _process_time_specific(self, old_time: Optional[datetime], new_time: datetime) -> None:
        """Process time change for live trading."""
        try:
            # Sync with system time periodically
            if (not self._last_sync_time or 
                new_time - self._last_sync_time >= self._time_sync_interval):
                self._sync_with_system_time()
            
            # Handle market events
            self._check_market_events(old_time, new_time)
            
        except Exception as e:
            self._logger.error(f"Error in live trading time processing: {e}")
    
    def _setup_time_sync(self) -> None:
        """Setup time synchronization with system clock."""
        try:
            # Schedule periodic time sync
            self.schedule_recurring_function(
                name="time_sync",
                callback=self._sync_with_system_time,
                start_time=datetime.utcnow() + self._time_sync_interval,
                period=self._time_sync_interval,
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self._logger.error(f"Error setting up time sync: {e}")
    
    def _sync_with_system_time(self) -> None:
        """Synchronize algorithm time with system time."""
        try:
            system_time = datetime.utcnow()
            
            if self._current_time:
                drift = abs(system_time - self._current_time)
                if drift > self._time_drift_tolerance:
                    self._logger.warning(f"Time drift detected: {drift}")
                    self.set_time(system_time)
            else:
                self.set_time(system_time)
            
            self._last_sync_time = system_time
            
        except Exception as e:
            self._logger.error(f"Error syncing with system time: {e}")
    
    def _schedule_market_events(self) -> None:
        """Schedule market open and close events."""
        try:
            # Schedule today's market events if we're during market hours
            current_time = datetime.utcnow()
            
            # Schedule market open event
            next_open = self.get_next_market_open(time=current_time)
            self.schedule_function(
                name="market_open",
                callback=self._on_market_open,
                scheduled_time=next_open,
                priority=EventPriority.HIGH
            )
            
            # Schedule market close event
            next_close = self.get_next_market_close(time=current_time)
            self.schedule_function(
                name="market_close",
                callback=self._on_market_close,
                scheduled_time=next_close,
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self._logger.error(f"Error scheduling market events: {e}")
    
    def _check_market_events(self, old_time: Optional[datetime], new_time: datetime) -> None:
        """Check for market open/close transitions."""
        try:
            if not old_time:
                return
            
            old_market_open = self.is_market_open(time=old_time)
            new_market_open = self.is_market_open(time=new_time)
            
            # Market opened
            if not old_market_open and new_market_open:
                self._on_market_open()
            
            # Market closed
            elif old_market_open and not new_market_open:
                self._on_market_close()
            
        except Exception as e:
            self._logger.error(f"Error checking market events: {e}")
    
    def _on_market_open(self) -> None:
        """Handle market open event."""
        try:
            self._logger.info("Market opened")
            
            # Notify algorithm if it has a market open handler
            if self._algorithm and hasattr(self._algorithm, 'on_market_open'):
                self._algorithm.on_market_open()
            
            # Schedule next market open event (tomorrow)
            next_open = self.get_next_market_open()
            self.schedule_function(
                name="market_open",
                callback=self._on_market_open,
                scheduled_time=next_open,
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self._logger.error(f"Error handling market open: {e}")
    
    def _on_market_close(self) -> None:
        """Handle market close event."""
        try:
            self._logger.info("Market closed")
            
            # Notify algorithm if it has a market close handler
            if self._algorithm and hasattr(self._algorithm, 'on_market_close'):
                self._algorithm.on_market_close()
            
            # Schedule next market close event (tomorrow)
            next_close = self.get_next_market_close()
            self.schedule_function(
                name="market_close",
                callback=self._on_market_close,
                scheduled_time=next_close,
                priority=EventPriority.HIGH
            )
            
        except Exception as e:
            self._logger.error(f"Error handling market close: {e}")
    
    def get_current_utc_time(self) -> datetime:
        """Get the current UTC time."""
        return datetime.utcnow()
    
    def get_time_until_market_open(self, symbol: Optional[str] = None) -> timedelta:
        """Get time until next market open."""
        try:
            current_time = self._current_time or datetime.utcnow()
            next_open = self.get_next_market_open(symbol, current_time)
            return next_open - current_time
            
        except Exception as e:
            self._logger.error(f"Error calculating time until market open: {e}")
            return timedelta(0)
    
    def get_time_until_market_close(self, symbol: Optional[str] = None) -> timedelta:
        """Get time until next market close."""
        try:
            current_time = self._current_time or datetime.utcnow()
            next_close = self.get_next_market_close(symbol, current_time)
            return next_close - current_time
            
        except Exception as e:
            self._logger.error(f"Error calculating time until market close: {e}")
            return timedelta(0)