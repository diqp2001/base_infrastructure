"""
Result handler implementations for QuantConnect Lean Engine Python implementation.
Handles performance tracking, result storage, and reporting.
"""

import logging
import json
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from pathlib import Path
import csv

from .interfaces import IResultHandler, IAlgorithm
from .engine_node_packet import EngineNodePacket
from .enums import ComponentState, ResultMode

# Import from common module
from ..common import OrderEvent, Portfolio


class BaseResultHandler(IResultHandler, ABC):
    """Base class for all result handler implementations."""
    
    def __init__(self):
        """Initialize the base result handler."""
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._state = ComponentState.CREATED
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Result tracking
        self._runtime_statistics: Dict[str, str] = {}
        self._charts: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self._orders: List[OrderEvent] = []
        self._trades: List[Dict[str, Any]] = []
        self._logs: List[Dict[str, Any]] = []
        
        # Performance metrics
        self._performance_metrics: Dict[str, float] = {}
        self._portfolio_values: List[Dict[str, Any]] = []
        self._benchmark_values: List[Dict[str, Any]] = []
        
        # Processing threads
        self._processing_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Configuration
        self._sample_period = timedelta(minutes=1)
        self._last_sample_time: Optional[datetime] = None
        
        self._logger.info(f"Initialized {self.__class__.__name__}")
    
    def initialize(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Initialize the result handler with algorithm and job parameters."""
        try:
            with self._lock:
                if self._state != ComponentState.CREATED:
                    self._logger.warning(f"Result handler already initialized with state: {self._state}")
                    return
                
                self._state = ComponentState.INITIALIZING
                self._algorithm = algorithm
                self._job = job
                
                self._logger.info("Initializing result handler")
                
                # Initialize storage
                self._initialize_storage()
                
                # Initialize specific components
                self._initialize_specific()
                
                # Start processing
                self._start_processing()
                
                self._state = ComponentState.INITIALIZED
                self._logger.info("Result handler initialization completed")
                
        except Exception as e:
            self._logger.error(f"Error during result handler initialization: {e}")
            self._state = ComponentState.ERROR
            raise
    
    def process_synchronous_events(self, algorithm: IAlgorithm) -> None:
        """Process algorithm events synchronously."""
        try:
            # Sample performance metrics
            self._sample_performance(algorithm)
            
            # Process any pending results
            self._process_pending_results()
            
        except Exception as e:
            self._logger.error(f"Error processing synchronous events: {e}")
    
    def send_status_update(self, status: str, message: str = "") -> None:
        """Send a status update message."""
        try:
            status_update = {
                'type': 'status',
                'status': status,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._log_event(status_update)
            self._send_result_specific(status_update)
            
        except Exception as e:
            self._logger.error(f"Error sending status update: {e}")
    
    def runtime_statistic(self, key: str, value: str) -> None:
        """Set a runtime statistic."""
        try:
            with self._lock:
                self._runtime_statistics[key] = value
                
                # Send update
                statistic_update = {
                    'type': 'runtime_statistic',
                    'key': key,
                    'value': value,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self._send_result_specific(statistic_update)
                
        except Exception as e:
            self._logger.error(f"Error setting runtime statistic: {e}")
    
    def debug_message(self, message: str) -> None:
        """Send a debug message."""
        try:
            debug_msg = {
                'type': 'debug',
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._log_event(debug_msg)
            self._logger.debug(message)
            
        except Exception as e:
            self._logger.error(f"Error sending debug message: {e}")
    
    def error_message(self, error: str, stack_trace: str = "") -> None:
        """Send an error message."""
        try:
            error_msg = {
                'type': 'error',
                'error': error,
                'stackTrace': stack_trace,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._log_event(error_msg)
            self._send_result_specific(error_msg)
            self._logger.error(f"{error} - {stack_trace}")
            
        except Exception as e:
            self._logger.error(f"Error sending error message: {e}")
    
    def log_message(self, message: str) -> None:
        """Log a message."""
        try:
            log_msg = {
                'type': 'log',
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._log_event(log_msg)
            self._logger.info(message)
            
        except Exception as e:
            self._logger.error(f"Error logging message: {e}")
    
    def chart(self, name: str, chart_type: str, series: str, 
              time: datetime, value: Union[float, Decimal]) -> None:
        """Add a point to a chart series."""
        try:
            with self._lock:
                # Initialize chart if needed
                if name not in self._charts:
                    self._charts[name] = {}
                
                if series not in self._charts[name]:
                    self._charts[name][series] = []
                
                # Add data point
                data_point = {
                    'time': time.isoformat(),
                    'value': float(value) if isinstance(value, Decimal) else value
                }
                
                self._charts[name][series].append(data_point)
                
                # Send update
                chart_update = {
                    'type': 'chart',
                    'name': name,
                    'chartType': chart_type,
                    'series': series,
                    'dataPoint': data_point
                }
                
                self._send_result_specific(chart_update)
                
        except Exception as e:
            self._logger.error(f"Error adding chart point: {e}")
    
    def store_result(self, packet: Dict[str, Any]) -> None:
        """Store a result packet."""
        try:
            # Add timestamp if not present
            if 'timestamp' not in packet:
                packet['timestamp'] = datetime.utcnow().isoformat()
            
            # Store locally
            self._store_result_locally(packet)
            
            # Send via specific implementation
            self._send_result_specific(packet)
            
        except Exception as e:
            self._logger.error(f"Error storing result: {e}")
    
    def send_final_result(self) -> None:
        """Send the final results."""
        try:
            self._logger.info("Preparing final results")
            
            # Calculate final performance metrics
            final_metrics = self._calculate_final_metrics()
            
            # Create final result packet
            final_result = {
                'type': 'final_result',
                'performance_metrics': final_metrics,
                'runtime_statistics': self._runtime_statistics.copy(),
                'charts': self._charts.copy(),
                'orders': len(self._orders),
                'trades': len(self._trades),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store and send final result
            self.store_result(final_result)
            
            # Perform specific finalization
            self._finalize_specific()
            
            self._logger.info("Final results sent")
            
        except Exception as e:
            self._logger.error(f"Error sending final result: {e}")
    
    def exit(self) -> None:
        """Exit and cleanup the result handler."""
        try:
            with self._lock:
                if self._state == ComponentState.DISPOSED:
                    return
                
                self._logger.info("Exiting result handler")
                
                # Stop processing
                self._stop_processing()
                
                # Cleanup specific resources
                self._cleanup_specific()
                
                self._state = ComponentState.DISPOSED
                self._logger.info("Result handler exited")
                
        except Exception as e:
            self._logger.error(f"Error during result handler exit: {e}")
    
    # Abstract methods for specific implementations
    
    @abstractmethod
    def _initialize_specific(self) -> None:
        """Perform specific initialization. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _send_result_specific(self, result: Dict[str, Any]) -> None:
        """Send result via specific implementation. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _finalize_specific(self) -> None:
        """Perform specific finalization. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cleanup_specific(self) -> None:
        """Perform specific cleanup. Must be implemented by subclasses."""
        pass
    
    # Protected helper methods
    
    def _initialize_storage(self) -> None:
        """Initialize result storage."""
        try:
            if self._job:
                # Ensure results folder exists
                results_folder = Path(self._job.results_folder)
                results_folder.mkdir(parents=True, exist_ok=True)
                
                # Initialize runtime statistics
                self._runtime_statistics = {
                    'Algorithm Id': self._job.algorithm_id,
                    'Algorithm Name': self._job.algorithm_name,
                    'Start Date': self._job.start_date.isoformat() if self._job.start_date else '',
                    'End Date': self._job.end_date.isoformat() if self._job.end_date else '',
                    'Starting Capital': str(self._job.starting_capital),
                    'Engine Mode': self._job.engine_mode.value
                }
            
        except Exception as e:
            self._logger.error(f"Error initializing storage: {e}")
            raise
    
    def _sample_performance(self, algorithm: IAlgorithm) -> None:
        """Sample algorithm performance metrics."""
        try:
            current_time = datetime.utcnow()
            
            # Check if it's time to sample
            if (self._last_sample_time and 
                current_time - self._last_sample_time < self._sample_period):
                return
            
            self._last_sample_time = current_time
            
            # Sample portfolio value (simplified)
            if hasattr(algorithm, 'portfolio'):
                portfolio_value = float(algorithm.portfolio.total_portfolio_value)
                
                portfolio_sample = {
                    'time': current_time.isoformat(),
                    'portfolio_value': portfolio_value,
                    'cash': float(algorithm.portfolio.cash_book.total_value_in_account_currency),
                    'holdings_value': portfolio_value - float(algorithm.portfolio.cash_book.total_value_in_account_currency)
                }
                
                self._portfolio_values.append(portfolio_sample)
                
                # Update runtime statistics
                self.runtime_statistic('Portfolio Value', f"${portfolio_value:,.2f}")
                self.runtime_statistic('Cash', f"${float(algorithm.portfolio.cash_book.total_value_in_account_currency):,.2f}")
            
        except Exception as e:
            self._logger.warning(f"Error sampling performance: {e}")
    
    def _process_pending_results(self) -> None:
        """Process any pending results."""
        try:
            # This would handle any queued results that need processing
            pass
            
        except Exception as e:
            self._logger.error(f"Error processing pending results: {e}")
    
    def _log_event(self, event: Dict[str, Any]) -> None:
        """Log an event locally."""
        try:
            with self._lock:
                self._logs.append(event)
                
                # Limit log size
                if len(self._logs) > 10000:
                    self._logs = self._logs[-5000:]  # Keep last 5000 logs
                    
        except Exception as e:
            self._logger.error(f"Error logging event: {e}")
    
    def _store_result_locally(self, result: Dict[str, Any]) -> None:
        """Store result locally."""
        try:
            # This would store results to local files or database
            # Implementation depends on storage requirements
            pass
            
        except Exception as e:
            self._logger.error(f"Error storing result locally: {e}")
    
    def _calculate_final_metrics(self) -> Dict[str, float]:
        """Calculate final performance metrics."""
        try:
            metrics = {}
            
            if self._portfolio_values:
                # Calculate basic metrics
                starting_value = self._portfolio_values[0]['portfolio_value'] if self._portfolio_values else float(self._job.starting_capital)
                ending_value = self._portfolio_values[-1]['portfolio_value'] if self._portfolio_values else starting_value
                
                total_return = (ending_value - starting_value) / starting_value if starting_value > 0 else 0
                
                metrics.update({
                    'Total Return': total_return,
                    'Starting Portfolio Value': starting_value,
                    'Ending Portfolio Value': ending_value,
                    'Total Orders': len(self._orders),
                    'Total Trades': len(self._trades)
                })
                
                # Calculate additional metrics (simplified)
                if len(self._portfolio_values) > 1:
                    daily_returns = []
                    for i in range(1, len(self._portfolio_values)):
                        prev_value = self._portfolio_values[i-1]['portfolio_value']
                        curr_value = self._portfolio_values[i]['portfolio_value']
                        if prev_value > 0:
                            daily_return = (curr_value - prev_value) / prev_value
                            daily_returns.append(daily_return)
                    
                    if daily_returns:
                        import statistics
                        avg_daily_return = statistics.mean(daily_returns)
                        volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
                        
                        # Annualize metrics (simplified)
                        annual_return = avg_daily_return * 252  # Assuming 252 trading days
                        annual_volatility = volatility * (252 ** 0.5)
                        
                        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
                        
                        metrics.update({
                            'Annual Return': annual_return,
                            'Annual Volatility': annual_volatility,
                            'Sharpe Ratio': sharpe_ratio
                        })
            
            return metrics
            
        except Exception as e:
            self._logger.error(f"Error calculating final metrics: {e}")
            return {}
    
    def _start_processing(self) -> None:
        """Start result processing thread."""
        try:
            self._shutdown_event.clear()
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                name="ResultProcessingThread"
            )
            self._processing_thread.daemon = True
            self._processing_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting processing: {e}")
    
    def _stop_processing(self) -> None:
        """Stop result processing thread."""
        try:
            self._shutdown_event.set()
            
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping processing: {e}")
    
    def _processing_loop(self) -> None:
        """Main processing loop for results."""
        try:
            self._logger.info("Result processing loop started")
            
            while not self._shutdown_event.is_set():
                try:
                    # Perform periodic tasks
                    self._periodic_processing()
                    
                    # Sleep briefly
                    time.sleep(1.0)
                    
                except Exception as e:
                    self._logger.error(f"Error in processing loop: {e}")
                    time.sleep(5.0)
            
            self._logger.info("Result processing loop stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in processing loop: {e}")
    
    def _periodic_processing(self) -> None:
        """Perform periodic processing tasks."""
        try:
            # This would handle periodic tasks like:
            # - Flushing buffered results
            # - Calculating intermediate metrics
            # - Cleanup old data
            pass
            
        except Exception as e:
            self._logger.error(f"Error in periodic processing: {e}")


class BacktestingResultHandler(BaseResultHandler):
    """Result handler for backtesting with file-based storage."""
    
    def __init__(self):
        """Initialize the backtesting result handler."""
        super().__init__()
        self._results_file: Optional[Path] = None
        self._charts_file: Optional[Path] = None
        self._orders_file: Optional[Path] = None
        self._logs_file: Optional[Path] = None
    
    def _initialize_specific(self) -> None:
        """Initialize backtesting specific components."""
        try:
            if not self._job:
                return
            
            # Setup result files
            results_folder = Path(self._job.results_folder)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            self._results_file = results_folder / f"backtest_results_{timestamp}.json"
            self._charts_file = results_folder / f"backtest_charts_{timestamp}.json"
            self._orders_file = results_folder / f"backtest_orders_{timestamp}.csv"
            self._logs_file = results_folder / f"backtest_logs_{timestamp}.json"
            
            self._logger.info(f"Backtesting results will be saved to: {results_folder}")
            
        except Exception as e:
            self._logger.error(f"Backtesting result handler initialization failed: {e}")
            raise
    
    def _send_result_specific(self, result: Dict[str, Any]) -> None:
        """Send result to file storage."""
        try:
            # For backtesting, we primarily store to files
            # In a real implementation, you might also send to a UI or API
            pass
            
        except Exception as e:
            self._logger.error(f"Error sending backtesting result: {e}")
    
    def _finalize_specific(self) -> None:
        """Finalize backtesting results."""
        try:
            # Save final results to files
            self._save_results_to_files()
            
            # Generate summary report
            self._generate_summary_report()
            
        except Exception as e:
            self._logger.error(f"Error finalizing backtesting results: {e}")
    
    def _cleanup_specific(self) -> None:
        """Cleanup backtesting specific resources."""
        try:
            # No specific cleanup needed for file-based storage
            pass
            
        except Exception as e:
            self._logger.error(f"Error in backtesting cleanup: {e}")
    
    def _save_results_to_files(self) -> None:
        """Save all results to files."""
        try:
            # Save main results
            if self._results_file:
                results_data = {
                    'runtime_statistics': self._runtime_statistics,
                    'performance_metrics': self._performance_metrics,
                    'portfolio_values': self._portfolio_values,
                    'final_metrics': self._calculate_final_metrics()
                }
                
                with open(self._results_file, 'w') as f:
                    json.dump(results_data, f, indent=2)
            
            # Save charts
            if self._charts_file and self._charts:
                with open(self._charts_file, 'w') as f:
                    json.dump(self._charts, f, indent=2)
            
            # Save orders (CSV format)
            if self._orders_file and self._orders:
                with open(self._orders_file, 'w', newline='') as f:
                    if self._orders:
                        writer = csv.DictWriter(f, fieldnames=['order_id', 'symbol', 'time', 'status', 'direction', 'quantity', 'fill_price'])
                        writer.writeheader()
                        for order in self._orders:
                            writer.writerow({
                                'order_id': order.order_id,
                                'symbol': order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol),
                                'time': order.time.isoformat(),
                                'status': order.status.name if hasattr(order.status, 'name') else str(order.status),
                                'direction': order.direction.name if hasattr(order.direction, 'name') else str(order.direction),
                                'quantity': order.fill_quantity,
                                'fill_price': float(order.fill_price)
                            })
            
            # Save logs
            if self._logs_file and self._logs:
                with open(self._logs_file, 'w') as f:
                    json.dump(self._logs, f, indent=2)
            
            self._logger.info("Results saved to files")
            
        except Exception as e:
            self._logger.error(f"Error saving results to files: {e}")
    
    def _generate_summary_report(self) -> None:
        """Generate a summary report."""
        try:
            if not self._job:
                return
            
            summary_file = Path(self._job.results_folder) / "backtest_summary.txt"
            
            with open(summary_file, 'w') as f:
                f.write("BACKTESTING SUMMARY REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                # Basic info
                f.write(f"Algorithm: {self._job.algorithm_name}\n")
                f.write(f"Period: {self._job.start_date} to {self._job.end_date}\n")
                f.write(f"Starting Capital: ${self._job.starting_capital:,}\n\n")
                
                # Performance metrics
                final_metrics = self._calculate_final_metrics()
                f.write("PERFORMANCE METRICS:\n")
                f.write("-" * 20 + "\n")
                for key, value in final_metrics.items():
                    if isinstance(value, float):
                        if 'Return' in key or 'Ratio' in key:
                            f.write(f"{key}: {value:.2%}\n")
                        else:
                            f.write(f"{key}: {value:.2f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                
                f.write("\nRUNTIME STATISTICS:\n")
                f.write("-" * 20 + "\n")
                for key, value in self._runtime_statistics.items():
                    f.write(f"{key}: {value}\n")
            
            self._logger.info(f"Summary report generated: {summary_file}")
            
        except Exception as e:
            self._logger.error(f"Error generating summary report: {e}")


class LiveTradingResultHandler(BaseResultHandler):
    """Result handler for live trading with real-time reporting."""
    
    def __init__(self):
        """Initialize the live trading result handler."""
        super().__init__()
        self._api_endpoint: Optional[str] = None
        self._websocket_connection: Optional[Any] = None
        self._result_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.Lock()
    
    def _initialize_specific(self) -> None:
        """Initialize live trading specific components."""
        try:
            # Setup real-time communication
            # In practice, this would connect to APIs, WebSockets, etc.
            self._logger.info("Initializing live trading result handler")
            
            # Initialize real-time reporting
            self._setup_realtime_reporting()
            
        except Exception as e:
            self._logger.error(f"Live trading result handler initialization failed: {e}")
            raise
    
    def _send_result_specific(self, result: Dict[str, Any]) -> None:
        """Send result via real-time channels."""
        try:
            # Queue result for real-time transmission
            with self._queue_lock:
                self._result_queue.append(result)
            
            # In practice, this would send via WebSocket, API, etc.
            self._logger.debug(f"Queued result for transmission: {result.get('type', 'unknown')}")
            
        except Exception as e:
            self._logger.error(f"Error sending live trading result: {e}")
    
    def _finalize_specific(self) -> None:
        """Finalize live trading results."""
        try:
            # Send any remaining queued results
            self._flush_result_queue()
            
            # Close real-time connections
            self._close_realtime_connections()
            
        except Exception as e:
            self._logger.error(f"Error finalizing live trading results: {e}")
    
    def _cleanup_specific(self) -> None:
        """Cleanup live trading specific resources."""
        try:
            self._close_realtime_connections()
            
        except Exception as e:
            self._logger.error(f"Error in live trading cleanup: {e}")
    
    def _setup_realtime_reporting(self) -> None:
        """Setup real-time reporting channels."""
        try:
            # This would setup WebSocket connections, API endpoints, etc.
            # For now, we'll use a simple queue-based approach
            self._logger.info("Real-time reporting setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up real-time reporting: {e}")
    
    def _flush_result_queue(self) -> None:
        """Flush any remaining results in the queue."""
        try:
            with self._queue_lock:
                pending_count = len(self._result_queue)
                if pending_count > 0:
                    self._logger.info(f"Flushing {pending_count} pending results")
                    # In practice, send these via real-time channels
                    self._result_queue.clear()
                    
        except Exception as e:
            self._logger.error(f"Error flushing result queue: {e}")
    
    def _close_realtime_connections(self) -> None:
        """Close real-time connections."""
        try:
            # Close WebSocket connections, API sessions, etc.
            if self._websocket_connection:
                # self._websocket_connection.close()
                self._websocket_connection = None
            
            self._logger.info("Real-time connections closed")
            
        except Exception as e:
            self._logger.error(f"Error closing real-time connections: {e}")
    
    def _periodic_processing(self) -> None:
        """Perform periodic processing for live trading."""
        try:
            # Send queued results
            with self._queue_lock:
                if self._result_queue:
                    # Process a batch of results
                    batch = self._result_queue[:10]  # Process up to 10 at a time
                    self._result_queue = self._result_queue[10:]
                    
                    for result in batch:
                        # In practice, send via real-time channels
                        self._logger.debug(f"Processing queued result: {result.get('type', 'unknown')}")
            
        except Exception as e:
            self._logger.error(f"Error in live trading periodic processing: {e}")