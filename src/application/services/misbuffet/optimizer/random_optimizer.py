"""
Random Search Optimizer implementation.
Provides random sampling optimization through statistical parameter space exploration.
"""

import asyncio
import logging
import random
import numpy as np
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from dataclasses import dataclass

from .interfaces import IOptimizer, IOptimizationTarget
from .parameter_management import OptimizationParameterSet, ParameterSpace
from .result_management import OptimizationResult, OptimizationStatistics
from .configuration import OptimizerConfiguration
from .enums import OptimizationStatus


@dataclass
class RandomSearchProgress:
    """Progress tracking for random search optimization."""
    total_samples_planned: int
    completed_samples: int
    current_sample: Optional[OptimizationParameterSet] = None
    unique_samples_generated: int = 0
    duplicate_samples_rejected: int = 0
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0.0 to 1.0)."""
        if self.total_samples_planned == 0:
            return 1.0
        return self.completed_samples / self.total_samples_planned
    
    def get_remaining_samples(self) -> int:
        """Get number of remaining samples."""
        return max(0, self.total_samples_planned - self.completed_samples)
    
    def get_efficiency(self) -> float:
        """Get sampling efficiency (unique samples / total generated)."""
        total_generated = self.unique_samples_generated + self.duplicate_samples_rejected
        if total_generated == 0:
            return 1.0
        return self.unique_samples_generated / total_generated


class RandomOptimizer(IOptimizer):
    """
    Random Search optimizer implementation.
    Uses statistical sampling to explore the parameter space efficiently.
    """
    
    def __init__(self, 
                 parameter_space: ParameterSpace,
                 target_function: IOptimizationTarget,
                 configuration: Optional[OptimizerConfiguration] = None):
        self.parameter_space = parameter_space
        self.target_function = target_function
        self.configuration = configuration or OptimizerConfiguration()
        
        # Random search state
        self.total_samples = self.configuration.random_search_samples
        self.completed_samples = 0
        self.generated_parameter_sets: Set[str] = set()  # Track unique parameter sets
        
        # Optimization state
        self.is_running = False
        self.is_stopped = False
        self.best_result: Optional[OptimizationResult] = None
        self.all_results: List[OptimizationResult] = []
        
        # Progress tracking
        self.progress = RandomSearchProgress(self.total_samples, 0)
        
        # Statistics
        self.statistics = OptimizationStatistics(
            optimization_id=self.configuration.optimization_id,
            start_time=datetime.now()
        )
        
        # Random number generator
        self.rng = random.Random(self.configuration.random_search_seed)
        np.random.seed(self.configuration.random_search_seed)
        
        # Adaptive sampling parameters
        self.adaptive_sampling = True
        self.exploration_rate = 1.0  # Start with full exploration
        self.exploitation_threshold = 0.3  # Switch to exploitation after 30% completion
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, configuration: OptimizerConfiguration) -> None:
        """Initialize the optimizer with configuration settings."""
        self.configuration = configuration
        
        # Update sampling parameters
        self.total_samples = self.configuration.random_search_samples
        self.progress = RandomSearchProgress(self.total_samples, 0)
        
        # Reset random number generator
        if self.configuration.random_search_seed is not None:
            self.rng = random.Random(self.configuration.random_search_seed)
            np.random.seed(self.configuration.random_search_seed)
        
        # Reset state
        self.completed_samples = 0
        self.generated_parameter_sets.clear()
        self.is_running = False
        self.is_stopped = False
        self.best_result = None
        self.all_results = []
        
        self.logger.info(f"Random search optimizer initialized with {self.total_samples} samples")
    
    async def optimize(self) -> OptimizationStatistics:
        """Run the random search optimization process."""
        if self.total_samples <= 0:
            raise ValueError("Total samples must be positive")
        
        self.is_running = True
        self.statistics.start_time = datetime.now()
        
        try:
            # Create semaphore for concurrent evaluation
            semaphore = asyncio.Semaphore(self.configuration.max_concurrent_backtests)
            
            # Generate and evaluate parameter sets
            await self._run_random_sampling(semaphore)
            
            # Finalize statistics
            self.statistics.end_time = datetime.now()
            self.statistics.total_runs_requested = self.total_samples
            self.statistics.update_with_results(self.all_results)
            
            self.logger.info(
                f"Random search completed. Evaluated {self.completed_samples} samples. "
                f"Sampling efficiency: {self.progress.get_efficiency():.2%}. "
                f"Best fitness: {self.best_result.fitness if self.best_result else 'N/A'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error during random search optimization: {e}")
            raise
        finally:
            self.is_running = False
        
        return self.statistics
    
    async def _run_random_sampling(self, semaphore: asyncio.Semaphore) -> None:
        """Run the main random sampling loop."""
        batch_size = self.configuration.max_concurrent_backtests
        batch = []
        max_generation_attempts = self.total_samples * 10  # Prevent infinite loops
        generation_attempts = 0
        
        while (self.completed_samples < self.total_samples and 
               not self.is_stopped and 
               generation_attempts < max_generation_attempts):
            
            # Check time limit
            if self.configuration.max_execution_time:
                elapsed_time = datetime.now() - self.statistics.start_time
                if elapsed_time >= self.configuration.max_execution_time:
                    self.logger.info("Maximum execution time reached")
                    break
            
            # Generate parameter set
            param_set = self._generate_parameter_set()
            generation_attempts += 1
            
            if param_set is None:
                continue  # Skip if we couldn't generate a unique parameter set
            
            batch.append(param_set)
            
            # Process batch when full
            if len(batch) >= batch_size:
                await self._process_batch(batch, semaphore)
                batch = []
                
                # Report progress
                if self.completed_samples % self.configuration.progress_reporting_interval == 0:
                    self._report_progress()
                
                # Update exploration/exploitation balance
                self._update_sampling_strategy()
        
        # Process remaining samples in batch
        if batch and not self.is_stopped:
            await self._process_batch(batch, semaphore)
    
    def _generate_parameter_set(self) -> Optional[OptimizationParameterSet]:
        """Generate a parameter set using current sampling strategy."""
        max_attempts = 100  # Maximum attempts to generate unique parameter set
        
        for _ in range(max_attempts):
            if self.adaptive_sampling and self._should_exploit():
                param_set = self._generate_exploitation_sample()
            else:
                param_set = self._generate_exploration_sample()
            
            # Check for uniqueness
            param_hash = self._hash_parameter_set(param_set)
            if param_hash not in self.generated_parameter_sets:
                self.generated_parameter_sets.add(param_hash)
                self.progress.unique_samples_generated += 1
                return param_set
            else:
                self.progress.duplicate_samples_rejected += 1
        
        # If we can't generate a unique parameter set, return None
        self.logger.warning("Could not generate unique parameter set after maximum attempts")
        return None
    
    def _generate_exploration_sample(self) -> OptimizationParameterSet:
        """Generate a random parameter set for exploration."""
        return self.parameter_space.generate_random_parameter_set()
    
    def _generate_exploitation_sample(self) -> OptimizationParameterSet:
        """Generate a parameter set for exploitation around best results."""
        if not self.best_result:
            return self._generate_exploration_sample()
        
        # Sample around the best result with some noise
        best_params = self.best_result.parameter_set.parameters
        new_params = {}
        
        for param in self.parameter_space.get_all_parameters():
            param_name = param.name
            best_value = best_params.get(param_name)
            
            if best_value is None:
                # Parameter not in best result, use random value
                new_params[param_name] = param.generate_random_value()
                continue
            
            # Add noise to best value
            if param.parameter_type.value in ['integer', 'float']:
                # Calculate noise based on parameter range
                param_range = param.max_value - param.min_value
                noise_std = param_range * 0.1  # 10% of range
                
                if param.parameter_type.value == 'integer':
                    noise = int(self.rng.gauss(0, noise_std))
                    new_value = best_value + noise
                    new_params[param_name] = param.clip_value(new_value)
                else:
                    noise = self.rng.gauss(0, noise_std)
                    new_value = best_value + noise
                    new_params[param_name] = param.clip_value(new_value)
            else:
                # For categorical/boolean parameters, occasionally randomize
                if self.rng.random() < 0.3:  # 30% chance to randomize
                    new_params[param_name] = param.generate_random_value()
                else:
                    new_params[param_name] = best_value
        
        return OptimizationParameterSet(parameters=new_params)
    
    def _should_exploit(self) -> bool:
        """Determine if we should exploit vs explore."""
        progress = self.progress.get_progress_percentage()
        return progress > self.exploitation_threshold and self.best_result is not None
    
    def _update_sampling_strategy(self) -> None:
        """Update sampling strategy based on progress."""
        progress = self.progress.get_progress_percentage()
        
        # Gradually shift from exploration to exploitation
        if progress > self.exploitation_threshold:
            # Reduce exploration rate as we progress
            self.exploration_rate = max(0.1, 1.0 - (progress - self.exploitation_threshold) / 0.7)
        else:
            self.exploration_rate = 1.0
    
    def _hash_parameter_set(self, param_set: OptimizationParameterSet) -> str:
        """Create a hash string for parameter set to check uniqueness."""
        import hashlib
        import json
        
        # Sort parameters to ensure consistent hashing
        sorted_params = sorted(param_set.parameters.items())
        param_string = json.dumps(sorted_params, sort_keys=True, default=str)
        return hashlib.md5(param_string.encode()).hexdigest()
    
    async def _process_batch(self, batch: List[OptimizationParameterSet], semaphore: asyncio.Semaphore) -> None:
        """Process a batch of parameter sets concurrently."""
        async def evaluate_parameter_set(param_set: OptimizationParameterSet) -> None:
            async with semaphore:
                try:
                    self.progress.current_sample = param_set
                    
                    # Validate parameters
                    if not self.target_function.validate_parameters(param_set):
                        self.logger.warning(f"Invalid parameter set: {param_set.unique_id}")
                        return
                    
                    # Evaluate parameter set
                    result = await self.target_function.evaluate(param_set)
                    
                    # Store result
                    self.all_results.append(result)
                    self.completed_samples += 1
                    self.progress.completed_samples = self.completed_samples
                    
                    # Update best result
                    if result.is_successful():
                        if self.best_result is None or result.fitness > self.best_result.fitness:
                            self.best_result = result
                            self.logger.info(f"New best result: {result.fitness} with parameters {param_set.parameters}")
                    
                    # Check if target fitness reached
                    if (self.configuration.target_fitness is not None and 
                        result.fitness >= self.configuration.target_fitness):
                        self.logger.info(f"Target fitness {self.configuration.target_fitness} reached")
                        self.stop()
                    
                except Exception as e:
                    self.logger.error(f"Error evaluating parameter set {param_set.unique_id}: {e}")
                    self.completed_samples += 1
                    self.progress.completed_samples = self.completed_samples
        
        # Evaluate all parameter sets in batch concurrently
        tasks = [evaluate_parameter_set(param_set) for param_set in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _report_progress(self) -> None:
        """Report optimization progress."""
        progress_percentage = self.progress.get_progress_percentage() * 100
        remaining_samples = self.progress.get_remaining_samples()
        efficiency = self.progress.get_efficiency()
        
        # Estimate time remaining
        estimated_remaining_time = None
        if self.completed_samples > 0:
            elapsed_time = datetime.now() - self.statistics.start_time
            avg_time_per_sample = elapsed_time.total_seconds() / self.completed_samples
            estimated_remaining_time = avg_time_per_sample * remaining_samples
        
        self.logger.info(
            f"Random search progress: {self.completed_samples}/{self.total_samples} "
            f"({progress_percentage:.1f}%) - "
            f"Efficiency: {efficiency:.1%} - "
            f"Exploration rate: {self.exploration_rate:.1%} - "
            f"Best fitness: {self.best_result.fitness if self.best_result else 'N/A'}"
        )
        
        if estimated_remaining_time:
            hours, remainder = divmod(estimated_remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.logger.info(f"Estimated time remaining: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
    
    def get_next_parameter_set(self) -> Optional[OptimizationParameterSet]:
        """Get the next parameter set to evaluate."""
        if self.completed_samples >= self.total_samples or self.is_stopped:
            return None
        
        return self._generate_parameter_set()
    
    def register_result(self, result: OptimizationResult) -> None:
        """Register the result of evaluating a parameter set."""
        self.all_results.append(result)
        self.completed_samples += 1
        self.progress.completed_samples = self.completed_samples
        
        # Update best result
        if result.is_successful():
            if self.best_result is None or result.fitness > self.best_result.fitness:
                self.best_result = result
    
    def is_complete(self) -> bool:
        """Check if the optimization process is complete."""
        if self.is_stopped:
            return True
        
        if self.completed_samples >= self.total_samples:
            return True
        
        if self.configuration.max_execution_time:
            elapsed_time = datetime.now() - self.statistics.start_time
            if elapsed_time >= self.configuration.max_execution_time:
                return True
        
        return False
    
    def get_best_result(self) -> Optional[OptimizationResult]:
        """Get the best result found so far."""
        return self.best_result
    
    def get_progress(self) -> float:
        """Get optimization progress as a percentage (0.0 to 1.0)."""
        return self.progress.get_progress_percentage()
    
    def stop(self) -> None:
        """Stop the optimization process."""
        self.is_stopped = True
        self.logger.info("Random search optimization stopped")
    
    def get_sampling_statistics(self) -> Dict[str, Any]:
        """Get detailed sampling statistics."""
        return {
            'total_samples_planned': self.total_samples,
            'completed_samples': self.completed_samples,
            'remaining_samples': self.progress.get_remaining_samples(),
            'progress_percentage': self.progress.get_progress_percentage() * 100,
            'unique_samples_generated': self.progress.unique_samples_generated,
            'duplicate_samples_rejected': self.progress.duplicate_samples_rejected,
            'sampling_efficiency': self.progress.get_efficiency(),
            'exploration_rate': self.exploration_rate,
            'best_fitness': self.best_result.fitness if self.best_result else None,
            'is_complete': self.is_complete(),
            'is_running': self.is_running
        }
    
    def get_convergence_analysis(self) -> Dict[str, Any]:
        """Analyze convergence patterns in random search."""
        if len(self.all_results) < 10:
            return {'error': 'Insufficient data for convergence analysis'}
        
        # Sort results by evaluation order
        sorted_results = sorted(self.all_results, key=lambda r: r.start_time)
        
        # Calculate improvement over time
        best_fitness_over_time = []
        current_best = float('-inf')
        
        for result in sorted_results:
            if result.is_successful() and result.fitness > current_best:
                current_best = result.fitness
            best_fitness_over_time.append(current_best)
        
        # Calculate improvement rate
        improvements = sum(1 for i in range(1, len(best_fitness_over_time)) 
                          if best_fitness_over_time[i] > best_fitness_over_time[i-1])
        
        improvement_rate = improvements / len(best_fitness_over_time) if best_fitness_over_time else 0
        
        # Calculate convergence metrics
        final_fitness = best_fitness_over_time[-1] if best_fitness_over_time else 0
        initial_fitness = best_fitness_over_time[0] if best_fitness_over_time else 0
        
        return {
            'improvement_rate': improvement_rate,
            'total_improvements': improvements,
            'fitness_improvement': final_fitness - initial_fitness,
            'convergence_ratio': final_fitness / initial_fitness if initial_fitness != 0 else float('inf'),
            'stagnation_period': len(best_fitness_over_time) - improvements,
            'best_fitness_timeline': best_fitness_over_time
        }
    
    def __repr__(self) -> str:
        """String representation of the random optimizer."""
        return (f"RandomOptimizer(total_samples={self.total_samples}, "
                f"completed={self.completed_samples}, "
                f"progress={self.progress.get_progress_percentage()*100:.1f}%, "
                f"efficiency={self.progress.get_efficiency():.1%}, "
                f"best_fitness={self.best_result.fitness if self.best_result else 'N/A'})")