"""
QuantConnect Lean Optimizer.Launcher Worker Manager

Manages worker nodes for distributed optimization execution including
local processes, Docker containers, and cloud instances.
"""

import asyncio
import logging
import multiprocessing
import subprocess
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import queue

from .interfaces import (
    IWorkerManager, 
    WorkerStatus, 
    WorkerManagementException,
    JobSubmissionException,
    IOptimizerNodePacket
)
from .node_packet import OptimizerNodePacket
from ..optimizer.result_management import OptimizationResult


@dataclass
class WorkerInfo:
    """Information about a worker node."""
    
    worker_id: str
    status: WorkerStatus
    created_time: datetime
    last_heartbeat: datetime
    current_job_id: Optional[str] = None
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_execution_time: float = 0.0
    resource_usage: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = {}


class LocalWorkerManager(IWorkerManager):
    """
    Worker manager for local process-based execution.
    Uses multiprocessing for parallel optimization jobs.
    """
    
    def __init__(self, max_workers: int = None, logger: Optional[logging.Logger] = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.logger = logger or logging.getLogger(__name__)
        
        self._workers: Dict[str, WorkerInfo] = {}
        self._executor: Optional[ProcessPoolExecutor] = None
        self._job_queue: queue.Queue = queue.Queue()
        self._result_queue: queue.Queue = queue.Queue()
        self._running_jobs: Dict[str, Future] = {}
        self._shutdown_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    async def start_workers(self, count: int) -> bool:
        """Start the specified number of worker processes."""
        try:
            if self._executor is not None:
                self.logger.warning("Workers already started")
                return True
            
            worker_count = min(count, self.max_workers)
            self._executor = ProcessPoolExecutor(max_workers=worker_count)
            
            # Create worker info records
            for i in range(worker_count):
                worker_id = f"local-worker-{i}-{uuid.uuid4().hex[:8]}"
                worker_info = WorkerInfo(
                    worker_id=worker_id,
                    status=WorkerStatus.IDLE,
                    created_time=datetime.now(timezone.utc),
                    last_heartbeat=datetime.now(timezone.utc)
                )
                self._workers[worker_id] = worker_info
            
            # Start monitoring thread
            self._monitor_thread = threading.Thread(target=self._monitor_workers, daemon=True)
            self._monitor_thread.start()
            
            self.logger.info(f"Started {worker_count} local workers")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to start workers: {e}")
            raise WorkerManagementException(f"Failed to start workers: {e}")
    
    async def stop_workers(self) -> bool:
        """Stop all worker processes gracefully."""
        try:
            self._shutdown_event.set()
            
            if self._executor:
                # Cancel running jobs
                for job_id, future in self._running_jobs.items():
                    future.cancel()
                    self.logger.info(f"Cancelled job {job_id}")
                
                # Shutdown executor
                self._executor.shutdown(wait=True)
                self._executor = None
            
            # Wait for monitor thread
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            
            # Update worker status
            with self._lock:
                for worker_info in self._workers.values():
                    worker_info.status = WorkerStatus.DISCONNECTED
            
            self.logger.info("Stopped all local workers")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to stop workers: {e}")
            return False
    
    async def submit_job(self, packet: IOptimizerNodePacket) -> str:
        """Submit a job to an available worker."""
        if not self._executor:
            raise JobSubmissionException("Workers not started")
        
        try:
            # Find available worker
            available_worker = self._find_available_worker()
            if not available_worker:
                raise JobSubmissionException("No available workers")
            
            # Submit job to executor
            future = self._executor.submit(self._execute_job, packet)
            
            # Track the job
            job_id = packet.job_id
            self._running_jobs[job_id] = future
            
            # Update worker status
            with self._lock:
                available_worker.status = WorkerStatus.BUSY
                available_worker.current_job_id = job_id
                available_worker.last_heartbeat = datetime.now(timezone.utc)
            
            self.logger.info(f"Submitted job {job_id} to worker {available_worker.worker_id}")
            return job_id
        
        except Exception as e:
            self.logger.error(f"Failed to submit job: {e}")
            raise JobSubmissionException(f"Failed to submit job: {e}")
    
    async def get_job_result(self, job_id: str) -> Optional[OptimizationResult]:
        """Get result for a specific job."""
        if job_id not in self._running_jobs:
            return None
        
        future = self._running_jobs[job_id]
        
        if future.done():
            try:
                result = future.result()
                # Cleanup completed job
                del self._running_jobs[job_id]
                self._update_worker_after_job_completion(job_id, success=True)
                return result
            except Exception as e:
                self.logger.error(f"Job {job_id} failed: {e}")
                del self._running_jobs[job_id]
                self._update_worker_after_job_completion(job_id, success=False)
                return None
        
        return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job."""
        if job_id not in self._running_jobs:
            return False
        
        try:
            future = self._running_jobs[job_id]
            success = future.cancel()
            
            if success:
                del self._running_jobs[job_id]
                self._update_worker_after_job_completion(job_id, success=False)
                self.logger.info(f"Cancelled job {job_id}")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def get_worker_count(self) -> int:
        """Get total number of workers."""
        return len(self._workers)
    
    def get_active_workers(self) -> int:
        """Get number of active workers."""
        with self._lock:
            return sum(1 for w in self._workers.values() 
                      if w.status in [WorkerStatus.IDLE, WorkerStatus.BUSY])
    
    def get_worker_status(self) -> Dict[str, WorkerStatus]:
        """Get status of all workers."""
        with self._lock:
            return {worker_id: info.status for worker_id, info in self._workers.items()}
    
    def get_worker_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed worker statistics."""
        with self._lock:
            stats = {}
            for worker_id, info in self._workers.items():
                stats[worker_id] = {
                    'status': info.status.value,
                    'completed_jobs': info.completed_jobs,
                    'failed_jobs': info.failed_jobs,
                    'total_execution_time': info.total_execution_time,
                    'uptime': (datetime.now(timezone.utc) - info.created_time).total_seconds(),
                    'current_job_id': info.current_job_id
                }
            return stats
    
    def _find_available_worker(self) -> Optional[WorkerInfo]:
        """Find an available worker."""
        with self._lock:
            for worker_info in self._workers.values():
                if worker_info.status == WorkerStatus.IDLE:
                    return worker_info
        return None
    
    def _update_worker_after_job_completion(self, job_id: str, success: bool) -> None:
        """Update worker status after job completion."""
        with self._lock:
            for worker_info in self._workers.values():
                if worker_info.current_job_id == job_id:
                    worker_info.status = WorkerStatus.IDLE
                    worker_info.current_job_id = None
                    worker_info.last_heartbeat = datetime.now(timezone.utc)
                    
                    if success:
                        worker_info.completed_jobs += 1
                    else:
                        worker_info.failed_jobs += 1
                    
                    break
    
    def _monitor_workers(self) -> None:
        """Monitor worker health and status."""
        while not self._shutdown_event.is_set():
            try:
                # Check for completed jobs
                completed_jobs = []
                for job_id, future in self._running_jobs.items():
                    if future.done():
                        completed_jobs.append(job_id)
                
                # Process completed jobs
                for job_id in completed_jobs:
                    future = self._running_jobs[job_id]
                    try:
                        result = future.result()
                        self._result_queue.put((job_id, result, None))
                    except Exception as e:
                        self._result_queue.put((job_id, None, str(e)))
                    
                    del self._running_jobs[job_id]
                    self._update_worker_after_job_completion(job_id, success=result is not None)
                
                # Update heartbeats for active workers
                with self._lock:
                    for worker_info in self._workers.values():
                        if worker_info.status in [WorkerStatus.IDLE, WorkerStatus.BUSY]:
                            worker_info.last_heartbeat = datetime.now(timezone.utc)
                
                time.sleep(1)  # Monitor every second
            
            except Exception as e:
                self.logger.error(f"Error in worker monitor: {e}")
                time.sleep(5)  # Wait longer on error
    
    @staticmethod
    def _execute_job(packet: IOptimizerNodePacket) -> OptimizationResult:
        """
        Execute a job in a worker process.
        This is the function that runs in the subprocess.
        """
        try:
            # This is a simplified implementation
            # In a real implementation, this would:
            # 1. Load the algorithm
            # 2. Configure it with the parameters from the packet
            # 3. Run the backtest
            # 4. Extract and return the results
            
            # For now, we'll create a mock result
            from ..optimizer.result_management import OptimizationResult, PerformanceMetrics
            
            # Simulate some work
            time.sleep(1)
            
            # Create mock performance metrics
            metrics = PerformanceMetrics(
                total_return=0.15,
                sharpe_ratio=1.2,
                max_drawdown=0.08,
                win_rate=0.55,
                profit_loss_ratio=1.8,
                total_trades=100,
                winning_trades=55,
                losing_trades=45
            )
            
            # Create optimization result
            result = OptimizationResult(
                parameter_set=packet.parameter_set,
                performance_metrics=metrics,
                fitness_score=metrics.sharpe_ratio,
                execution_time=1.0,
                timestamp=datetime.now(timezone.utc),
                success=True
            )
            
            return result
        
        except Exception as e:
            # Return failed result
            from ..optimizer.result_management import OptimizationResult, PerformanceMetrics
            
            metrics = PerformanceMetrics()  # Empty metrics for failed runs
            result = OptimizationResult(
                parameter_set=packet.parameter_set,
                performance_metrics=metrics,
                fitness_score=float('-inf'),
                execution_time=0.0,
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_message=str(e)
            )
            
            return result


class DockerWorkerManager(IWorkerManager):
    """
    Worker manager for Docker-based execution.
    Manages Docker containers as worker nodes.
    """
    
    def __init__(self, 
                 docker_image: str,
                 max_workers: int = 4,
                 logger: Optional[logging.Logger] = None):
        self.docker_image = docker_image
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        
        self._containers: Dict[str, Dict[str, Any]] = {}
        self._workers: Dict[str, WorkerInfo] = {}
        self._running_jobs: Dict[str, str] = {}  # job_id -> container_id
        self._lock = threading.Lock()
    
    async def start_workers(self, count: int) -> bool:
        """Start Docker container workers."""
        try:
            worker_count = min(count, self.max_workers)
            
            for i in range(worker_count):
                worker_id = f"docker-worker-{i}-{uuid.uuid4().hex[:8]}"
                container_name = f"optimizer-worker-{worker_id}"
                
                # Start Docker container
                cmd = [
                    "docker", "run", "-d",
                    "--name", container_name,
                    "--rm",  # Remove container when it stops
                    self.docker_image
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise WorkerManagementException(f"Failed to start container: {result.stderr}")
                
                container_id = result.stdout.strip()
                
                # Store container info
                self._containers[worker_id] = {
                    'container_id': container_id,
                    'container_name': container_name
                }
                
                # Create worker info
                worker_info = WorkerInfo(
                    worker_id=worker_id,
                    status=WorkerStatus.IDLE,
                    created_time=datetime.now(timezone.utc),
                    last_heartbeat=datetime.now(timezone.utc)
                )
                self._workers[worker_id] = worker_info
            
            self.logger.info(f"Started {worker_count} Docker workers")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to start Docker workers: {e}")
            raise WorkerManagementException(f"Failed to start Docker workers: {e}")
    
    async def stop_workers(self) -> bool:
        """Stop all Docker container workers."""
        try:
            for worker_id, container_info in self._containers.items():
                container_id = container_info['container_id']
                
                # Stop container
                cmd = ["docker", "stop", container_id]
                subprocess.run(cmd, capture_output=True)
                
                # Update worker status
                if worker_id in self._workers:
                    self._workers[worker_id].status = WorkerStatus.DISCONNECTED
            
            self._containers.clear()
            self.logger.info("Stopped all Docker workers")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to stop Docker workers: {e}")
            return False
    
    async def submit_job(self, packet: IOptimizerNodePacket) -> str:
        """Submit job to Docker worker."""
        # This would implement Docker-specific job submission
        # For now, return the job ID
        return packet.job_id
    
    async def get_job_result(self, job_id: str) -> Optional[OptimizationResult]:
        """Get job result from Docker worker."""
        # This would implement Docker-specific result retrieval
        return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel job in Docker worker."""
        # This would implement Docker-specific job cancellation
        return False
    
    def get_worker_count(self) -> int:
        """Get total number of workers."""
        return len(self._workers)
    
    def get_active_workers(self) -> int:
        """Get number of active workers."""
        with self._lock:
            return sum(1 for w in self._workers.values() 
                      if w.status in [WorkerStatus.IDLE, WorkerStatus.BUSY])
    
    def get_worker_status(self) -> Dict[str, WorkerStatus]:
        """Get status of all workers."""
        with self._lock:
            return {worker_id: info.status for worker_id, info in self._workers.items()}


class WorkerManagerFactory:
    """Factory for creating worker managers."""
    
    @staticmethod
    def create_local_manager(max_workers: int = None,
                           logger: Optional[logging.Logger] = None) -> LocalWorkerManager:
        """Create local worker manager."""
        return LocalWorkerManager(max_workers=max_workers, logger=logger)
    
    @staticmethod
    def create_docker_manager(docker_image: str,
                            max_workers: int = 4,
                            logger: Optional[logging.Logger] = None) -> DockerWorkerManager:
        """Create Docker worker manager."""
        return DockerWorkerManager(
            docker_image=docker_image,
            max_workers=max_workers,
            logger=logger
        )