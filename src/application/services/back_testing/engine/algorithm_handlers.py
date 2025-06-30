"""
Algorithm handler implementations for QuantConnect Lean Engine Python implementation.
Handles algorithm lifecycle management and execution.
"""

import logging
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .interfaces import IAlgorithmHandler, IAlgorithm
from .engine_node_packet import EngineNodePacket
from .enums import ComponentState, AlgorithmStatus

# Import from common module
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import OrderEvent, Slice, Portfolio


class AlgorithmHandler(IAlgorithmHandler):
    """
    Algorithm handler for managing algorithm lifecycle and execution.
    Coordinates algorithm execution with the engine components.
    """
    
    def __init__(self):
        """Initialize the algorithm handler."""
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._state = ComponentState.CREATED
        self._algorithm_status = AlgorithmStatus.RUNNING
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Execution tracking
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._iterations = 0
        self._data_points_processed = 0
        self._orders_submitted = 0
        
        # Performance sampling
        self._last_performance_sample: Optional[datetime] = None
        self._performance_samples: List[Dict[str, Any]] = []
        self._sample_interval = timedelta(minutes=1)
        
        # Error tracking
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._runtime_errors = 0
        self._max_runtime_errors = 10
        
        # Thread management
        self._monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Algorithm state
        self._is_warming_up = False
        self._warmup_period: Optional[timedelta] = None
        
        self._logger.info("Initialized AlgorithmHandler")
    
    def initialize(self, job: EngineNodePacket, algorithm: IAlgorithm) -> bool:
        """Initialize the algorithm handler."""
        try:
            with self._lock:
                if self._state != ComponentState.CREATED:
                    self._logger.warning(f"Algorithm handler already initialized with state: {self._state}")
                    return False
                
                self._state = ComponentState.INITIALIZING
                self._job = job
                self._algorithm = algorithm
                
                self._logger.info("Initializing algorithm handler")
                
                # Setup algorithm monitoring
                self._setup_monitoring()
                
                # Configure algorithm
                self._configure_algorithm()
                
                # Start monitoring thread
                self._start_monitoring()
                
                self._state = ComponentState.INITIALIZED
                self._start_time = datetime.utcnow()
                
                self._logger.info("Algorithm handler initialization completed")
                return True
                
        except Exception as e:
            self._logger.error(f"Error during algorithm handler initialization: {e}")
            self._state = ComponentState.ERROR
            self._algorithm_status = AlgorithmStatus.ERROR
            return False
    
    def run(self) -> None:
        """Run the algorithm handler."""
        try:
            with self._lock:
                if self._state != ComponentState.INITIALIZED:
                    raise RuntimeError(f"Algorithm handler not initialized: {self._state}")
                
                if self._algorithm_status != AlgorithmStatus.RUNNING:
                    self._logger.warning(f"Algorithm not in running state: {self._algorithm_status}")
                    return
                
                self._logger.info("Algorithm handler started running")
                
                # Set algorithm to running state
                self._algorithm_status = AlgorithmStatus.RUNNING
                
                # Perform any pre-run setup
                self._pre_run_setup()
                
        except Exception as e:
            self._logger.error(f"Error starting algorithm handler: {e}")
            self._algorithm_status = AlgorithmStatus.ERROR
            raise
    
    def on_data(self, data: Slice) -> None:
        """Handle new market data."""
        try:
            if self._algorithm_status != AlgorithmStatus.RUNNING:
                return
            
            if not self._algorithm:
                self._logger.error("No algorithm instance available")
                return
            
            # Track data processing
            self._data_points_processed += 1
            self._iterations += 1
            
            # Check if we're still warming up
            if self._is_warming_up and self._should_continue_warmup():
                return
            
            # Call algorithm's OnData method
            try:
                if hasattr(self._algorithm, 'on_data'):
                    self._algorithm.on_data(data)
                
            except Exception as e:
                self._handle_algorithm_error("OnData", e)
                return
            
            # Sample performance periodically
            self._sample_performance_if_needed()
            
        except Exception as e:
            self._logger.error(f"Error in algorithm data handling: {e}")
            self._handle_algorithm_error("DataHandling", e)
    
    def on_order_event(self, order_event: OrderEvent) -> None:
        """Handle order events."""
        try:
            if self._algorithm_status != AlgorithmStatus.RUNNING:
                return
            
            if not self._algorithm:
                return
            
            # Call algorithm's OnOrderEvent method
            try:
                if hasattr(self._algorithm, 'on_order_event'):
                    self._algorithm.on_order_event(order_event)
                
                # Track order submissions
                if order_event.status.name == 'SUBMITTED':
                    self._orders_submitted += 1
                
            except Exception as e:
                self._handle_algorithm_error("OnOrderEvent", e)
            
        except Exception as e:
            self._logger.error(f"Error in algorithm order event handling: {e}")
    
    def sample_performance(self, time: datetime, value: Decimal) -> None:
        """Sample algorithm performance at a given time."""
        try:
            with self._lock:
                performance_sample = {
                    'time': time.isoformat(),
                    'portfolio_value': float(value),
                    'iterations': self._iterations,
                    'data_points': self._data_points_processed,
                    'orders': self._orders_submitted,
                    'errors': len(self._errors)
                }
                
                self._performance_samples.append(performance_sample)
                
                # Limit sample history
                if len(self._performance_samples) > 10000:
                    self._performance_samples = self._performance_samples[-5000:]
                
                self._last_performance_sample = time
                
        except Exception as e:
            self._logger.error(f"Error sampling performance: {e}")
    
    def set_status(self, status: AlgorithmStatus) -> None:
        """Set the algorithm status."""
        try:
            with self._lock:
                old_status = self._algorithm_status
                self._algorithm_status = status
                
                if old_status != status:
                    self._logger.info(f"Algorithm status changed: {old_status.name} -> {status.name}")
                    
                    # Handle status transitions
                    if status == AlgorithmStatus.STOPPED:
                        self._on_algorithm_stopped()
                    elif status == AlgorithmStatus.ERROR:
                        self._on_algorithm_error()
                    elif status == AlgorithmStatus.COMPLETED:
                        self._on_algorithm_completed()
                
        except Exception as e:
            self._logger.error(f"Error setting algorithm status: {e}")
    
    def get_status(self) -> AlgorithmStatus:
        """Get the current algorithm status."""
        return self._algorithm_status
    
    def exit(self) -> None:
        """Exit and cleanup the algorithm handler."""
        try:
            with self._lock:
                if self._state == ComponentState.DISPOSED:
                    return
                
                self._logger.info("Exiting algorithm handler")
                
                # Stop algorithm if running
                if self._algorithm_status == AlgorithmStatus.RUNNING:
                    self.set_status(AlgorithmStatus.STOPPED)
                
                # Stop monitoring
                self._stop_monitoring()
                
                # Call algorithm cleanup if available
                self._cleanup_algorithm()
                
                self._end_time = datetime.utcnow()
                self._state = ComponentState.DISPOSED
                
                self._logger.info("Algorithm handler exited")
                
        except Exception as e:
            self._logger.error(f"Error during algorithm handler exit: {e}")
    
    def get_runtime_statistics(self) -> Dict[str, Any]:
        """Get runtime statistics for the algorithm."""
        try:
            with self._lock:
                runtime = None
                if self._start_time:
                    end_time = self._end_time or datetime.utcnow()
                    runtime = (end_time - self._start_time).total_seconds()
                
                return {
                    'status': self._algorithm_status.name,
                    'iterations': self._iterations,
                    'data_points_processed': self._data_points_processed,
                    'orders_submitted': self._orders_submitted,
                    'runtime_seconds': runtime,
                    'runtime_errors': self._runtime_errors,
                    'total_errors': len(self._errors),
                    'total_warnings': len(self._warnings),
                    'performance_samples': len(self._performance_samples),
                    'is_warming_up': self._is_warming_up
                }
                
        except Exception as e:
            self._logger.error(f"Error getting runtime statistics: {e}")
            return {}
    
    def get_performance_samples(self) -> List[Dict[str, Any]]:
        """Get all performance samples."""
        with self._lock:
            return self._performance_samples.copy()
    
    def get_errors(self) -> List[str]:
        """Get all errors."""
        with self._lock:
            return self._errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get all warnings."""
        with self._lock:
            return self._warnings.copy()
    
    # Private helper methods
    
    def _setup_monitoring(self) -> None:
        """Setup algorithm monitoring."""
        try:
            # Configure monitoring parameters
            if self._job:
                # Set max runtime if specified
                if self._job.max_runtime_minutes > 0:
                    self._max_runtime = timedelta(minutes=self._job.max_runtime_minutes)
                else:
                    self._max_runtime = timedelta(hours=24)  # Default 24 hour limit
            
            self._logger.info("Algorithm monitoring setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up monitoring: {e}")
    
    def _configure_algorithm(self) -> None:
        """Configure the algorithm instance."""
        try:
            if not self._algorithm:
                return
            
            # Set up warmup period if specified
            if hasattr(self._algorithm, 'warmup_period'):
                warmup = getattr(self._algorithm, 'warmup_period', None)
                if warmup:
                    self._warmup_period = warmup
                    self._is_warming_up = True
                    self._logger.info(f"Algorithm warmup period set to: {warmup}")
            
            # Configure algorithm parameters from job
            if self._job and self._job.parameters:
                for key, value in self._job.parameters.items():
                    if hasattr(self._algorithm, key):
                        try:
                            setattr(self._algorithm, key, value)
                            self._logger.debug(f"Set algorithm parameter {key} = {value}")
                        except Exception as e:
                            self._logger.warning(f"Failed to set algorithm parameter {key}: {e}")
            
        except Exception as e:
            self._logger.error(f"Error configuring algorithm: {e}")
    
    def _start_monitoring(self) -> None:
        """Start the monitoring thread."""
        try:
            self._shutdown_event.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="AlgorithmMonitoringThread"
            )
            self._monitoring_thread.daemon = True
            self._monitoring_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting monitoring: {e}")
    
    def _stop_monitoring(self) -> None:
        """Stop the monitoring thread."""
        try:
            self._shutdown_event.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping monitoring: {e}")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        try:
            self._logger.info("Algorithm monitoring loop started")
            
            while not self._shutdown_event.is_set() and self._algorithm_status == AlgorithmStatus.RUNNING:
                try:
                    # Check for runtime timeout
                    self._check_runtime_timeout()
                    
                    # Check for excessive errors
                    self._check_error_threshold()
                    
                    # Perform health checks
                    self._perform_health_checks()
                    
                    # Sleep between checks
                    time.sleep(1.0)
                    
                except Exception as e:
                    self._logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(5.0)
            
            self._logger.info("Algorithm monitoring loop stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in monitoring loop: {e}")
    
    def _check_runtime_timeout(self) -> None:
        """Check if algorithm has exceeded maximum runtime."""
        try:
            if not self._start_time or not hasattr(self, '_max_runtime'):
                return
            
            runtime = datetime.utcnow() - self._start_time
            if runtime > self._max_runtime:
                self._logger.warning(f"Algorithm exceeded maximum runtime: {runtime}")
                self.set_status(AlgorithmStatus.STOPPED)
            
        except Exception as e:
            self._logger.error(f"Error checking runtime timeout: {e}")
    
    def _check_error_threshold(self) -> None:
        """Check if algorithm has exceeded error threshold."""
        try:
            if self._runtime_errors >= self._max_runtime_errors:
                self._logger.error(f"Algorithm exceeded maximum runtime errors: {self._runtime_errors}")
                self.set_status(AlgorithmStatus.ERROR)
            
        except Exception as e:
            self._logger.error(f"Error checking error threshold: {e}")
    
    def _perform_health_checks(self) -> None:
        """Perform algorithm health checks."""
        try:
            # Check algorithm responsiveness (simplified)
            if self._algorithm_status == AlgorithmStatus.RUNNING:
                # Could check if algorithm is responding to data, etc.
                pass
            
        except Exception as e:
            self._logger.error(f"Error in health checks: {e}")
    
    def _handle_algorithm_error(self, context: str, error: Exception) -> None:
        """Handle an algorithm error."""
        try:
            self._runtime_errors += 1
            error_msg = f"Algorithm error in {context}: {str(error)}"
            stack_trace = traceback.format_exc()
            
            self._errors.append(error_msg)
            self._logger.error(f"{error_msg}\n{stack_trace}")
            
            # Stop algorithm if too many errors
            if self._runtime_errors >= self._max_runtime_errors:
                self.set_status(AlgorithmStatus.ERROR)
            
        except Exception as e:
            self._logger.error(f"Error handling algorithm error: {e}")
    
    def _sample_performance_if_needed(self) -> None:
        """Sample performance if enough time has passed."""
        try:
            current_time = datetime.utcnow()
            
            if (not self._last_performance_sample or 
                current_time - self._last_performance_sample >= self._sample_interval):
                
                # Get portfolio value if available
                portfolio_value = Decimal('0')
                if self._algorithm and hasattr(self._algorithm, 'portfolio'):
                    portfolio = getattr(self._algorithm, 'portfolio')
                    if hasattr(portfolio, 'total_portfolio_value'):
                        portfolio_value = portfolio.total_portfolio_value
                
                self.sample_performance(current_time, portfolio_value)
            
        except Exception as e:
            self._logger.error(f"Error sampling performance: {e}")
    
    def _should_continue_warmup(self) -> bool:
        """Check if algorithm should continue warming up."""
        try:
            if not self._is_warming_up or not self._warmup_period:
                return False
            
            if not self._start_time:
                return True
            
            warmup_elapsed = datetime.utcnow() - self._start_time
            if warmup_elapsed >= self._warmup_period:
                self._is_warming_up = False
                self._logger.info("Algorithm warmup period completed")
                return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error checking warmup status: {e}")
            return False
    
    def _pre_run_setup(self) -> None:
        """Perform pre-run setup."""
        try:
            # Any setup needed before algorithm starts running
            self._logger.debug("Pre-run setup completed")
            
        except Exception as e:
            self._logger.error(f"Error in pre-run setup: {e}")
    
    def _cleanup_algorithm(self) -> None:
        """Cleanup algorithm resources."""
        try:
            if self._algorithm and hasattr(self._algorithm, 'on_end_of_algorithm'):
                try:
                    self._algorithm.on_end_of_algorithm()
                except Exception as e:
                    self._logger.warning(f"Error in algorithm cleanup: {e}")
            
        except Exception as e:
            self._logger.error(f"Error cleaning up algorithm: {e}")
    
    def _on_algorithm_stopped(self) -> None:
        """Handle algorithm stopped event."""
        try:
            self._logger.info("Algorithm stopped")
            self._end_time = datetime.utcnow()
            
        except Exception as e:
            self._logger.error(f"Error handling algorithm stopped: {e}")
    
    def _on_algorithm_error(self) -> None:
        """Handle algorithm error event."""
        try:
            self._logger.error("Algorithm entered error state")
            self._end_time = datetime.utcnow()
            
        except Exception as e:
            self._logger.error(f"Error handling algorithm error: {e}")
    
    def _on_algorithm_completed(self) -> None:
        """Handle algorithm completed event."""
        try:
            self._logger.info("Algorithm completed successfully")
            self._end_time = datetime.utcnow()
            
        except Exception as e:
            self._logger.error(f"Error handling algorithm completion: {e}")
    
    # Warmup management methods
    
    def set_warmup_period(self, period: timedelta) -> None:
        """Set the algorithm warmup period."""
        try:
            self._warmup_period = period
            self._is_warming_up = True
            self._logger.info(f"Warmup period set to: {period}")
            
        except Exception as e:
            self._logger.error(f"Error setting warmup period: {e}")
    
    def is_warming_up(self) -> bool:
        """Check if algorithm is currently warming up."""
        return self._is_warming_up
    
    def end_warmup(self) -> None:
        """Manually end the warmup period."""
        try:
            self._is_warming_up = False
            self._logger.info("Warmup period manually ended")
            
        except Exception as e:
            self._logger.error(f"Error ending warmup: {e}")
    
    # Algorithm control methods
    
    def quit(self, message: str = "") -> None:
        """Request algorithm to quit."""
        try:
            self._logger.info(f"Algorithm quit requested: {message}")
            self.set_status(AlgorithmStatus.STOPPED)
            
        except Exception as e:
            self._logger.error(f"Error quitting algorithm: {e}")
    
    def set_run_time_limit(self, limit: timedelta) -> None:
        """Set the algorithm runtime limit."""
        try:
            self._max_runtime = limit
            self._logger.info(f"Runtime limit set to: {limit}")
            
        except Exception as e:
            self._logger.error(f"Error setting runtime limit: {e}")
    
    def get_runtime(self) -> Optional[timedelta]:
        """Get the current algorithm runtime."""
        try:
            if self._start_time:
                end_time = self._end_time or datetime.utcnow()
                return end_time - self._start_time
            return None
            
        except Exception as e:
            self._logger.error(f"Error getting runtime: {e}")
            return None