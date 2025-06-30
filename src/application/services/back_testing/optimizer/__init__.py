"""
Optimizer module for QuantConnect Lean Python implementation.
Provides optimization algorithms for parameter tuning and backtesting strategy optimization.
"""

from .interfaces import IOptimizer, IOptimizerFactory, IOptimizationTarget
from .parameter_management import OptimizationParameter, OptimizationParameterSet, ParameterSpace
from .result_management import OptimizationResult, PerformanceMetrics, OptimizationStatistics
from .configuration import OptimizerConfiguration, OptimizationNodePacket
from .genetic_optimizer import GeneticOptimizer, Individual, Population
from .grid_search_optimizer import GridSearchOptimizer
from .random_optimizer import RandomOptimizer
from .optimizer_factory import OptimizerFactory
from .enums import OptimizationType, SelectionType, CrossoverType, MutationType

__all__ = [
    # Interfaces
    'IOptimizer', 'IOptimizerFactory', 'IOptimizationTarget',
    
    # Parameter Management
    'OptimizationParameter', 'OptimizationParameterSet', 'ParameterSpace',
    
    # Result Management
    'OptimizationResult', 'PerformanceMetrics', 'OptimizationStatistics',
    
    # Configuration
    'OptimizerConfiguration', 'OptimizationNodePacket',
    
    # Optimizers
    'GeneticOptimizer', 'GridSearchOptimizer', 'RandomOptimizer',
    'Individual', 'Population',
    
    # Factory
    'OptimizerFactory',
    
    # Enums
    'OptimizationType', 'SelectionType', 'CrossoverType', 'MutationType',
]