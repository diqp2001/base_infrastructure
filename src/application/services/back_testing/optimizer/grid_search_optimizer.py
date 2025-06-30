"""
Grid Search Optimizer implementation.
Provides exhaustive parameter space exploration through systematic combination testing.
"""

import asyncio
import logging
from typing import Optional, List, Iterator, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from .interfaces import IOptimizer, IOptimizationTarget
from .parameter_management import OptimizationParameterSet, ParameterSpace
from .result_management import OptimizationResult, OptimizationStatistics
from .configuration import OptimizerConfiguration
from .enums import OptimizationStatus


@dataclass
class GridSearchProgress:
    """Progress tracking for grid search optimization."""
    total_combinations: int
    completed_combinations: int
    current_combination: Optional[OptimizationParameterSet] = None
    estimated_time_remaining: Optional[float] = None
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0.0 to 1.0)."""
        if self.total_combinations == 0:
            return 1.0
        return self.completed_combinations / self.total_combinations
    
    def get_remaining_combinations(self) -> int:
        """Get number of remaining combinations."""
        return max(0, self.total_combinations - self.completed_combinations)


class GridSearchOptimizer(IOptimizer):
    """
    Grid Search optimizer implementation.
    Systematically evaluates all possible parameter combinations.
    """
    
    def __init__(self, 
                 parameter_space: ParameterSpace,
                 target_function: IOptimizationTarget,
                 configuration: Optional[OptimizerConfiguration] = None):
        self.parameter_space = parameter_space
        self.target_function = target_function
        self.configuration = configuration or OptimizerConfiguration()
        
        # Grid search state
        self.parameter_combinations: Optional[Iterator[OptimizationParameterSet]] = None
        self.current_combination: Optional[OptimizationParameterSet] = None
        self.total_combinations: Optional[int] = None
        self.completed_combinations = 0
        
        # Optimization state
        self.is_running = False
        self.is_stopped = False
        self.best_result: Optional[OptimizationResult] = None
        self.all_results: List[OptimizationResult] = []
        
        # Progress tracking
        self.progress = GridSearchProgress(0, 0)
        
        # Statistics
        self.statistics = OptimizationStatistics(
            optimization_id=self.configuration.optimization_id,
            start_time=datetime.now()
        )
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, configuration: OptimizerConfiguration) -> None:
        """Initialize the optimizer with configuration settings."""
        self.configuration = configuration
        
        # Calculate total combinations
        self.total_combinations = self.parameter_space.get_total_combinations()
        
        if self.total_combinations is None:
            raise ValueError("Grid search requires discrete parameter space with finite combinations")
        
        # Apply maximum combinations limit if configured
        if (self.configuration.grid_search_max_combinations and 
            self.total_combinations > self.configuration.grid_search_max_combinations):
            self.logger.warning(
                f"Total combinations ({self.total_combinations}) exceeds maximum "
                f"({self.configuration.grid_search_max_combinations}). "
                f"Grid search will be limited."
            )
            self.total_combinations = self.configuration.grid_search_max_combinations
        
        # Initialize progress tracking
        self.progress = GridSearchProgress(
            total_combinations=self.total_combinations,
            completed_combinations=0
        )
        
        # Generate parameter combinations
        self.parameter_combinations = self.parameter_space.generate_grid_combinations()
        
        # Reset state
        self.completed_combinations = 0
        self.is_running = False
        self.is_stopped = False
        self.best_result = None
        self.all_results = []
        
        self.logger.info(f"Grid search optimizer initialized with {self.total_combinations} combinations")
    
    async def optimize(self) -> OptimizationStatistics:
        """Run the grid search optimization process."""
        if self.parameter_combinations is None:
            self.initialize(self.configuration)
        
        self.is_running = True
        self.statistics.start_time = datetime.now()
        
        try:
            # Create semaphore for concurrent evaluation
            semaphore = asyncio.Semaphore(self.configuration.max_concurrent_backtests)
            
            # Process parameter combinations in batches
            batch_size = self.configuration.max_concurrent_backtests
            batch = []
            
            for combination in self.parameter_combinations:
                if self.is_stopped:
                    break
                
                # Check iteration limit
                if (self.configuration.max_iterations > 0 and 
                    self.completed_combinations >= self.configuration.max_iterations):
                    break
                
                # Check time limit
                if self.configuration.max_execution_time:
                    elapsed_time = datetime.now() - self.statistics.start_time
                    if elapsed_time >= self.configuration.max_execution_time:
                        self.logger.info("Maximum execution time reached")
                        break
                
                batch.append(combination)
                
                # Process batch when full or at end
                if len(batch) >= batch_size:
                    await self._process_batch(batch, semaphore)
                    batch = []
                    
                    # Report progress
                    if self.completed_combinations % self.configuration.progress_reporting_interval == 0:
                        self._report_progress()
            
            # Process remaining combinations in batch
            if batch and not self.is_stopped:
                await self._process_batch(batch, semaphore)
            
            # Finalize statistics
            self.statistics.end_time = datetime.now()
            self.statistics.total_runs_requested = self.total_combinations
            self.statistics.update_with_results(self.all_results)
            
            self.logger.info(
                f"Grid search completed. Evaluated {self.completed_combinations} combinations. "
                f"Best fitness: {self.best_result.fitness if self.best_result else 'N/A'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error during grid search optimization: {e}")
            raise
        finally:
            self.is_running = False
        
        return self.statistics
    
    async def _process_batch(self, batch: List[OptimizationParameterSet], semaphore: asyncio.Semaphore) -> None:
        """Process a batch of parameter combinations concurrently."""
        async def evaluate_combination(param_set: OptimizationParameterSet) -> None:
            async with semaphore:
                try:
                    self.current_combination = param_set
                    self.progress.current_combination = param_set
                    
                    # Validate parameters
                    if not self.target_function.validate_parameters(param_set):
                        self.logger.warning(f"Invalid parameter set: {param_set.unique_id}")
                        return
                    
                    # Evaluate parameter set
                    result = await self.target_function.evaluate(param_set)
                    
                    # Store result
                    self.all_results.append(result)
                    self.completed_combinations += 1
                    self.progress.completed_combinations = self.completed_combinations
                    
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
                    self.completed_combinations += 1
                    self.progress.completed_combinations = self.completed_combinations
        
        # Evaluate all combinations in batch concurrently
        tasks = [evaluate_combination(param_set) for param_set in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _report_progress(self) -> None:
        """Report optimization progress."""
        progress_percentage = self.progress.get_progress_percentage() * 100
        remaining_combinations = self.progress.get_remaining_combinations()
        
        # Estimate time remaining
        if self.completed_combinations > 0:
            elapsed_time = datetime.now() - self.statistics.start_time
            avg_time_per_combination = elapsed_time.total_seconds() / self.completed_combinations
            estimated_remaining_time = avg_time_per_combination * remaining_combinations
            self.progress.estimated_time_remaining = estimated_remaining_time
        
        self.logger.info(
            f"Grid search progress: {self.completed_combinations}/{self.total_combinations} "
            f"({progress_percentage:.1f}%) - "
            f"Best fitness: {self.best_result.fitness if self.best_result else 'N/A'}"
        )
        
        if self.progress.estimated_time_remaining:
            hours, remainder = divmod(self.progress.estimated_time_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.logger.info(f"Estimated time remaining: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
    
    def get_next_parameter_set(self) -> Optional[OptimizationParameterSet]:
        """Get the next parameter set to evaluate."""
        if self.parameter_combinations is None:
            return None
        
        try:
            return next(self.parameter_combinations)
        except StopIteration:
            return None
    
    def register_result(self, result: OptimizationResult) -> None:
        """Register the result of evaluating a parameter set."""
        self.all_results.append(result)
        self.completed_combinations += 1
        self.progress.completed_combinations = self.completed_combinations
        
        # Update best result
        if result.is_successful():
            if self.best_result is None or result.fitness > self.best_result.fitness:
                self.best_result = result
    
    def is_complete(self) -> bool:
        """Check if the optimization process is complete."""
        if self.is_stopped:
            return True
        
        if self.total_combinations and self.completed_combinations >= self.total_combinations:
            return True
        
        if (self.configuration.max_iterations > 0 and 
            self.completed_combinations >= self.configuration.max_iterations):
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
        self.logger.info("Grid search optimization stopped")
    
    def get_grid_summary(self) -> Dict[str, Any]:
        """Get summary of grid search configuration and progress."""
        return {
            'total_combinations': self.total_combinations,
            'completed_combinations': self.completed_combinations,
            'remaining_combinations': self.progress.get_remaining_combinations(),
            'progress_percentage': self.progress.get_progress_percentage() * 100,
            'estimated_time_remaining': self.progress.estimated_time_remaining,
            'best_fitness': self.best_result.fitness if self.best_result else None,
            'best_parameters': self.best_result.parameter_set.parameters if self.best_result else None,
            'is_complete': self.is_complete(),
            'is_running': self.is_running
        }
    
    def get_parameter_analysis(self) -> Dict[str, Any]:
        """Analyze parameter space and provide insights."""
        if not self.all_results:
            return {}
        
        analysis = {}
        
        # Parameter importance analysis
        parameter_names = self.parameter_space.get_parameter_names()
        
        for param_name in parameter_names:
            param_values = []
            fitness_values = []
            
            for result in self.all_results:
                if result.is_successful():
                    param_value = result.parameter_set.get_parameter_value(param_name)
                    if param_value is not None:
                        param_values.append(param_value)
                        fitness_values.append(result.fitness)
            
            if len(param_values) > 1:
                # Calculate correlation between parameter and fitness
                try:
                    import numpy as np
                    correlation = np.corrcoef(param_values, fitness_values)[0, 1]
                    analysis[param_name] = {
                        'correlation_with_fitness': correlation,
                        'best_value': self.best_result.parameter_set.get_parameter_value(param_name) if self.best_result else None,
                        'value_range': (min(param_values), max(param_values)),
                        'sample_count': len(param_values)
                    }
                except Exception as e:
                    self.logger.warning(f"Could not calculate correlation for parameter {param_name}: {e}")
        
        return analysis
    
    def export_results(self, file_path: str, format: str = 'csv') -> None:
        """Export optimization results to file."""
        if not self.all_results:
            self.logger.warning("No results to export")
            return
        
        try:
            if format.lower() == 'csv':
                import pandas as pd
                
                # Prepare data for export
                export_data = []
                for result in self.all_results:
                    row = result.parameter_set.parameters.copy()
                    row['fitness'] = result.fitness
                    row['execution_time'] = result.execution_time
                    row['status'] = result.status.value
                    row['backtest_id'] = result.backtest_id
                    export_data.append(row)
                
                df = pd.DataFrame(export_data)
                df.to_csv(file_path, index=False)
                self.logger.info(f"Results exported to {file_path}")
            
            elif format.lower() == 'json':
                import json
                
                export_data = [result.to_dict() for result in self.all_results]
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                self.logger.info(f"Results exported to {file_path}")
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            raise
    
    def __repr__(self) -> str:
        """String representation of the grid search optimizer."""
        return (f"GridSearchOptimizer(total_combinations={self.total_combinations}, "
                f"completed={self.completed_combinations}, "
                f"progress={self.progress.get_progress_percentage()*100:.1f}%, "
                f"best_fitness={self.best_result.fitness if self.best_result else 'N/A'})")