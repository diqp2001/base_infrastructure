"""
Core interfaces for the Optimizer module.
Defines the contracts that optimizer components must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator, Callable
from datetime import datetime

from .enums import OptimizationType, OptimizationStatus


class IOptimizer(ABC):
    """
    Main interface defining the contract for optimization algorithms.
    All optimizers must implement this interface.
    """
    
    @abstractmethod
    def initialize(self, configuration: 'OptimizerConfiguration') -> None:
        """Initialize the optimizer with configuration settings."""
        pass
    
    @abstractmethod
    async def optimize(self) -> 'OptimizationStatistics':
        """
        Run the optimization process.
        Returns optimization statistics upon completion.
        """
        pass
    
    @abstractmethod
    def get_next_parameter_set(self) -> Optional['OptimizationParameterSet']:
        """
        Get the next parameter set to evaluate.
        Returns None when optimization is complete.
        """
        pass
    
    @abstractmethod
    def register_result(self, result: 'OptimizationResult') -> None:
        """Register the result of evaluating a parameter set."""
        pass
    
    @abstractmethod
    def is_complete(self) -> bool:
        """Check if the optimization process is complete."""
        pass
    
    @abstractmethod
    def get_best_result(self) -> Optional['OptimizationResult']:
        """Get the best result found so far."""
        pass
    
    @abstractmethod
    def get_progress(self) -> float:
        """Get optimization progress as a percentage (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the optimization process."""
        pass


class IOptimizerFactory(ABC):
    """
    Factory interface for creating optimizer instances.
    Implements the Factory pattern for optimizer instantiation.
    """
    
    @abstractmethod
    def create_optimizer(self, 
                        optimization_type: OptimizationType,
                        parameter_space: 'ParameterSpace',
                        target_function: 'IOptimizationTarget',
                        configuration: Optional['OptimizerConfiguration'] = None) -> IOptimizer:
        """Create an optimizer instance based on the specified type and configuration."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[OptimizationType]:
        """Get list of supported optimization types."""
        pass


class IOptimizationTarget(ABC):
    """
    Interface for optimization target functions.
    Defines how parameter sets are evaluated and scored.
    """
    
    @abstractmethod
    async def evaluate(self, parameter_set: 'OptimizationParameterSet') -> 'OptimizationResult':
        """
        Evaluate a parameter set and return the optimization result.
        This typically involves running a backtest with the given parameters.
        """
        pass
    
    @abstractmethod
    def get_objectives(self) -> List[str]:
        """Get list of objective metrics this target optimizes for."""
        pass
    
    @abstractmethod
    def validate_parameters(self, parameter_set: 'OptimizationParameterSet') -> bool:
        """Validate that the parameter set is valid for evaluation."""
        pass


class IParameterSpace(ABC):
    """
    Interface for parameter space management.
    Defines the search space for optimization.
    """
    
    @abstractmethod
    def add_parameter(self, parameter: 'OptimizationParameter') -> None:
        """Add a parameter to the search space."""
        pass
    
    @abstractmethod
    def remove_parameter(self, parameter_name: str) -> bool:
        """Remove a parameter from the search space."""
        pass
    
    @abstractmethod
    def get_parameter(self, parameter_name: str) -> Optional['OptimizationParameter']:
        """Get a parameter by name."""
        pass
    
    @abstractmethod
    def get_all_parameters(self) -> List['OptimizationParameter']:
        """Get all parameters in the search space."""
        pass
    
    @abstractmethod
    def generate_random_parameter_set(self) -> 'OptimizationParameterSet':
        """Generate a random parameter set within the search space."""
        pass
    
    @abstractmethod
    def validate_parameter_set(self, parameter_set: 'OptimizationParameterSet') -> bool:
        """Validate that a parameter set is within the search space bounds."""
        pass
    
    @abstractmethod
    def get_total_combinations(self) -> Optional[int]:
        """Get total number of possible parameter combinations (if finite)."""
        pass


class ISelectionStrategy(ABC):
    """Interface for genetic algorithm selection strategies."""
    
    @abstractmethod
    def select_parents(self, population: 'Population', num_parents: int) -> List['Individual']:
        """Select parents from the population for reproduction."""
        pass


class ICrossoverStrategy(ABC):
    """Interface for genetic algorithm crossover strategies."""
    
    @abstractmethod
    def crossover(self, parent1: 'Individual', parent2: 'Individual') -> List['Individual']:
        """Perform crossover between two parents to create offspring."""
        pass


class IMutationStrategy(ABC):
    """Interface for genetic algorithm mutation strategies."""
    
    @abstractmethod
    def mutate(self, individual: 'Individual', mutation_rate: float) -> 'Individual':
        """Apply mutation to an individual."""
        pass


class IConstraintHandler(ABC):
    """Interface for handling optimization constraints."""
    
    @abstractmethod
    def validate_constraints(self, parameter_set: 'OptimizationParameterSet') -> bool:
        """Check if parameter set satisfies all constraints."""
        pass
    
    @abstractmethod
    def repair_solution(self, parameter_set: 'OptimizationParameterSet') -> 'OptimizationParameterSet':
        """Repair a parameter set to satisfy constraints."""
        pass
    
    @abstractmethod
    def add_constraint(self, constraint: Callable[['OptimizationParameterSet'], bool]) -> None:
        """Add a constraint function."""
        pass


class IResultStorage(ABC):
    """Interface for storing and retrieving optimization results."""
    
    @abstractmethod
    async def store_result(self, result: 'OptimizationResult') -> None:
        """Store an optimization result."""
        pass
    
    @abstractmethod
    async def get_results(self, 
                         optimization_id: str,
                         limit: Optional[int] = None,
                         offset: Optional[int] = None) -> List['OptimizationResult']:
        """Retrieve optimization results."""
        pass
    
    @abstractmethod
    async def get_best_results(self, 
                              optimization_id: str,
                              metric: str,
                              top_n: int = 10) -> List['OptimizationResult']:
        """Get top N best results for a specific metric."""
        pass
    
    @abstractmethod
    async def delete_results(self, optimization_id: str) -> None:
        """Delete all results for an optimization run."""
        pass


class IProgressReporter(ABC):
    """Interface for reporting optimization progress."""
    
    @abstractmethod
    def report_progress(self, 
                       current_iteration: int,
                       total_iterations: int,
                       best_fitness: float,
                       current_fitness: float,
                       elapsed_time: float) -> None:
        """Report optimization progress."""
        pass
    
    @abstractmethod
    def report_completion(self, statistics: 'OptimizationStatistics') -> None:
        """Report optimization completion."""
        pass
    
    @abstractmethod
    def report_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Report optimization error."""
        pass


class IDistributedOptimizer(ABC):
    """Interface for distributed optimization across multiple nodes."""
    
    @abstractmethod
    async def submit_work(self, parameter_sets: List['OptimizationParameterSet']) -> List[str]:
        """Submit parameter sets for evaluation to worker nodes."""
        pass
    
    @abstractmethod
    async def collect_results(self, job_ids: List[str]) -> List['OptimizationResult']:
        """Collect results from worker nodes."""
        pass
    
    @abstractmethod
    def get_available_workers(self) -> int:
        """Get number of available worker nodes."""
        pass
    
    @abstractmethod
    async def shutdown_workers(self) -> None:
        """Shutdown all worker nodes."""
        pass