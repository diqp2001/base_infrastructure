"""
QuantConnect Lean Optimizer.Launcher Main

Main orchestrator for distributed optimization campaigns that coordinates
optimizers, workers, and result collection across multiple execution nodes.
"""

import asyncio
import logging
import signal
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import json

from .interfaces import (
    IOptimizerLauncher,
    OptimizerLauncherStatus,
    OptimizerLauncherMode,
    OptimizerLauncherException,
    OptimizerLauncherConfiguration
)
from .configuration import OptimizerLauncherConfigurationManager
from .node_packet import OptimizerNodePacket, NodePacketFactory, AlgorithmConfiguration
from .worker_manager import WorkerManagerFactory, LocalWorkerManager, DockerWorkerManager
from .result_coordinator import ResultCoordinator, OptimizationCampaignResult, ProgressReporter

from ..optimizer.interfaces import IOptimizer, IOptimizerFactory
from ..optimizer.optimizer_factory import OptimizerFactory
from ..optimizer.parameter_management import ParameterSpace, OptimizationParameterSet
from ..optimizer.result_management import OptimizationResult
from ..optimizer.enums import OptimizationType
from ..launcher.interfaces import LauncherConfiguration
from ..common.enums import Resolution, SecurityType


class OptimizerLauncher(IOptimizerLauncher):
    """
    Main optimizer launcher that orchestrates distributed optimization campaigns.
    Combines optimization algorithms with distributed execution across worker nodes.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration and state
        self._config: Optional[OptimizerLauncherConfiguration] = None
        self._status = OptimizerLauncherStatus.INITIALIZING
        self._progress = 0.0
        
        # Core components
        self._optimizer: Optional[IOptimizer] = None
        self._worker_manager = None
        self._result_coordinator: Optional[ResultCoordinator] = None
        self._progress_reporter: Optional[ProgressReporter] = None
        
        # Execution tracking
        self._campaign_id: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._total_evaluations = 0
        self._completed_evaluations = 0
        self._active_jobs: Dict[str, OptimizerNodePacket] = {}
        self._shutdown_requested = False
        
        # Signal handling - only works in main thread
        try:
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                self.logger.debug("Signal handlers set up for main thread")
            else:
                self.logger.debug("Skipping signal handler setup - not in main thread")
        except Exception as e:
            self.logger.warning(f"Could not set up signal handlers: {e}")
            # Continue without signal handlers
    
    def initialize(self, config: OptimizerLauncherConfiguration) -> bool:
        """Initialize the optimizer launcher with given configuration."""
        try:
            self.logger.info("Initializing optimizer launcher")
            self._status = OptimizerLauncherStatus.LOADING_CONFIG
            
            # Validate configuration
            config_manager = OptimizerLauncherConfigurationManager(self.logger)
            validation_errors = config_manager.validate_configuration(config)
            if validation_errors:
                raise OptimizerLauncherException(f"Configuration validation failed: {validation_errors}")
            
            self._config = config
            self._campaign_id = f"campaign_{int(time.time())}"
            
            # Initialize result coordinator
            self._result_coordinator = ResultCoordinator(
                campaign_id=self._campaign_id,
                output_folder=config.output_folder,
                logger=self.logger
            )
            
            # Initialize progress reporter
            self._progress_reporter = ProgressReporter(self.logger)
            self._result_coordinator.add_progress_reporter(self._progress_reporter)
            
            # Initialize worker manager
            self._status = OptimizerLauncherStatus.STARTING_WORKERS
            self._worker_manager = self._create_worker_manager()
            
            # Initialize optimizer
            self._optimizer = self._create_optimizer()
            
            self.logger.info(f"Optimizer launcher initialized for campaign {self._campaign_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize optimizer launcher: {e}")
            self._status = OptimizerLauncherStatus.FAILED
            return False
    
    async def run_optimization(self) -> OptimizationCampaignResult:
        """Run the optimization campaign."""
        try:
            if not self._config or not self._optimizer or not self._worker_manager:
                raise OptimizerLauncherException("Optimizer launcher not properly initialized")
            
            self._status = OptimizerLauncherStatus.OPTIMIZING
            self._start_time = datetime.now(timezone.utc)
            
            self.logger.info(f"Starting optimization campaign {self._campaign_id}")
            self._progress_reporter.report_campaign_start(self._config)
            
            # Start workers
            await self._worker_manager.start_workers(self._config.max_concurrent_backtests)
            
            # Estimate total evaluations
            self._total_evaluations = self._estimate_total_evaluations()
            
            # Main optimization loop
            await self._run_optimization_loop()
            
            # Finalize results
            self._status = OptimizerLauncherStatus.FINALIZING
            await self._finalize_optimization()
            
            self._status = OptimizerLauncherStatus.COMPLETED
            campaign_result = self._result_coordinator.get_campaign_result()
            
            self.logger.info(f"Optimization campaign {self._campaign_id} completed successfully")
            return campaign_result
        
        except Exception as e:
            self.logger.error(f"Optimization campaign failed: {e}")
            self._status = OptimizerLauncherStatus.FAILED
            raise OptimizerLauncherException(f"Optimization campaign failed: {e}")
        
        finally:
            # Cleanup
            await self._cleanup()
    
    def stop_optimization(self) -> bool:
        """Stop the optimization campaign gracefully."""
        try:
            self.logger.info("Stopping optimization campaign")
            self._shutdown_requested = True
            self._status = OptimizerLauncherStatus.CANCELLED
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop optimization: {e}")
            return False
    
    @property
    def status(self) -> OptimizerLauncherStatus:
        """Gets the current launcher status."""
        return self._status
    
    @property
    def progress(self) -> float:
        """Gets the optimization progress (0.0 to 1.0)."""
        if self._total_evaluations > 0:
            return min(1.0, self._completed_evaluations / self._total_evaluations)
        return self._progress
    
    async def get_live_results(self) -> List[OptimizationResult]:
        """Get current optimization results in real-time."""
        if self._result_coordinator:
            return await self._result_coordinator.get_all_results()
        return []
    
    async def _run_optimization_loop(self) -> None:
        """Main optimization execution loop."""
        
        # Submit initial batch of jobs
        await self._submit_initial_jobs()
        
        # Main loop
        while not self._shutdown_requested and not self._optimizer.is_complete():
            try:
                # Check for completed jobs and collect results
                await self._collect_completed_results()
                
                # Submit new jobs if workers are available
                await self._submit_new_jobs()
                
                # Update progress
                self._update_progress()
                
                # Brief pause to prevent busy waiting
                await asyncio.sleep(0.1)
            
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                if not self._config.fault_tolerance:
                    raise
                # Continue with fault tolerance
                await asyncio.sleep(1)
        
        # Wait for remaining jobs to complete
        await self._wait_for_remaining_jobs()
    
    async def _submit_initial_jobs(self) -> None:
        """Submit initial batch of optimization jobs."""
        active_workers = self._worker_manager.get_active_workers()
        initial_batch_size = min(active_workers * 2, 10)  # Submit 2x workers initially
        
        for _ in range(initial_batch_size):
            if self._shutdown_requested:
                break
            
            parameter_set = self._optimizer.get_next_parameter_set()
            if parameter_set is None:
                break
            
            await self._submit_job(parameter_set)
    
    async def _submit_new_jobs(self) -> None:
        """Submit new jobs to available workers."""
        active_workers = self._worker_manager.get_active_workers()
        current_jobs = len(self._active_jobs)
        
        # Submit jobs to fill available worker capacity
        while (current_jobs < active_workers and 
               not self._shutdown_requested and 
               not self._optimizer.is_complete()):
            
            parameter_set = self._optimizer.get_next_parameter_set()
            if parameter_set is None:
                break
            
            await self._submit_job(parameter_set)
            current_jobs += 1
    
    async def _submit_job(self, parameter_set: OptimizationParameterSet) -> None:
        """Submit a single optimization job."""
        try:
            # Create algorithm configuration
            algorithm_config = self._create_algorithm_configuration()
            
            # Create node packet
            packet = NodePacketFactory.create_packet(
                parameter_set=parameter_set,
                algorithm_config=algorithm_config,
                campaign_id=self._campaign_id
            )
            
            # Submit to worker manager
            job_id = await self._worker_manager.submit_job(packet)
            self._active_jobs[job_id] = packet
            
            self.logger.debug(f"Submitted job {job_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to submit job: {e}")
            if not self._config.fault_tolerance:
                raise
    
    async def _collect_completed_results(self) -> None:
        """Collect results from completed jobs."""
        completed_jobs = []
        
        for job_id, packet in self._active_jobs.items():
            try:
                result = await self._worker_manager.get_job_result(job_id)
                if result is not None:
                    # Register result with optimizer
                    self._optimizer.register_result(result)
                    
                    # Register result with coordinator
                    await self._result_coordinator.register_result(result)
                    
                    # Track completion
                    completed_jobs.append(job_id)
                    self._completed_evaluations += 1
                    
                    self.logger.debug(f"Collected result for job {job_id}: fitness={result.fitness_score}")
            
            except Exception as e:
                self.logger.error(f"Error collecting result for job {job_id}: {e}")
                completed_jobs.append(job_id)  # Remove failed job
        
        # Remove completed jobs
        for job_id in completed_jobs:
            del self._active_jobs[job_id]
    
    async def _wait_for_remaining_jobs(self) -> None:
        """Wait for all remaining jobs to complete."""
        self.logger.info(f"Waiting for {len(self._active_jobs)} remaining jobs to complete")
        
        max_wait_time = 300  # 5 minutes maximum wait
        start_wait = time.time()
        
        while self._active_jobs and (time.time() - start_wait) < max_wait_time:
            await self._collect_completed_results()
            
            if self._active_jobs:
                await asyncio.sleep(1)
        
        # Cancel any remaining jobs
        if self._active_jobs:
            self.logger.warning(f"Cancelling {len(self._active_jobs)} remaining jobs due to timeout")
            for job_id in list(self._active_jobs.keys()):
                await self._worker_manager.cancel_job(job_id)
            self._active_jobs.clear()
    
    def _update_progress(self) -> None:
        """Update optimization progress."""
        if self._total_evaluations > 0:
            self._progress = min(1.0, self._completed_evaluations / self._total_evaluations)
        else:
            self._progress = self._optimizer.get_progress()
        
        # Report progress periodically
        if self._completed_evaluations % 10 == 0:
            elapsed_time = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            best_result = self._optimizer.get_best_result()
            best_fitness = best_result.fitness_score if best_result else float('-inf')
            
            self._progress_reporter.report_progress_update(
                completed=self._completed_evaluations,
                total=self._total_evaluations,
                best_fitness=best_fitness,
                elapsed_time=elapsed_time
            )
    
    async def _finalize_optimization(self) -> None:
        """Finalize the optimization process."""
        # Complete the campaign
        self._result_coordinator.complete_campaign()
        
        # Export final results
        results_file = Path(self._config.output_folder) / self._config.results_file
        await self._result_coordinator.export_results(str(results_file), format="json")
        
        # Export CSV for analysis
        csv_file = results_file.with_suffix('.csv')
        await self._result_coordinator.export_results(str(csv_file), format="csv")
        
        self.logger.info(f"Results exported to {results_file} and {csv_file}")
    
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        try:
            if self._worker_manager:
                await self._worker_manager.stop_workers()
            
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _create_worker_manager(self):
        """Create appropriate worker manager based on configuration."""
        if self._config.mode == OptimizerLauncherMode.LOCAL:
            return WorkerManagerFactory.create_local_manager(
                max_workers=self._config.max_concurrent_backtests,
                logger=self.logger
            )
        elif self._config.mode == OptimizerLauncherMode.CLOUD:
            if self._config.worker_image:
                return WorkerManagerFactory.create_docker_manager(
                    docker_image=self._config.worker_image,
                    max_workers=self._config.max_concurrent_backtests,
                    logger=self.logger
                )
            else:
                # Fall back to local manager
                self.logger.warning("No worker image specified for cloud mode, using local manager")
                return WorkerManagerFactory.create_local_manager(
                    max_workers=self._config.max_concurrent_backtests,
                    logger=self.logger
                )
        else:
            # Default to local manager
            return WorkerManagerFactory.create_local_manager(
                max_workers=self._config.max_concurrent_backtests,
                logger=self.logger
            )
    
    def _create_optimizer(self):
        """Create optimizer instance based on configuration."""
        # Load parameter space from file
        parameter_space = self._load_parameter_space()
        
        # Create optimization target (simplified for now)
        optimization_target = self._create_optimization_target()
        
        # Create optimizer
        optimizer_factory = OptimizerFactory()
        optimization_type = OptimizationType.GENETIC  # Default, could be configurable
        
        return optimizer_factory.create_optimizer(
            optimization_type=optimization_type,
            parameter_space=parameter_space,
            target_function=optimization_target
        )
    
    def _load_parameter_space(self) -> ParameterSpace:
        """Load parameter space from configuration file."""
        try:
            with open(self._config.parameter_file, 'r') as f:
                param_data = json.load(f)
            
            parameter_space = ParameterSpace()
            
            # Create parameters from configuration
            # This is a simplified implementation
            for param_config in param_data.get('parameters', []):
                # In a real implementation, this would create proper OptimizationParameter objects
                pass
            
            return parameter_space
        
        except Exception as e:
            self.logger.error(f"Failed to load parameter space: {e}")
            # Return empty parameter space as fallback
            return ParameterSpace()
    
    def _create_optimization_target(self):
        """Create optimization target function."""
        # This would create a proper IOptimizationTarget implementation
        # For now, return None (would need to be implemented based on specific requirements)
        return None
    
    def _create_algorithm_configuration(self) -> AlgorithmConfiguration:
        """Create algorithm configuration for job packets."""
        return AlgorithmConfiguration(
            algorithm_type_name=self._config.algorithm_type_name,
            algorithm_location=self._config.algorithm_location,
            start_date="2020-01-01",  # Would be configurable
            end_date="2021-01-01",    # Would be configurable
            initial_cash=100000.0,
            data_folder=self._config.data_folder,
            resolution=Resolution.DAILY,
            security_types=[SecurityType.EQUITY]
        )
    
    def _estimate_total_evaluations(self) -> int:
        """Estimate total number of evaluations for progress tracking."""
        # This would depend on the optimization algorithm and parameter space
        # For now, return a reasonable estimate
        return 1000
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully")
        self._shutdown_requested = True


class OptimizerLauncherFactory:
    """Factory for creating optimizer launcher instances."""
    
    @staticmethod
    def create_launcher(mode: OptimizerLauncherMode = OptimizerLauncherMode.LOCAL,
                       logger: Optional[logging.Logger] = None) -> OptimizerLauncher:
        """Create optimizer launcher instance."""
        return OptimizerLauncher(logger=logger)
    
    @staticmethod
    def create_from_config_file(config_path: str,
                               logger: Optional[logging.Logger] = None) -> OptimizerLauncher:
        """Create optimizer launcher from configuration file."""
        config_manager = OptimizerLauncherConfigurationManager(logger)
        config = config_manager.load_from_file(config_path)
        
        launcher = OptimizerLauncher(logger=logger)
        launcher.initialize(config)
        
        return launcher
    
    @staticmethod
    def create_from_environment(logger: Optional[logging.Logger] = None) -> OptimizerLauncher:
        """Create optimizer launcher from environment variables."""
        config_manager = OptimizerLauncherConfigurationManager(logger)
        config = config_manager.load_from_environment()
        
        launcher = OptimizerLauncher(logger=logger)
        launcher.initialize(config)
        
        return launcher