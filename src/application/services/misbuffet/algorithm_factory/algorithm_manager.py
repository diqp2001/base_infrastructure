"""
Algorithm manager for lifecycle management of algorithms.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from ..common.interfaces import IAlgorithm
from ..common.enums import AlgorithmStatus
from ..common.data_types import Slice
from .algorithm_node_packet import AlgorithmNodePacket


class AlgorithmState(Enum):
    """Algorithm execution state."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


class AlgorithmManager:
    """
    Manages the lifecycle and execution of algorithms.
    """
    
    def __init__(self):
        self._algorithms: Dict[str, IAlgorithm] = {}
        self._algorithm_states: Dict[str, AlgorithmState] = {}
        self._algorithm_packets: Dict[str, AlgorithmNodePacket] = {}
        self._algorithm_threads: Dict[str, threading.Thread] = {}
        
        # Statistics
        self._start_times: Dict[str, datetime] = {}
        self._end_times: Dict[str, datetime] = {}
        self._error_counts: Dict[str, int] = {}
        self._data_points_processed: Dict[str, int] = {}
        
        # Event handlers
        self.algorithm_started: Optional[Callable[[str, IAlgorithm], None]] = None
        self.algorithm_stopped: Optional[Callable[[str, IAlgorithm], None]] = None
        self.algorithm_error: Optional[Callable[[str, IAlgorithm, Exception], None]] = None
        
        # Configuration
        self._max_error_count = 10
        self._heartbeat_interval = timedelta(seconds=30)
        
        # Monitoring
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False
        self._start_monitoring()
    
    def register_algorithm(self, algorithm_id: str, algorithm: IAlgorithm, 
                          packet: AlgorithmNodePacket = None) -> bool:
        """
        Register an algorithm for management.
        
        Args:
            algorithm_id: Unique identifier for the algorithm
            algorithm: Algorithm instance
            packet: Optional configuration packet
            
        Returns:
            True if registration was successful
        """
        try:
            if algorithm_id in self._algorithms:
                raise ValueError(f"Algorithm with ID '{algorithm_id}' already registered")
            
            self._algorithms[algorithm_id] = algorithm
            self._algorithm_states[algorithm_id] = AlgorithmState.STOPPED
            self._error_counts[algorithm_id] = 0
            self._data_points_processed[algorithm_id] = 0
            
            if packet:
                self._algorithm_packets[algorithm_id] = packet
            
            return True
            
        except Exception as e:
            print(f"Failed to register algorithm '{algorithm_id}': {e}")
            return False
    
    def unregister_algorithm(self, algorithm_id: str) -> bool:
        """
        Unregister an algorithm.
        
        Args:
            algorithm_id: Algorithm identifier
            
        Returns:
            True if unregistration was successful
        """
        try:
            # Stop algorithm if running
            if self.is_running(algorithm_id):
                self.stop_algorithm(algorithm_id)
            
            # Clean up
            self._algorithms.pop(algorithm_id, None)
            self._algorithm_states.pop(algorithm_id, None)
            self._algorithm_packets.pop(algorithm_id, None)
            self._algorithm_threads.pop(algorithm_id, None)
            self._start_times.pop(algorithm_id, None)
            self._end_times.pop(algorithm_id, None)
            self._error_counts.pop(algorithm_id, None)
            self._data_points_processed.pop(algorithm_id, None)
            
            return True
            
        except Exception as e:
            print(f"Failed to unregister algorithm '{algorithm_id}': {e}")
            return False
    
    def start_algorithm(self, algorithm_id: str) -> bool:
        """
        Start an algorithm.
        
        Args:
            algorithm_id: Algorithm identifier
            
        Returns:
            True if start was successful
        """
        if algorithm_id not in self._algorithms:
            print(f"Algorithm '{algorithm_id}' not found")
            return False
        
        if self.is_running(algorithm_id):
            print(f"Algorithm '{algorithm_id}' is already running")
            return False
        
        try:
            algorithm = self._algorithms[algorithm_id]
            
            # Set state to initializing
            self._algorithm_states[algorithm_id] = AlgorithmState.INITIALIZING
            self._start_times[algorithm_id] = datetime.utcnow()
            self._error_counts[algorithm_id] = 0
            
            # Initialize algorithm
            if hasattr(algorithm, '_initialize_algorithm'):
                algorithm._initialize_algorithm()
            else:
                algorithm.initialize()
            
            # Set state to running
            self._algorithm_states[algorithm_id] = AlgorithmState.RUNNING
            
            # Notify event handler
            if self.algorithm_started:
                try:
                    self.algorithm_started(algorithm_id, algorithm)
                except Exception as e:
                    print(f"Error in algorithm_started handler: {e}")
            
            return True
            
        except Exception as e:
            self._algorithm_states[algorithm_id] = AlgorithmState.ERROR
            self._record_error(algorithm_id, e)
            print(f"Failed to start algorithm '{algorithm_id}': {e}")
            return False
    
    def stop_algorithm(self, algorithm_id: str) -> bool:
        """
        Stop an algorithm.
        
        Args:
            algorithm_id: Algorithm identifier
            
        Returns:
            True if stop was successful
        """
        if algorithm_id not in self._algorithms:
            print(f"Algorithm '{algorithm_id}' not found")
            return False
        
        if not self.is_running(algorithm_id):
            return True  # Already stopped
        
        try:
            algorithm = self._algorithms[algorithm_id]
            
            # Set state to stopping
            self._algorithm_states[algorithm_id] = AlgorithmState.STOPPING
            
            # Call algorithm cleanup
            if hasattr(algorithm, '_finalize_algorithm'):
                algorithm._finalize_algorithm()
            elif hasattr(algorithm, 'on_end_of_algorithm'):
                algorithm.on_end_of_algorithm()
            
            # Set state to stopped
            self._algorithm_states[algorithm_id] = AlgorithmState.STOPPED
            self._end_times[algorithm_id] = datetime.utcnow()
            
            # Clean up thread if exists
            if algorithm_id in self._algorithm_threads:
                thread = self._algorithm_threads[algorithm_id]
                if thread.is_alive():
                    thread.join(timeout=5.0)
                del self._algorithm_threads[algorithm_id]
            
            # Notify event handler
            if self.algorithm_stopped:
                try:
                    self.algorithm_stopped(algorithm_id, algorithm)
                except Exception as e:
                    print(f"Error in algorithm_stopped handler: {e}")
            
            return True
            
        except Exception as e:
            self._algorithm_states[algorithm_id] = AlgorithmState.ERROR
            self._record_error(algorithm_id, e)
            print(f"Failed to stop algorithm '{algorithm_id}': {e}")
            return False
    
    def process_data(self, algorithm_id: str, data_slice: Slice) -> bool:
        """
        Process data for an algorithm.
        
        Args:
            algorithm_id: Algorithm identifier
            data_slice: Data slice to process
            
        Returns:
            True if processing was successful
        """
        if algorithm_id not in self._algorithms:
            return False
        
        if not self.is_running(algorithm_id):
            return False
        
        try:
            algorithm = self._algorithms[algorithm_id]
            
            # Process data slice
            if hasattr(algorithm, '_process_data_slice'):
                algorithm._process_data_slice(data_slice)
            else:
                algorithm.on_data(data_slice)
            
            # Update statistics
            self._data_points_processed[algorithm_id] += len(data_slice.get_all_data())
            
            return True
            
        except Exception as e:
            self._record_error(algorithm_id, e)
            
            # Check error threshold
            if self._error_counts[algorithm_id] >= self._max_error_count:
                print(f"Algorithm '{algorithm_id}' exceeded error threshold, stopping")
                self.stop_algorithm(algorithm_id)
            
            return False
    
    def is_running(self, algorithm_id: str) -> bool:
        """Check if an algorithm is running."""
        state = self._algorithm_states.get(algorithm_id)
        return state in [AlgorithmState.INITIALIZING, AlgorithmState.RUNNING]
    
    def get_algorithm_state(self, algorithm_id: str) -> Optional[AlgorithmState]:
        """Get the current state of an algorithm."""
        return self._algorithm_states.get(algorithm_id)
    
    def get_algorithm(self, algorithm_id: str) -> Optional[IAlgorithm]:
        """Get an algorithm instance."""
        return self._algorithms.get(algorithm_id)
    
    def get_algorithm_packet(self, algorithm_id: str) -> Optional[AlgorithmNodePacket]:
        """Get the algorithm packet."""
        return self._algorithm_packets.get(algorithm_id)
    
    def get_running_algorithms(self) -> List[str]:
        """Get list of running algorithm IDs."""
        return [
            alg_id for alg_id, state in self._algorithm_states.items()
            if state in [AlgorithmState.INITIALIZING, AlgorithmState.RUNNING]
        ]
    
    def get_all_algorithms(self) -> List[str]:
        """Get list of all algorithm IDs."""
        return list(self._algorithms.keys())
    
    def get_algorithm_statistics(self, algorithm_id: str) -> Dict[str, Any]:
        """Get statistics for an algorithm."""
        if algorithm_id not in self._algorithms:
            return {}
        
        start_time = self._start_times.get(algorithm_id)
        end_time = self._end_times.get(algorithm_id)
        current_time = datetime.utcnow()
        
        runtime = None
        if start_time:
            if end_time:
                runtime = (end_time - start_time).total_seconds()
            else:
                runtime = (current_time - start_time).total_seconds()
        
        return {
            'algorithm_id': algorithm_id,
            'state': self._algorithm_states.get(algorithm_id, AlgorithmState.STOPPED).value,
            'start_time': start_time,
            'end_time': end_time,
            'runtime_seconds': runtime,
            'error_count': self._error_counts.get(algorithm_id, 0),
            'data_points_processed': self._data_points_processed.get(algorithm_id, 0),
            'is_running': self.is_running(algorithm_id)
        }
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics for all algorithms."""
        total_algorithms = len(self._algorithms)
        running_algorithms = len(self.get_running_algorithms())
        stopped_algorithms = sum(1 for state in self._algorithm_states.values() 
                               if state == AlgorithmState.STOPPED)
        error_algorithms = sum(1 for state in self._algorithm_states.values() 
                             if state == AlgorithmState.ERROR)
        
        total_errors = sum(self._error_counts.values())
        total_data_points = sum(self._data_points_processed.values())
        
        return {
            'total_algorithms': total_algorithms,
            'running_algorithms': running_algorithms,
            'stopped_algorithms': stopped_algorithms,
            'error_algorithms': error_algorithms,
            'total_errors': total_errors,
            'total_data_points_processed': total_data_points
        }
    
    def _record_error(self, algorithm_id: str, error: Exception):
        """Record an error for an algorithm."""
        self._error_counts[algorithm_id] = self._error_counts.get(algorithm_id, 0) + 1
        
        # Notify error handler
        if self.algorithm_error:
            try:
                algorithm = self._algorithms.get(algorithm_id)
                if algorithm:
                    self.algorithm_error(algorithm_id, algorithm, error)
            except Exception as e:
                print(f"Error in algorithm_error handler: {e}")
        
        print(f"Algorithm '{algorithm_id}' error #{self._error_counts[algorithm_id]}: {error}")
    
    def _start_monitoring(self):
        """Start the monitoring thread."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring = False
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_worker,
                daemon=True
            )
            self._monitoring_thread.start()
    
    def _monitoring_worker(self):
        """Monitoring worker thread."""
        while not self._stop_monitoring:
            try:
                # Check algorithm health
                current_time = datetime.utcnow()
                
                for algorithm_id in list(self._algorithms.keys()):
                    if self.is_running(algorithm_id):
                        # Check for hanging algorithms
                        start_time = self._start_times.get(algorithm_id)
                        if start_time:
                            runtime = current_time - start_time
                            
                            # Check if algorithm has been initializing too long
                            state = self._algorithm_states.get(algorithm_id)
                            if (state == AlgorithmState.INITIALIZING and 
                                runtime > timedelta(minutes=5)):
                                print(f"Algorithm '{algorithm_id}' stuck in initializing state")
                                self._algorithm_states[algorithm_id] = AlgorithmState.ERROR
                
                time.sleep(self._heartbeat_interval.total_seconds())
                
            except Exception as e:
                print(f"Error in monitoring worker: {e}")
                time.sleep(10)  # Sleep longer on error
    
    def stop_all_algorithms(self):
        """Stop all running algorithms."""
        running_algorithms = self.get_running_algorithms()
        
        for algorithm_id in running_algorithms:
            try:
                self.stop_algorithm(algorithm_id)
            except Exception as e:
                print(f"Error stopping algorithm '{algorithm_id}': {e}")
    
    def restart_algorithm(self, algorithm_id: str) -> bool:
        """
        Restart an algorithm.
        
        Args:
            algorithm_id: Algorithm identifier
            
        Returns:
            True if restart was successful
        """
        try:
            # Stop if running
            if self.is_running(algorithm_id):
                if not self.stop_algorithm(algorithm_id):
                    return False
            
            # Wait a moment for cleanup
            time.sleep(1.0)
            
            # Start again
            return self.start_algorithm(algorithm_id)
            
        except Exception as e:
            print(f"Failed to restart algorithm '{algorithm_id}': {e}")
            return False
    
    def dispose(self):
        """Clean up the algorithm manager."""
        # Stop monitoring
        self._stop_monitoring = True
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        
        # Stop all algorithms
        self.stop_all_algorithms()
        
        # Clear data
        self._algorithms.clear()
        self._algorithm_states.clear()
        self._algorithm_packets.clear()
        self._algorithm_threads.clear()
        self._start_times.clear()
        self._end_times.clear()
        self._error_counts.clear()
        self._data_points_processed.clear()
    
    def __str__(self) -> str:
        """String representation of the algorithm manager."""
        total = len(self._algorithms)
        running = len(self.get_running_algorithms())
        return f"AlgorithmManager(total={total}, running={running})"