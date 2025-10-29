"""
ProgressMonitor for test_base_project.

Provides real-time monitoring and progress tracking for backtesting operations,
ML model training, and factor data processing.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ProgressLevel(Enum):
    """Progress message levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


@dataclass
class ProgressEvent:
    """Represents a progress event."""
    timestamp: datetime
    level: ProgressLevel
    component: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'component': self.component,
            'message': self.message,
            'data': self.data
        }


class ProgressMonitor:
    """
    Monitors and tracks progress across all BaseProject components.
    
    Provides centralized progress tracking for:
    - Backtesting execution
    - ML model training and prediction
    - Factor data processing
    - Portfolio optimization
    - Performance analysis
    """
    
    def __init__(self, web_interface=None):
        """
        Initialize the progress monitor.
        
        Args:
            web_interface: Optional web interface for real-time updates
        """
        self.web_interface = web_interface
        self.events = []
        self.component_stats = {}
        self.callbacks = []
        
        # Component tracking
        self.active_components = set()
        self.component_progress = {}
        
        # Timing
        self.start_time = None
        self.component_start_times = {}

    def start_monitoring(self):
        """Start the monitoring session."""
        self.start_time = datetime.now()
        self.log_event(ProgressLevel.INFO, "monitor", "Progress monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring session."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            self.log_event(ProgressLevel.INFO, "monitor", 
                         f"Progress monitoring stopped. Duration: {duration}")

    def log_event(self, 
                  level: ProgressLevel, 
                  component: str, 
                  message: str,
                  data: Optional[Dict[str, Any]] = None):
        """
        Log a progress event.
        
        Args:
            level: Event severity level
            component: Component that generated the event
            message: Human-readable message
            data: Optional additional data
        """
        event = ProgressEvent(
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            data=data or {}
        )
        
        self.events.append(event)
        
        # Update component stats
        if component not in self.component_stats:
            self.component_stats[component] = {
                'total_events': 0,
                'last_event': None,
                'error_count': 0,
                'warning_count': 0
            }
        
        stats = self.component_stats[component]
        stats['total_events'] += 1
        stats['last_event'] = event.timestamp
        
        if level == ProgressLevel.ERROR:
            stats['error_count'] += 1
        elif level == ProgressLevel.WARNING:
            stats['warning_count'] += 1
        
        # Send to web interface
        if self.web_interface:
            try:
                self.web_interface.progress_queue.put(event.to_dict())
            except Exception:
                pass  # Ignore web interface errors
        
        # Execute callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Ignore callback errors

    def start_component(self, component: str, task_description: str = ""):
        """
        Mark the start of a component's processing.
        
        Args:
            component: Component name
            task_description: Description of the task being started
        """
        self.active_components.add(component)
        self.component_start_times[component] = datetime.now()
        self.component_progress[component] = 0.0
        
        message = f"Starting {task_description}" if task_description else f"Starting {component}"
        self.log_event(ProgressLevel.INFO, component, message)

    def update_component_progress(self, 
                                component: str, 
                                progress: float,
                                status_message: str = ""):
        """
        Update progress for a specific component.
        
        Args:
            component: Component name
            progress: Progress percentage (0.0 to 1.0)
            status_message: Optional status message
        """
        self.component_progress[component] = min(1.0, max(0.0, progress))
        
        if status_message:
            self.log_event(ProgressLevel.INFO, component, 
                         f"Progress: {progress*100:.1f}% - {status_message}")

    def complete_component(self, component: str, summary: str = ""):
        """
        Mark completion of a component's processing.
        
        Args:
            component: Component name
            summary: Optional completion summary
        """
        self.active_components.discard(component)
        self.component_progress[component] = 1.0
        
        # Calculate duration
        if component in self.component_start_times:
            duration = datetime.now() - self.component_start_times[component]
            message = f"Completed in {duration}"
            if summary:
                message += f" - {summary}"
        else:
            message = "Completed"
            if summary:
                message += f" - {summary}"
        
        self.log_event(ProgressLevel.SUCCESS, component, message)

    def log_error(self, component: str, error_message: str, exception: Exception = None):
        """
        Log an error event.
        
        Args:
            component: Component that experienced the error
            error_message: Error description
            exception: Optional exception object
        """
        data = {}
        if exception:
            data['exception_type'] = type(exception).__name__
            data['exception_message'] = str(exception)
        
        self.log_event(ProgressLevel.ERROR, component, error_message, data)

    def log_warning(self, component: str, warning_message: str):
        """
        Log a warning event.
        
        Args:
            component: Component that generated the warning
            warning_message: Warning description
        """
        self.log_event(ProgressLevel.WARNING, component, warning_message)

    def get_overall_progress(self) -> float:
        """
        Calculate overall progress across all components.
        
        Returns:
            Overall progress as percentage (0.0 to 1.0)
        """
        if not self.component_progress:
            return 0.0
        
        return sum(self.component_progress.values()) / len(self.component_progress)

    def get_active_components(self) -> Dict[str, float]:
        """
        Get currently active components and their progress.
        
        Returns:
            Dictionary mapping component names to progress percentages
        """
        return {comp: self.component_progress.get(comp, 0.0) 
                for comp in self.active_components}

    def get_component_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary statistics for all components.
        
        Returns:
            Dictionary containing component statistics
        """
        summary = {}
        
        for component, stats in self.component_stats.items():
            duration = None
            if component in self.component_start_times:
                start_time = self.component_start_times[component]
                if component in self.active_components:
                    duration = datetime.now() - start_time
                else:
                    # Find completion event
                    completion_events = [e for e in self.events 
                                       if e.component == component and e.level == ProgressLevel.SUCCESS]
                    if completion_events:
                        duration = completion_events[-1].timestamp - start_time
            
            summary[component] = {
                **stats,
                'progress': self.component_progress.get(component, 0.0),
                'is_active': component in self.active_components,
                'duration': str(duration) if duration else None
            }
        
        return summary

    def add_callback(self, callback: Callable[[ProgressEvent], None]):
        """
        Add a callback function to be called on each progress event.
        
        Args:
            callback: Function that accepts a ProgressEvent
        """
        self.callbacks.append(callback)

    def get_recent_events(self, count: int = 50) -> list[ProgressEvent]:
        """
        Get recent progress events.
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of recent ProgressEvent objects
        """
        return self.events[-count:] if self.events else []

    def export_log(self, filename: str = None) -> str:
        """
        Export progress log to file.
        
        Args:
            filename: Optional filename (defaults to timestamped name)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"progress_log_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("BaseProject Progress Log\n")
                f.write("=" * 50 + "\n\n")
                
                if self.start_time:
                    f.write(f"Monitoring started: {self.start_time}\n")
                    if not self.active_components:
                        duration = datetime.now() - self.start_time
                        f.write(f"Total duration: {duration}\n")
                    f.write("\n")
                
                f.write("Events:\n")
                f.write("-" * 30 + "\n")
                
                for event in self.events:
                    f.write(f"[{event.timestamp}] {event.level.value} - {event.component}: {event.message}\n")
                    if event.data:
                        f.write(f"  Data: {event.data}\n")
                
                f.write("\nComponent Summary:\n")
                f.write("-" * 30 + "\n")
                
                summary = self.get_component_summary()
                for component, stats in summary.items():
                    f.write(f"{component}:\n")
                    for key, value in stats.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
            
            return filename
            
        except Exception as e:
            self.log_error("monitor", f"Failed to export log: {e}")
            return None