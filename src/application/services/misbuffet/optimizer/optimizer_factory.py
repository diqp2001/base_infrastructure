"""
Optimizer Factory implementation.
Provides factory pattern for creating optimizer instances with proper configuration.
"""

import logging
from typing import Optional, List, Dict, Any, Type

from .interfaces import IOptimizer, IOptimizerFactory, IOptimizationTarget
from .parameter_management import ParameterSpace
from .configuration import OptimizerConfiguration
from .enums import OptimizationType
from .genetic_optimizer import GeneticOptimizer
from .grid_search_optimizer import GridSearchOptimizer
from .random_optimizer import RandomOptimizer


class OptimizerFactory(IOptimizerFactory):
    """
    Factory for creating optimizer instances.
    Implements the Factory pattern for optimizer instantiation with proper validation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Registry of available optimizer types
        self._optimizer_registry: Dict[OptimizationType, Type[IOptimizer]] = {
            OptimizationType.GENETIC: GeneticOptimizer,
            OptimizationType.GRID_SEARCH: GridSearchOptimizer,
            OptimizationType.RANDOM: RandomOptimizer,
        }
        
        # Configuration validators for each optimizer type
        self._configuration_validators: Dict[OptimizationType, callable] = {
            OptimizationType.GENETIC: self._validate_genetic_configuration,
            OptimizationType.GRID_SEARCH: self._validate_grid_search_configuration,
            OptimizationType.RANDOM: self._validate_random_configuration,
        }
    
    def create_optimizer(self, 
                        optimization_type: OptimizationType,
                        parameter_space: ParameterSpace,
                        target_function: IOptimizationTarget,
                        configuration: Optional[OptimizerConfiguration] = None) -> IOptimizer:
        """
        Create an optimizer instance based on the specified type and configuration.
        
        Args:
            optimization_type: Type of optimizer to create
            parameter_space: Parameter space for optimization
            target_function: Target function to optimize
            configuration: Configuration settings for the optimizer
            
        Returns:
            Configured optimizer instance
            
        Raises:
            ValueError: If optimization type is not supported or configuration is invalid
            TypeError: If required parameters are missing or invalid
        """
        # Validate inputs
        self._validate_factory_inputs(optimization_type, parameter_space, target_function)
        
        # Create default configuration if none provided
        if configuration is None:
            configuration = self._create_default_configuration(optimization_type)
        else:
            # Validate provided configuration
            self._validate_configuration(optimization_type, configuration, parameter_space)
        
        # Get optimizer class
        optimizer_class = self._optimizer_registry.get(optimization_type)
        if optimizer_class is None:
            raise ValueError(f"Unsupported optimization type: {optimization_type}")
        
        # Create and configure optimizer
        try:
            optimizer = optimizer_class(
                parameter_space=parameter_space,
                target_function=target_function,
                configuration=configuration
            )
            
            self.logger.info(f"Created {optimization_type.value} optimizer with configuration: {configuration.optimization_id}")
            return optimizer
            
        except Exception as e:
            self.logger.error(f"Failed to create {optimization_type.value} optimizer: {e}")
            raise
    
    def get_supported_types(self) -> List[OptimizationType]:
        """Get list of supported optimization types."""
        return list(self._optimizer_registry.keys())
    
    def register_optimizer(self, optimization_type: OptimizationType, optimizer_class: Type[IOptimizer]) -> None:
        """
        Register a new optimizer type.
        
        Args:
            optimization_type: Type identifier for the optimizer
            optimizer_class: Optimizer class that implements IOptimizer
        """
        if not issubclass(optimizer_class, IOptimizer):
            raise TypeError("Optimizer class must implement IOptimizer interface")
        
        self._optimizer_registry[optimization_type] = optimizer_class
        self.logger.info(f"Registered optimizer type: {optimization_type.value}")
    
    def unregister_optimizer(self, optimization_type: OptimizationType) -> bool:
        """
        Unregister an optimizer type.
        
        Args:
            optimization_type: Type identifier to unregister
            
        Returns:
            True if successfully unregistered, False if type was not registered
        """
        if optimization_type in self._optimizer_registry:
            del self._optimizer_registry[optimization_type]
            self.logger.info(f"Unregistered optimizer type: {optimization_type.value}")
            return True
        return False
    
    def is_supported(self, optimization_type: OptimizationType) -> bool:
        """Check if an optimization type is supported."""
        return optimization_type in self._optimizer_registry
    
    def get_optimizer_info(self, optimization_type: OptimizationType) -> Dict[str, Any]:
        """Get information about a specific optimizer type."""
        if not self.is_supported(optimization_type):
            raise ValueError(f"Unsupported optimization type: {optimization_type}")
        
        optimizer_class = self._optimizer_registry[optimization_type]
        
        return {
            'type': optimization_type.value,
            'class_name': optimizer_class.__name__,
            'module': optimizer_class.__module__,
            'description': getattr(optimizer_class, '__doc__', 'No description available'),
            'supports_concurrent_evaluation': True,  # All current optimizers support this
            'supports_early_stopping': True,
            'requires_discrete_parameters': optimization_type == OptimizationType.GRID_SEARCH
        }
    
    def get_recommended_configuration(self, 
                                    optimization_type: OptimizationType,
                                    parameter_space: ParameterSpace,
                                    evaluation_budget: Optional[int] = None) -> OptimizerConfiguration:
        """
        Get recommended configuration for an optimization type and parameter space.
        
        Args:
            optimization_type: Type of optimizer
            parameter_space: Parameter space for optimization
            evaluation_budget: Maximum number of evaluations allowed
            
        Returns:
            Recommended configuration
        """
        config = OptimizerConfiguration(optimization_type=optimization_type)
        
        # Get parameter space characteristics
        num_parameters = len(parameter_space)
        total_combinations = parameter_space.get_total_combinations()
        
        if optimization_type == OptimizationType.GENETIC:
            # Genetic algorithm recommendations
            config.population_size = min(50, max(20, num_parameters * 10))
            config.max_generations = 100
            
            if evaluation_budget:
                # Adjust generations based on budget
                max_evaluations_per_gen = config.population_size
                config.max_generations = min(config.max_generations, evaluation_budget // max_evaluations_per_gen)
            
            # Adjust based on parameter space size
            if num_parameters > 10:
                config.mutation_rate = 0.15  # Higher mutation for complex spaces
                config.crossover_rate = 0.7   # Lower crossover to preserve good solutions
            
        elif optimization_type == OptimizationType.GRID_SEARCH:
            # Grid search recommendations
            if total_combinations and evaluation_budget:
                config.grid_search_max_combinations = min(total_combinations, evaluation_budget)
            
            # Warn if grid search might be inefficient
            if total_combinations and total_combinations > 10000:
                self.logger.warning(
                    f"Grid search with {total_combinations} combinations may be inefficient. "
                    f"Consider using genetic algorithm or random search."
                )
        
        elif optimization_type == OptimizationType.RANDOM:
            # Random search recommendations
            if evaluation_budget:
                config.random_search_samples = evaluation_budget
            else:
                # Default based on parameter space size
                config.random_search_samples = min(1000, max(100, num_parameters * 50))
        
        # Common recommendations
        config.max_concurrent_backtests = min(8, max(2, num_parameters // 2))
        
        return config
    
    def _validate_factory_inputs(self, 
                                optimization_type: OptimizationType,
                                parameter_space: ParameterSpace,
                                target_function: IOptimizationTarget) -> None:
        """Validate factory method inputs."""
        if not isinstance(optimization_type, OptimizationType):
            raise TypeError("optimization_type must be an OptimizationType enum")
        
        if not isinstance(parameter_space, ParameterSpace):
            raise TypeError("parameter_space must be a ParameterSpace instance")
        
        if not isinstance(target_function, IOptimizationTarget):
            raise TypeError("target_function must implement IOptimizationTarget interface")
        
        if len(parameter_space) == 0:
            raise ValueError("Parameter space must contain at least one parameter")
    
    def _validate_configuration(self, 
                               optimization_type: OptimizationType,
                               configuration: OptimizerConfiguration,
                               parameter_space: ParameterSpace) -> None:
        """Validate configuration for specific optimizer type."""
        # General configuration validation
        if not isinstance(configuration, OptimizerConfiguration):
            raise TypeError("configuration must be an OptimizerConfiguration instance")
        
        errors = configuration.validate()
        if errors:
            raise ValueError(f"Configuration validation errors: {errors}")
        
        # Type-specific validation
        validator = self._configuration_validators.get(optimization_type)
        if validator:
            validator(configuration, parameter_space)
    
    def _validate_genetic_configuration(self, 
                                      configuration: OptimizerConfiguration,
                                      parameter_space: ParameterSpace) -> None:
        """Validate genetic algorithm specific configuration."""
        if configuration.population_size < 2:
            raise ValueError("Genetic algorithm requires population_size >= 2")
        
        if configuration.max_generations < 1:
            raise ValueError("Genetic algorithm requires max_generations >= 1")
        
        # Check that population size makes sense relative to parameter space
        if configuration.population_size > 1000:
            self.logger.warning("Large population size may impact performance")
    
    def _validate_grid_search_configuration(self, 
                                          configuration: OptimizerConfiguration,
                                          parameter_space: ParameterSpace) -> None:
        """Validate grid search specific configuration."""
        total_combinations = parameter_space.get_total_combinations()
        
        if total_combinations is None:
            raise ValueError("Grid search requires discrete parameter space with finite combinations")
        
        if total_combinations == 0:
            raise ValueError("Parameter space has no valid combinations")
        
        # Warn about large search spaces
        if total_combinations > 100000:
            self.logger.warning(
                f"Grid search with {total_combinations} combinations may take a very long time. "
                f"Consider limiting with grid_search_max_combinations or using a different optimizer."
            )
    
    def _validate_random_configuration(self, 
                                     configuration: OptimizerConfiguration,
                                     parameter_space: ParameterSpace) -> None:
        """Validate random search specific configuration."""
        if configuration.random_search_samples < 1:
            raise ValueError("Random search requires random_search_samples >= 1")
        
        # Check if sample size is reasonable
        total_combinations = parameter_space.get_total_combinations()
        if (total_combinations is not None and 
            configuration.random_search_samples > total_combinations):
            self.logger.warning(
                f"Random search samples ({configuration.random_search_samples}) exceeds "
                f"total possible combinations ({total_combinations}). "
                f"Consider using grid search instead."
            )
    
    def _create_default_configuration(self, optimization_type: OptimizationType) -> OptimizerConfiguration:
        """Create default configuration for optimization type."""
        config = OptimizerConfiguration(optimization_type=optimization_type)
        
        # Set type-specific defaults
        if optimization_type == OptimizationType.GENETIC:
            config.population_size = 30
            config.max_generations = 50
            config.mutation_rate = 0.1
            config.crossover_rate = 0.8
            config.elitism_rate = 0.1
        
        elif optimization_type == OptimizationType.GRID_SEARCH:
            config.grid_search_max_combinations = 10000
        
        elif optimization_type == OptimizationType.RANDOM:
            config.random_search_samples = 500
        
        return config
    
    def create_multiple_optimizers(self, 
                                 configurations: List[Dict[str, Any]],
                                 parameter_space: ParameterSpace,
                                 target_function: IOptimizationTarget) -> List[IOptimizer]:
        """
        Create multiple optimizers from a list of configurations.
        Useful for ensemble optimization or comparison studies.
        
        Args:
            configurations: List of configuration dictionaries
            parameter_space: Parameter space for optimization
            target_function: Target function to optimize
            
        Returns:
            List of configured optimizer instances
        """
        optimizers = []
        
        for i, config_dict in enumerate(configurations):
            try:
                # Extract optimization type
                opt_type_str = config_dict.get('optimization_type', 'genetic')
                optimization_type = OptimizationType(opt_type_str)
                
                # Create configuration
                config = OptimizerConfiguration.from_dict(config_dict)
                
                # Create optimizer
                optimizer = self.create_optimizer(
                    optimization_type=optimization_type,
                    parameter_space=parameter_space,
                    target_function=target_function,
                    configuration=config
                )
                
                optimizers.append(optimizer)
                
            except Exception as e:
                self.logger.error(f"Failed to create optimizer {i}: {e}")
                raise
        
        self.logger.info(f"Created {len(optimizers)} optimizers")
        return optimizers
    
    def __repr__(self) -> str:
        """String representation of the optimizer factory."""
        supported_types = [opt_type.value for opt_type in self.get_supported_types()]
        return f"OptimizerFactory(supported_types={supported_types})"


# Global factory instance
default_optimizer_factory = OptimizerFactory()


def create_optimizer(optimization_type: OptimizationType,
                    parameter_space: ParameterSpace,
                    target_function: IOptimizationTarget,
                    configuration: Optional[OptimizerConfiguration] = None) -> IOptimizer:
    """
    Convenience function to create an optimizer using the default factory.
    
    Args:
        optimization_type: Type of optimizer to create
        parameter_space: Parameter space for optimization
        target_function: Target function to optimize
        configuration: Configuration settings for the optimizer
        
    Returns:
        Configured optimizer instance
    """
    return default_optimizer_factory.create_optimizer(
        optimization_type=optimization_type,
        parameter_space=parameter_space,
        target_function=target_function,
        configuration=configuration
    )


def get_recommended_configuration(optimization_type: OptimizationType,
                                parameter_space: ParameterSpace,
                                evaluation_budget: Optional[int] = None) -> OptimizerConfiguration:
    """
    Convenience function to get recommended configuration using the default factory.
    
    Args:
        optimization_type: Type of optimizer
        parameter_space: Parameter space for optimization
        evaluation_budget: Maximum number of evaluations allowed
        
    Returns:
        Recommended configuration
    """
    return default_optimizer_factory.get_recommended_configuration(
        optimization_type=optimization_type,
        parameter_space=parameter_space,
        evaluation_budget=evaluation_budget
    )