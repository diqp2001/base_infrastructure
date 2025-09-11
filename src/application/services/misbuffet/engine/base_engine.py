"""
Base engine implementation for QuantConnect Lean Engine Python implementation.
Provides common functionality for all engine types.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .interfaces import (
    IEngine, IDataFeed, ITransactionHandler, IResultHandler,
    ISetupHandler, IRealTimeHandler, IAlgorithmHandler
)
from .enums import (
    EngineStatus, AlgorithmStatus, ComponentState, LogLevel
)
from .engine_node_packet import EngineNodePacket

# Import from common module
from ..common import IAlgorithm


class BaseEngine(IEngine, ABC):
    """
    Base engine implementation providing common functionality.
    Abstract base class for backtesting and live trading engines.
    """
    
    def __init__(self):
        """Initialize the base engine."""
        self._status = EngineStatus.INITIALIZING
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Handler components
        self._data_feed: Optional[IDataFeed] = None
        self._transaction_handler: Optional[ITransactionHandler] = None
        self._result_handler: Optional[IResultHandler] = None
        self._setup_handler: Optional[ISetupHandler] = None
        self._realtime_handler: Optional[IRealTimeHandler] = None
        self._algorithm_handler: Optional[IAlgorithmHandler] = None
        
        # Performance metrics
        self._total_trades = 0
        self._total_fees = Decimal('0')
        self._total_performance = Decimal('0')
        self._max_drawdown = Decimal('0')
        
        # Error tracking
        self._errors: List[str] = []
        self._warnings: List[str] = []
        
        self._logger.info(f"Initialized {self.__class__.__name__}")
    
    @property
    def status(self) -> EngineStatus:
        """Get the current engine status."""
        return self._status
    
    @property
    def algorithm(self) -> Optional[IAlgorithm]:
        """Get the current algorithm instance."""
        return self._algorithm
    
    @algorithm.setter
    def algorithm(self, value: Optional[IAlgorithm]) -> None:
        """Set the current algorithm instance."""
        self._algorithm = value
    
    @property
    def job(self) -> Optional[EngineNodePacket]:
        """Get the current job configuration."""
        return self._job
    
    @property
    def start_time(self) -> Optional[datetime]:
        """Get the engine start time."""
        return self._start_time
    
    @property
    def end_time(self) -> Optional[datetime]:
        """Get the engine end time."""
        return self._end_time
    
    @property
    def runtime(self) -> Optional[timedelta]:
        """Get the total runtime."""
        if self._start_time is None:
            return None
        end = self._end_time or datetime.utcnow()
        return end - self._start_time
    
    def initialize(self) -> bool:
        """Initialize the engine and all its components."""
        try:
            with self._lock:
                if self._status != EngineStatus.INITIALIZING:
                    self._logger.warning(f"Engine already initialized with status: {self._status}")
                    return False
                
                self._logger.info("Initializing engine components...")
                
                # Initialize components in order
                success = (
                    self._initialize_logging() and
                    self._initialize_handlers() and
                    self._validate_configuration() and
                    self._setup_monitoring()
                )
                
                if success:
                    self._status = EngineStatus.STOPPED
                    self._logger.info("Engine initialization completed successfully")
                else:
                    self._status = EngineStatus.ERROR
                    self._logger.error("Engine initialization failed")
                
                return success
                
        except Exception as e:
            self._logger.error(f"Error during engine initialization: {e}")
            self._status = EngineStatus.ERROR
            self._errors.append(f"Initialization error: {str(e)}")
            return False
    
    def run(self, job: EngineNodePacket, algorithm_manager: Optional[Any] = None) -> None:
        """Run the engine with the specified job."""
        try:
            with self._lock:
                if self._status not in [EngineStatus.STOPPED, EngineStatus.INITIALIZING]:
                    raise RuntimeError(f"Cannot run engine in status: {self._status}")
                
                self._job = job
                self._start_time = datetime.utcnow()
                self._status = EngineStatus.RUNNING
                
                self._logger.info(f"Starting engine run for job: {job.algorithm_id}")
                
                # Validate job configuration
                job.validate()
                
                # Run the main execution loop
                self._execute_main_loop()
                
        except Exception as e:
            self._logger.error(f"Error during engine run: {e}")
            self._status = EngineStatus.ERROR
            self._errors.append(f"Runtime error: {str(e)}")
            raise
        
        finally:
            self._end_time = datetime.utcnow()
            if self._status == EngineStatus.RUNNING:
                self._status = EngineStatus.STOPPED
            
            self._logger.info(f"Engine run completed. Status: {self._status}")
    
    def dispose(self) -> None:
        """Clean up engine resources."""
        try:
            with self._lock:
                if self._status == EngineStatus.DISPOSED:
                    return
                
                self._logger.info("Disposing engine resources...")
                
                # Dispose handlers in reverse order
                handlers = [
                    self._algorithm_handler,
                    self._realtime_handler,
                    self._result_handler,
                    self._transaction_handler,
                    self._data_feed,
                    self._setup_handler
                ]
                
                for handler in handlers:
                    if handler and hasattr(handler, 'dispose'):
                        try:
                            handler.dispose()
                        except Exception as e:
                            self._logger.warning(f"Error disposing handler: {e}")
                
                self._status = EngineStatus.DISPOSED
                self._logger.info("Engine disposal completed")
                
        except Exception as e:
            self._logger.error(f"Error during engine disposal: {e}")
            self._errors.append(f"Disposal error: {str(e)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        runtime = self.runtime
        return {
            'status': self._status.name,
            'total_trades': self._total_trades,
            'total_fees': float(self._total_fees),
            'total_performance': float(self._total_performance),
            'max_drawdown': float(self._max_drawdown),
            'runtime_seconds': runtime.total_seconds() if runtime else 0,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'end_time': self._end_time.isoformat() if self._end_time else None,
            'errors': len(self._errors),
            'warnings': len(self._warnings)
        }
    
    def get_errors(self) -> List[str]:
        """Get all errors encountered."""
        return self._errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get all warnings encountered."""
        return self._warnings.copy()
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    def _execute_main_loop(self) -> None:
        """Execute the main engine loop. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _create_handlers(self) -> bool:
        """Create and configure engine handlers. Must be implemented by subclasses."""
        pass
    
    # Protected helper methods
    
    def _initialize_logging(self) -> bool:
        """Initialize logging configuration."""
        try:
            if self._job:
                log_level = self._job.log_level
                logging_level = {
                    LogLevel.TRACE: logging.DEBUG,
                    LogLevel.DEBUG: logging.DEBUG,
                    LogLevel.INFO: logging.INFO,
                    LogLevel.WARN: logging.WARNING,
                    LogLevel.ERROR: logging.ERROR,
                    LogLevel.FATAL: logging.CRITICAL
                }.get(log_level, logging.INFO)
                
                self._logger.setLevel(logging_level)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize logging: {e}")
            return False
    
    def _initialize_handlers(self) -> bool:
        """Initialize all engine handlers."""
        try:
            if not self._job:
                raise RuntimeError("Job configuration required for handler initialization")
            
            return self._create_handlers()
            
        except Exception as e:
            self._logger.error(f"Failed to initialize handlers: {e}")
            return False
    
    def _validate_configuration(self) -> bool:
        """Validate the engine configuration."""
        try:
            if not self._job:
                self._errors.append("Job configuration is required")
                return False
            
            # Validate required handlers
            required_handlers = [
                ('setup_handler', self._setup_handler),
                ('data_feed', self._data_feed),
                ('transaction_handler', self._transaction_handler),
                ('result_handler', self._result_handler),
            ]
            
            for name, handler in required_handlers:
                if handler is None:
                    self._errors.append(f"Required handler not initialized: {name}")
                    return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            self._errors.append(f"Configuration validation error: {str(e)}")
            return False
    
    def _setup_monitoring(self) -> bool:
        """Setup performance monitoring."""
        try:
            # Initialize performance counters
            self._total_trades = 0
            self._total_fees = Decimal('0')
            self._total_performance = Decimal('0')
            self._max_drawdown = Decimal('0')
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to setup monitoring: {e}")
            return False
    
    def _update_performance_metrics(self, trade_value: Decimal, fees: Decimal) -> None:
        """Update performance metrics with new trade data."""
        try:
            self._total_trades += 1
            self._total_fees += fees
            self._total_performance += trade_value - fees
            
            # Calculate drawdown (simplified)
            if self._total_performance < self._max_drawdown:
                self._max_drawdown = self._total_performance
                
        except Exception as e:
            self._logger.warning(f"Error updating performance metrics: {e}")
    
    def _check_timeout(self) -> bool:
        """Check if the engine has exceeded its timeout."""
        if not self._job or not self._start_time:
            return False
        
        if self._job.timeout_minutes <= 0:
            return False
        
        runtime = datetime.utcnow() - self._start_time
        timeout = timedelta(minutes=self._job.timeout_minutes)
        
        return runtime > timeout
    
    def _stop_requested(self) -> bool:
        """Check if a stop has been requested."""
        return self._status == EngineStatus.STOPPING
    
    def _log_status(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a status message with appropriate level."""
        log_func = {
            LogLevel.TRACE: self._logger.debug,
            LogLevel.DEBUG: self._logger.debug,
            LogLevel.INFO: self._logger.info,
            LogLevel.WARN: self._logger.warning,
            LogLevel.ERROR: self._logger.error,
            LogLevel.FATAL: self._logger.critical
        }.get(level, self._logger.info)
        
        log_func(message)
        
        # Also send to result handler if available
        if self._result_handler:
            try:
                self._result_handler.send_status_update(level.name, message)
            except Exception as e:
                self._logger.warning(f"Failed to send status to result handler: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.dispose()