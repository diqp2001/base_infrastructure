"""
LeanEngine implementation for QuantConnect Lean Engine Python implementation.
Main orchestration engine that coordinates all components.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_engine import BaseEngine
from .interfaces import IAlgorithm
from .enums import (
    EngineStatus, AlgorithmStatus, EngineMode, ComponentState
)
from .engine_node_packet import EngineNodePacket

# Import handlers (will be implemented next)
from .data_feeds import FileSystemDataFeed, LiveDataFeed, BacktestingDataFeed
from .transaction_handlers import BacktestingTransactionHandler, BrokerageTransactionHandler
from .result_handlers import BacktestingResultHandler, LiveTradingResultHandler
from .setup_handlers import ConsoleSetupHandler, BacktestingSetupHandler
from .realtime_handlers import BacktestingRealTimeHandler, LiveTradingRealTimeHandler
from .algorithm_handlers import AlgorithmHandler

# Import from common module using relative imports
from ..common import Slice, OrderEvent


class LeanEngine(BaseEngine):
    """
    Main Lean engine implementation.
    Orchestrates all engine components for backtesting and live trading.
    """
    
    def __init__(self):
        """Initialize the Lean engine."""
        super().__init__()
        self._algorithm_manager: Optional[Any] = None
        self._main_loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._data_processing_thread: Optional[threading.Thread] = None
        self._current_time: Optional[datetime] = None
        self._last_data_time: Optional[datetime] = None
        
        # Performance tracking
        self._processed_data_points = 0
        self._algorithm_iterations = 0
        self._last_performance_update = datetime.utcnow()
        
        self._logger.info("Initialized LeanEngine")
    
    def run(self, job: EngineNodePacket, algorithm_manager: Optional[Any] = None) -> None:
        """Run the Lean engine with the specified job and algorithm manager."""
        try:
            self._algorithm_manager = algorithm_manager
            self._logger.info(f"Starting Lean engine for job: {job.algorithm_id}")
            
            # Call base class run method
            super().run(job, algorithm_manager)
            
        except Exception as e:
            self._logger.error(f"Error in LeanEngine.run: {e}")
            self._errors.append(f"LeanEngine run error: {str(e)}")
            raise
    
    def _execute_main_loop(self) -> None:
        """Execute the main engine loop."""
        try:
            self._logger.info("Starting main execution loop")
            
            # Setup algorithm
            if not self._setup_algorithm():
                raise RuntimeError("Algorithm setup failed")
            
            # Initialize all handlers
            if not self._initialize_all_handlers():
                raise RuntimeError("Handler initialization failed")
            
            # Start data processing
            self._start_data_processing()
            
            # Run main loop based on engine mode
            if self._job.engine_mode == EngineMode.BACKTESTING:
                self._run_backtesting_loop()
            elif self._job.engine_mode == EngineMode.LIVE_TRADING:
                self._run_live_trading_loop()
            else:
                raise ValueError(f"Unsupported engine mode: {self._job.engine_mode}")
            
            # Send final results
            self._finalize_results()
            
        except Exception as e:
            self._logger.error(f"Error in main execution loop: {e}")
            self._errors.append(f"Main loop error: {str(e)}")
            raise
        
        finally:
            self._stop_data_processing()
    
    def _create_handlers(self) -> bool:
        """Create and configure engine handlers."""
        try:
            if not self._job:
                return False
            
            self._logger.info("Creating engine handlers")
            
            # Create setup handler
            self._setup_handler = self._create_setup_handler()
            if not self._setup_handler:
                return False
            
            # Create data feed
            self._data_feed = self._create_data_feed()
            if not self._data_feed:
                return False
            
            # Create transaction handler  
            self._transaction_handler = self._create_transaction_handler()
            if not self._transaction_handler:
                return False
            
            # Create result handler
            self._result_handler = self._create_result_handler()
            if not self._result_handler:
                return False
            
            # Create realtime handler
            self._realtime_handler = self._create_realtime_handler()
            if not self._realtime_handler:
                return False
            
            # Create algorithm handler
            self._algorithm_handler = self._create_algorithm_handler()
            if not self._algorithm_handler:
                return False
            
            self._logger.info("All handlers created successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Error creating handlers: {e}")
            return False
    
    def _create_setup_handler(self):
        """Create the setup handler based on configuration."""
        handler_name = self._job.setup_handler
        
        if handler_name == "ConsoleSetupHandler":
            return ConsoleSetupHandler()
        elif handler_name == "BacktestingSetupHandler":
            return BacktestingSetupHandler()
        else:
            self._logger.warning(f"Unknown setup handler: {handler_name}, using default")
            return ConsoleSetupHandler()
    
    def _create_data_feed(self):
        """Create the data feed based on configuration."""
        handler_name = self._job.data_feed_handler
        
        if handler_name == "FileSystemDataFeed":
            return FileSystemDataFeed()
        elif handler_name == "LiveDataFeed":
            return LiveDataFeed()
        elif handler_name == "BacktestingDataFeed":
            return BacktestingDataFeed()
        else:
            self._logger.warning(f"Unknown data feed: {handler_name}, using default")
            return FileSystemDataFeed()
    
    def _create_transaction_handler(self):
        """Create the transaction handler based on configuration."""
        handler_name = self._job.transaction_handler
        
        if handler_name == "BacktestingTransactionHandler":
            return BacktestingTransactionHandler()
        elif handler_name == "BrokerageTransactionHandler":
            return BrokerageTransactionHandler()
        else:
            self._logger.warning(f"Unknown transaction handler: {handler_name}, using default")
            return BacktestingTransactionHandler()
    
    def _create_result_handler(self):
        """Create the result handler based on configuration."""
        handler_name = self._job.result_handler
        
        if handler_name == "BacktestingResultHandler":
            return BacktestingResultHandler()
        elif handler_name == "LiveTradingResultHandler":
            return LiveTradingResultHandler()
        else:
            self._logger.warning(f"Unknown result handler: {handler_name}, using default")
            return BacktestingResultHandler()
    
    def _create_realtime_handler(self):
        """Create the realtime handler based on configuration."""
        handler_name = self._job.realtime_handler
        
        if handler_name == "BacktestingRealTimeHandler":
            return BacktestingRealTimeHandler()
        elif handler_name == "LiveTradingRealTimeHandler":
            return LiveTradingRealTimeHandler()
        else:
            self._logger.warning(f"Unknown realtime handler: {handler_name}, using default")
            return BacktestingRealTimeHandler()
    
    def _create_algorithm_handler(self):
        """Create the algorithm handler."""
        return AlgorithmHandler()
    
    def _setup_algorithm(self) -> bool:
        """Setup the algorithm instance."""
        try:
            self._logger.info("Setting up algorithm")
            
            if not self._setup_handler:
                raise RuntimeError("Setup handler not initialized")
            
            # Create algorithm instance
            self._algorithm = self._setup_handler.setup(self._job)
            if not self._algorithm:
                raise RuntimeError("Failed to create algorithm instance")
            
            self._logger.info(f"Algorithm setup completed: {self._algorithm.__class__.__name__}")
            return True
            
        except Exception as e:
            self._logger.error(f"Algorithm setup failed: {e}")
            self._errors.append(f"Algorithm setup error: {str(e)}")
            return False
    
    def _initialize_all_handlers(self) -> bool:
        """Initialize all handlers with algorithm and job."""
        try:
            self._logger.info("Initializing all handlers")
            
            if not self._algorithm:
                raise RuntimeError("Algorithm not setup")
            
            # Initialize data feed
            if not self._data_feed.initialize(self._algorithm, self._job):
                raise RuntimeError("Data feed initialization failed")
            
            # Initialize transaction handler
            self._transaction_handler.initialize(self._algorithm, None)  # Brokerage passed as None for backtesting
            
            # Initialize result handler
            self._result_handler.initialize(self._algorithm, self._job)
            
            # Initialize realtime handler
            self._realtime_handler.initialize(self._algorithm, self._job)
            
            # Initialize algorithm handler
            if not self._algorithm_handler.initialize(self._job, self._algorithm):
                raise RuntimeError("Algorithm handler initialization failed")
            
            self._logger.info("All handlers initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Handler initialization failed: {e}")
            self._errors.append(f"Handler initialization error: {str(e)}")
            return False
    
    def _start_data_processing(self) -> None:
        """Start the data processing thread."""
        try:
            self._logger.info("Starting data processing")
            self._shutdown_event.clear()
            
            self._data_processing_thread = threading.Thread(
                target=self._data_processing_loop,
                name="DataProcessingThread"
            )
            self._data_processing_thread.daemon = True
            self._data_processing_thread.start()
            
        except Exception as e:
            self._logger.error(f"Failed to start data processing: {e}")
            raise
    
    def _stop_data_processing(self) -> None:
        """Stop the data processing thread."""
        try:
            self._logger.info("Stopping data processing")
            self._shutdown_event.set()
            
            if self._data_processing_thread and self._data_processing_thread.is_alive():
                self._data_processing_thread.join(timeout=5.0)
                if self._data_processing_thread.is_alive():
                    self._logger.warning("Data processing thread did not stop gracefully")
            
        except Exception as e:
            self._logger.error(f"Error stopping data processing: {e}")
    
    def _data_processing_loop(self) -> None:
        """Main data processing loop running in separate thread."""
        try:
            self._logger.info("Data processing loop started")
            
            while not self._shutdown_event.is_set() and self._status == EngineStatus.RUNNING:
                try:
                    # Get next data batch
                    data_points = self._data_feed.get_next_ticks()
                    
                    if not data_points:
                        # No more data available
                        if self._job.engine_mode == EngineMode.BACKTESTING:
                            self._logger.info("No more data available, ending backtest")
                            break
                        else:
                            # Live trading - wait for more data
                            time.sleep(0.1)
                            continue
                    
                    # Process data points
                    for data_point in data_points:
                        if self._shutdown_event.is_set():
                            break
                        
                        self._process_data_point(data_point)
                        self._processed_data_points += 1
                    
                    # Update current time
                    if data_points:
                        self._current_time = data_points[-1].end_time
                        self._last_data_time = self._current_time
                    
                    # Update performance metrics periodically
                    self._update_performance_tracking()
                    
                    # Check for timeout
                    if self._check_timeout():
                        self._logger.warning("Engine timeout reached")
                        break
                    
                except Exception as e:
                    self._logger.error(f"Error in data processing loop: {e}")
                    self._errors.append(f"Data processing error: {str(e)}")
                    break
            
            self._logger.info("Data processing loop completed")
            
        except Exception as e:
            self._logger.error(f"Fatal error in data processing loop: {e}")
            self._errors.append(f"Fatal data processing error: {str(e)}")
    
    def _process_data_point(self, data_point) -> None:
        """Process a single data point."""
        try:
            # Update realtime handler
            if self._realtime_handler:
                self._realtime_handler.set_time(data_point.end_time)
            
            # Create slice and pass to algorithm
            slice_data = self._create_slice([data_point])
            if slice_data and self._algorithm_handler:
                self._algorithm_handler.on_data(slice_data)
                self._algorithm_iterations += 1
            
        except Exception as e:
            self._logger.error(f"Error processing data point: {e}")
            self._warnings.append(f"Data processing warning: {str(e)}")
    
    def _create_slice(self, data_points) -> Optional[Slice]:
        """Create a data slice from data points."""
        try:
            # This is a simplified implementation
            # In the real implementation, this would create a proper Slice object
            # with all the data organized by symbol and type
            if not data_points:
                return None
            
            # For now, return a basic slice
            # This would need to be implemented properly based on the Slice class
            return None  # Placeholder
            
        except Exception as e:
            self._logger.error(f"Error creating slice: {e}")
            return None
    
    def _run_backtesting_loop(self) -> None:
        """Run the backtesting execution loop."""
        try:
            self._logger.info("Starting backtesting loop")
            
            start_time = self._job.start_date
            end_time = self._job.end_date
            
            self._logger.info(f"Backtesting period: {start_time} to {end_time}")
            
            # Set algorithm time to start
            if self._realtime_handler:
                self._realtime_handler.set_time(start_time)
            
            # Wait for data processing to complete
            if self._data_processing_thread:
                self._data_processing_thread.join()
            
            self._logger.info("Backtesting loop completed")
            
        except Exception as e:
            self._logger.error(f"Error in backtesting loop: {e}")
            raise
    
    def _run_live_trading_loop(self) -> None:
        """Run the live trading execution loop."""
        try:
            self._logger.info("Starting live trading loop")
            
            # In live trading, we run until stopped
            while (self._status == EngineStatus.RUNNING and 
                   not self._shutdown_event.is_set() and 
                   not self._check_timeout()):
                
                # Process synchronous events
                if self._result_handler:
                    self._result_handler.process_synchronous_events(self._algorithm)
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.1)
            
            self._logger.info("Live trading loop completed")
            
        except Exception as e:
            self._logger.error(f"Error in live trading loop: {e}")
            raise
    
    def _update_performance_tracking(self) -> None:
        """Update performance tracking metrics."""
        try:
            now = datetime.utcnow()
            if (now - self._last_performance_update).total_seconds() >= 60:  # Update every minute
                
                if self._result_handler:
                    self._result_handler.runtime_statistic("Data Points Processed", str(self._processed_data_points))
                    self._result_handler.runtime_statistic("Algorithm Iterations", str(self._algorithm_iterations))
                    
                    if self.runtime:
                        self._result_handler.runtime_statistic("Runtime (seconds)", str(int(self.runtime.total_seconds())))
                
                self._last_performance_update = now
                
        except Exception as e:
            self._logger.warning(f"Error updating performance tracking: {e}")
    
    def _finalize_results(self) -> None:
        """Finalize and send results."""
        try:
            self._logger.info("Finalizing results")
            
            if self._result_handler:
                # Send final performance metrics
                metrics = self.get_performance_metrics()
                self._result_handler.store_result({
                    'type': 'FinalResults',
                    'metrics': metrics,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Send final result
                self._result_handler.send_final_result()
            
            self._logger.info("Results finalized")
            
        except Exception as e:
            self._logger.error(f"Error finalizing results: {e}")
            self._errors.append(f"Result finalization error: {str(e)}")
    
    def stop(self) -> None:
        """Request the engine to stop."""
        try:
            self._logger.info("Stop requested")
            self._status = EngineStatus.STOPPING
            self._shutdown_event.set()
            
        except Exception as e:
            self._logger.error(f"Error during stop: {e}")
    
    def get_algorithm_status(self) -> Optional[AlgorithmStatus]:
        """Get the current algorithm status."""
        if self._algorithm_handler:
            return self._algorithm_handler.get_status()
        return None
    
    def get_realtime_statistics(self) -> Dict[str, Any]:
        """Get real-time statistics."""
        return {
            'status': self._status.name,
            'algorithm_status': self.get_algorithm_status().name if self.get_algorithm_status() else None,
            'current_time': self._current_time.isoformat() if self._current_time else None,
            'last_data_time': self._last_data_time.isoformat() if self._last_data_time else None,
            'processed_data_points': self._processed_data_points,
            'algorithm_iterations': self._algorithm_iterations,
            'runtime_seconds': self.runtime.total_seconds() if self.runtime else 0,
            'errors': len(self._errors),
            'warnings': len(self._warnings)
        }