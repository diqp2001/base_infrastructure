"""
Enums for the Optimizer module.
Defines optimization types, selection strategies, and other enumerated values.
"""

from enum import Enum


class OptimizationType(Enum):
    """Types of optimization algorithms available."""
    GENETIC = "genetic"
    GRID_SEARCH = "grid_search"
    RANDOM = "random"
    BAYESIAN = "bayesian"
    PARTICLE_SWARM = "particle_swarm"


class SelectionType(Enum):
    """Selection strategies for genetic algorithm."""
    TOURNAMENT = "tournament"
    ROULETTE_WHEEL = "roulette_wheel"
    RANK = "rank"
    ELITIST = "elitist"
    UNIFORM = "uniform"


class CrossoverType(Enum):
    """Crossover strategies for genetic algorithm."""
    SINGLE_POINT = "single_point"
    TWO_POINT = "two_point"
    UNIFORM = "uniform"
    ARITHMETIC = "arithmetic"
    BLEND_ALPHA = "blend_alpha"


class MutationType(Enum):
    """Mutation strategies for genetic algorithm."""
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    BOUNDARY = "boundary"
    POLYNOMIAL = "polynomial"
    CREEP = "creep"


class OptimizationStatus(Enum):
    """Status of optimization runs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ParameterType(Enum):
    """Types of optimization parameters."""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    CATEGORICAL = "categorical"


class ObjectiveDirection(Enum):
    """Direction for optimization objectives."""
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class ConstraintType(Enum):
    """Types of optimization constraints."""
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    BOUNDS = "bounds"


class FitnessMetric(Enum):
    """Available fitness metrics for optimization."""
    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    PROFIT_LOSS_RATIO = "profit_loss_ratio"
    WIN_RATE = "win_rate"
    VOLATILITY = "volatility"
    CALMAR_RATIO = "calmar_ratio"
    SORTINO_RATIO = "sortino_ratio"
    BETA = "beta"
    ALPHA = "alpha"
    TREYNOR_RATIO = "treynor_ratio"
    INFORMATION_RATIO = "information_ratio"