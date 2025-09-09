from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional, Any, Union
from enum import Enum
import uuid


class ScheduleFrequency(Enum):
    """Defines scheduling frequencies"""
    ONCE = "Once"
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"


class DayOfWeek(Enum):
    """Days of the week"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class ScheduledEvent:
    """
    Represents a scheduled event with its execution parameters.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    callback: Callable = None
    frequency: ScheduleFrequency = ScheduleFrequency.ONCE
    next_execution: datetime = None
    last_execution: Optional[datetime] = None
    
    # Time-based parameters
    time_of_day: Optional[time] = None
    day_of_week: Optional[DayOfWeek] = None
    day_of_month: Optional[int] = None
    
    # Interval-based parameters (for custom intervals)
    interval: Optional[timedelta] = None
    
    # Execution tracking
    execution_count: int = 0
    max_executions: Optional[int] = None
    is_active: bool = True
    
    # Context data
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Returns True if this event has reached its maximum executions"""
        return self.max_executions is not None and self.execution_count >= self.max_executions
    
    @property
    def should_execute(self) -> bool:
        """Returns True if this event should be executed now"""
        if not self.is_active or self.is_expired or not self.next_execution:
            return False
        return datetime.now() >= self.next_execution
    
    def calculate_next_execution(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Calculates the next execution time based on frequency and parameters.
        """
        base_time = from_time or datetime.now()
        
        if self.frequency == ScheduleFrequency.ONCE:
            return self.next_execution or base_time
        
        elif self.frequency == ScheduleFrequency.DAILY:
            if self.time_of_day:
                next_date = base_time.date()
                next_datetime = datetime.combine(next_date, self.time_of_day)
                if next_datetime <= base_time:
                    next_datetime += timedelta(days=1)
                return next_datetime
            else:
                return base_time + timedelta(days=1)
        
        elif self.frequency == ScheduleFrequency.WEEKLY:
            if self.day_of_week is not None:
                days_ahead = self.day_of_week.value - base_time.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                next_date = base_time.date() + timedelta(days=days_ahead)
                if self.time_of_day:
                    return datetime.combine(next_date, self.time_of_day)
                else:
                    return datetime.combine(next_date, base_time.time())
            else:
                return base_time + timedelta(weeks=1)
        
        elif self.frequency == ScheduleFrequency.MONTHLY:
            if self.day_of_month:
                # Simple monthly scheduling - go to next month, same day
                if base_time.month == 12:
                    next_month = base_time.replace(year=base_time.year + 1, month=1, day=self.day_of_month)
                else:
                    try:
                        next_month = base_time.replace(month=base_time.month + 1, day=self.day_of_month)
                    except ValueError:
                        # Handle cases where day doesn't exist in next month (e.g., Feb 30)
                        next_month = base_time.replace(month=base_time.month + 1, day=28)
                
                if self.time_of_day:
                    return datetime.combine(next_month.date(), self.time_of_day)
                else:
                    return next_month
            else:
                # Add approximately one month
                return base_time + timedelta(days=30)
        
        elif self.interval:
            return base_time + self.interval
        
        else:
            return base_time + timedelta(days=1)  # Default to daily
    
    def execute(self) -> bool:
        """
        Executes the scheduled event and updates tracking information.
        Returns True if execution was successful.
        """
        if not self.should_execute or not self.callback:
            return False
        
        try:
            # Execute the callback
            if self.context:
                self.callback(**self.context)
            else:
                self.callback()
            
            # Update execution tracking
            self.last_execution = datetime.now()
            self.execution_count += 1
            
            # Calculate next execution time
            if not self.is_expired and self.frequency != ScheduleFrequency.ONCE:
                self.next_execution = self.calculate_next_execution()
            else:
                self.is_active = False
            
            return True
        
        except Exception as e:
            # Log error but don't stop scheduling
            print(f"Error executing scheduled event {self.name}: {e}")
            return False


class DateRules:
    """
    Provides rules for date-based scheduling.
    """
    
    @staticmethod
    def every_day() -> Dict[str, Any]:
        """Schedule for every day"""
        return {"frequency": ScheduleFrequency.DAILY}
    
    @staticmethod
    def every(days: int) -> Dict[str, Any]:
        """Schedule every N days"""
        return {"frequency": ScheduleFrequency.DAILY, "interval": timedelta(days=days)}
    
    @staticmethod
    def week_start() -> Dict[str, Any]:
        """Schedule for Monday of each week"""
        return {"frequency": ScheduleFrequency.WEEKLY, "day_of_week": DayOfWeek.MONDAY}
    
    @staticmethod
    def week_end() -> Dict[str, Any]:
        """Schedule for Friday of each week"""
        return {"frequency": ScheduleFrequency.WEEKLY, "day_of_week": DayOfWeek.FRIDAY}
    
    @staticmethod
    def month_start() -> Dict[str, Any]:
        """Schedule for the first day of each month"""
        return {"frequency": ScheduleFrequency.MONTHLY, "day_of_month": 1}
    
    @staticmethod
    def month_end() -> Dict[str, Any]:
        """Schedule for the last day of each month (approximated as 28th)"""
        return {"frequency": ScheduleFrequency.MONTHLY, "day_of_month": 28}
    
    @staticmethod
    def on(day: DayOfWeek) -> Dict[str, Any]:
        """Schedule for a specific day of the week"""
        return {"frequency": ScheduleFrequency.WEEKLY, "day_of_week": day}


class TimeRules:
    """
    Provides rules for time-based scheduling.
    """
    
    @staticmethod
    def at(hour: int, minute: int = 0, second: int = 0) -> Dict[str, Any]:
        """Schedule at a specific time"""
        return {"time_of_day": time(hour, minute, second)}
    
    @staticmethod
    def market_open(offset_minutes: int = 0) -> Dict[str, Any]:
        """Schedule at market open (9:30 AM ET by default)"""
        market_open_time = time(9, 30 + offset_minutes)
        return {"time_of_day": market_open_time}
    
    @staticmethod
    def market_close(offset_minutes: int = 0) -> Dict[str, Any]:
        """Schedule at market close (4:00 PM ET by default)"""
        market_close_time = time(16, 0 + offset_minutes)
        return {"time_of_day": market_close_time}
    
    @staticmethod
    def before_market_open(minutes: int = 30) -> Dict[str, Any]:
        """Schedule before market open"""
        return TimeRules.market_open(-minutes)
    
    @staticmethod
    def after_market_close(minutes: int = 30) -> Dict[str, Any]:
        """Schedule after market close"""
        return TimeRules.market_close(minutes)


class ScheduleManager:
    """
    Manages scheduled events and their execution.
    """
    
    def __init__(self):
        self._events: Dict[str, ScheduledEvent] = {}
        self._is_running = False
    
    def schedule(self, callback: Callable, name: str = "", 
                date_rule: Optional[Dict[str, Any]] = None,
                time_rule: Optional[Dict[str, Any]] = None,
                **kwargs) -> str:
        """
        Schedules a callback function with specified date and time rules.
        
        Args:
            callback: The function to execute
            name: Optional name for the scheduled event
            date_rule: Date-based scheduling rules from DateRules
            time_rule: Time-based scheduling rules from TimeRules  
            **kwargs: Additional context to pass to the callback
        
        Returns:
            Event ID for managing the scheduled event
        """
        event = ScheduledEvent(
            name=name or f"Event_{datetime.now().isoformat()}",
            callback=callback,
            context=kwargs
        )
        
        # Apply date rules
        if date_rule:
            for key, value in date_rule.items():
                if hasattr(event, key):
                    setattr(event, key, value)
        
        # Apply time rules
        if time_rule:
            for key, value in time_rule.items():
                if hasattr(event, key):
                    setattr(event, key, value)
        
        # Calculate initial execution time
        event.next_execution = event.calculate_next_execution()
        
        # Store the event
        self._events[event.id] = event
        
        return event.id
    
    def schedule_once(self, callback: Callable, execution_time: datetime, 
                     name: str = "", **kwargs) -> str:
        """
        Schedules a one-time execution.
        """
        event = ScheduledEvent(
            name=name or f"OneTime_{datetime.now().isoformat()}",
            callback=callback,
            frequency=ScheduleFrequency.ONCE,
            next_execution=execution_time,
            context=kwargs
        )
        
        self._events[event.id] = event
        return event.id
    
    def schedule_function(self, callback: Callable, name: str = "", 
                         date_rule: Optional[Dict[str, Any]] = None,
                         time_rule: Optional[Dict[str, Any]] = None) -> str:
        """
        Convenience method for scheduling functions with date/time rules.
        """
        return self.schedule(callback, name, date_rule, time_rule)
    
    def unschedule(self, event_id: str) -> bool:
        """
        Removes a scheduled event.
        """
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False
    
    def pause_event(self, event_id: str) -> bool:
        """
        Pauses a scheduled event without removing it.
        """
        if event_id in self._events:
            self._events[event_id].is_active = False
            return True
        return False
    
    def resume_event(self, event_id: str) -> bool:
        """
        Resumes a paused scheduled event.
        """
        if event_id in self._events:
            event = self._events[event_id]
            event.is_active = True
            # Recalculate next execution
            event.next_execution = event.calculate_next_execution()
            return True
        return False
    
    def get_scheduled_events(self) -> List[ScheduledEvent]:
        """
        Returns a list of all scheduled events.
        """
        return list(self._events.values())
    
    def get_pending_events(self) -> List[ScheduledEvent]:
        """
        Returns events that are ready to execute.
        """
        return [event for event in self._events.values() if event.should_execute]
    
    def execute_pending(self) -> int:
        """
        Executes all pending events and returns the number executed.
        """
        pending = self.get_pending_events()
        executed_count = 0
        
        for event in pending:
            if event.execute():
                executed_count += 1
            
            # Remove expired one-time events
            if event.is_expired or (event.frequency == ScheduleFrequency.ONCE and not event.is_active):
                self.unschedule(event.id)
        
        return executed_count
    
    def start(self):
        """Start the scheduler"""
        self._is_running = True
    
    def stop(self):
        """Stop the scheduler"""
        self._is_running = False
    
    def clear_all(self):
        """Remove all scheduled events"""
        self._events.clear()


# Global scheduler instance
_global_scheduler = ScheduleManager()


def schedule(callback: Callable, date_rule: Optional[Dict[str, Any]] = None,
            time_rule: Optional[Dict[str, Any]] = None, name: str = "", **kwargs) -> str:
    """Global schedule function"""
    return _global_scheduler.schedule(callback, name, date_rule, time_rule, **kwargs)


def schedule_function(callback: Callable, date_rule: Optional[Dict[str, Any]] = None,
                     time_rule: Optional[Dict[str, Any]] = None, name: str = "") -> str:
    """Global schedule function for functions"""
    return _global_scheduler.schedule_function(callback, name, date_rule, time_rule)


def unschedule(event_id: str) -> bool:
    """Global unschedule function"""
    return _global_scheduler.unschedule(event_id)


def execute_scheduled_events() -> int:
    """Execute all pending scheduled events"""
    return _global_scheduler.execute_pending()


def get_scheduler() -> ScheduleManager:
    """Get the global scheduler instance"""
    return _global_scheduler