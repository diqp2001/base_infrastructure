"""
Configuration management for optimization.
Handles optimizer configuration, node packets, and deployment settings.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from uuid import uuid4

from .enums import OptimizationType, SelectionType, CrossoverType, MutationType, FitnessMetric, ObjectiveDirection
from .parameter_management import ParameterSpace


@dataclass
class OptimizerConfiguration:
    """
    Configuration settings for optimization algorithms.
    Contains all parameters needed to configure and run an optimization.
    """
    # Basic Configuration
    optimization_type: OptimizationType = OptimizationType.GENETIC
    optimization_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Default Optimization"
    description: str = ""
    
    # Execution Configuration
    max_concurrent_backtests: int = 4
    max_execution_time: Optional[timedelta] = None
    max_iterations: int = 100
    target_fitness: Optional[float] = None
    convergence_threshold: float = 1e-6
    convergence_generations: int = 10
    
    # Fitness Configuration
    target_metric: FitnessMetric = FitnessMetric.SHARPE_RATIO
    objective_direction: ObjectiveDirection = ObjectiveDirection.MAXIMIZE
    multi_objective_weights: Optional[Dict[FitnessMetric, float]] = None
    
    # Genetic Algorithm Configuration
    population_size: int = 50
    max_generations: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elitism_rate: float = 0.1
    selection_type: SelectionType = SelectionType.TOURNAMENT
    crossover_type: CrossoverType = CrossoverType.UNIFORM
    mutation_type: MutationType = MutationType.GAUSSIAN
    
    # Tournament Selection Parameters
    tournament_size: int = 3
    selection_pressure: float = 2.0
    
    # Crossover Parameters
    crossover_alpha: float = 0.5  # For blend alpha crossover
    crossover_points: int = 2     # For multi-point crossover
    
    # Mutation Parameters
    mutation_sigma: float = 0.1   # For Gaussian mutation
    mutation_boundary_prob: float = 0.1  # For boundary mutation
    
    # Grid Search Configuration
    grid_search_step_size: Optional[Dict[str, float]] = None
    grid_search_max_combinations: Optional[int] = None
    
    # Random Search Configuration
    random_search_samples: int = 1000
    random_search_seed: Optional[int] = None
    
    # Constraints and Validation
    constraint_functions: List[Callable] = field(default_factory=list)
    validation_functions: List[Callable] = field(default_factory=list)
    repair_invalid_solutions: bool = True
    
    # Resource Management
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None
    disk_space_limit_gb: Optional[float] = None
    
    # Result Storage
    store_all_results: bool = True
    store_equity_curves: bool = False
    store_trade_logs: bool = False
    result_storage_path: Optional[str] = None
    
    # Monitoring and Reporting
    progress_reporting_interval: int = 10  # Report every N iterations
    enable_live_monitoring: bool = True
    log_level: str = "INFO"
    
    # Advanced Configuration
    distributed_execution: bool = False
    worker_nodes: List[str] = field(default_factory=list)
    fault_tolerance: bool = True
    checkpoint_interval: int = 50  # Checkpoint every N iterations
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Basic validation
        if self.population_size <= 0:
            errors.append("population_size must be positive")
        
        if self.max_generations <= 0:
            errors.append("max_generations must be positive")
        
        if not (0.0 <= self.mutation_rate <= 1.0):
            errors.append("mutation_rate must be between 0.0 and 1.0")
        
        if not (0.0 <= self.crossover_rate <= 1.0):
            errors.append("crossover_rate must be between 0.0 and 1.0")
        
        if not (0.0 <= self.elitism_rate <= 1.0):
            errors.append("elitism_rate must be between 0.0 and 1.0")
        
        if self.max_concurrent_backtests <= 0:
            errors.append("max_concurrent_backtests must be positive")
        
        # Genetic algorithm specific validation
        if self.optimization_type == OptimizationType.GENETIC:
            if self.tournament_size <= 0:
                errors.append("tournament_size must be positive")
            
            if self.selection_pressure <= 0:
                errors.append("selection_pressure must be positive")
        
        # Multi-objective validation
        if self.multi_objective_weights:
            total_weight = sum(self.multi_objective_weights.values())
            if abs(total_weight - 1.0) > 1e-6:
                errors.append("multi_objective_weights must sum to 1.0")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0
    
    def get_genetic_parameters(self) -> Dict[str, Any]:
        """Get genetic algorithm specific parameters."""
        return {
            'population_size': self.population_size,
            'max_generations': self.max_generations,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
            'elitism_rate': self.elitism_rate,
            'selection_type': self.selection_type,
            'crossover_type': self.crossover_type,
            'mutation_type': self.mutation_type,
            'tournament_size': self.tournament_size,
            'selection_pressure': self.selection_pressure,
            'crossover_alpha': self.crossover_alpha,
            'crossover_points': self.crossover_points,
            'mutation_sigma': self.mutation_sigma,
            'mutation_boundary_prob': self.mutation_boundary_prob
        }
    
    def get_execution_parameters(self) -> Dict[str, Any]:
        """Get execution-related parameters."""
        return {
            'max_concurrent_backtests': self.max_concurrent_backtests,
            'max_execution_time': self.max_execution_time,
            'max_iterations': self.max_iterations,
            'target_fitness': self.target_fitness,
            'convergence_threshold': self.convergence_threshold,
            'convergence_generations': self.convergence_generations
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'optimization_type': self.optimization_type.value,
            'optimization_id': self.optimization_id,
            'name': self.name,
            'description': self.description,
            'max_concurrent_backtests': self.max_concurrent_backtests,
            'max_execution_time': self.max_execution_time.total_seconds() if self.max_execution_time else None,
            'max_iterations': self.max_iterations,
            'target_fitness': self.target_fitness,
            'convergence_threshold': self.convergence_threshold,
            'convergence_generations': self.convergence_generations,
            'target_metric': self.target_metric.value,
            'objective_direction': self.objective_direction.value,
            'multi_objective_weights': {k.value: v for k, v in self.multi_objective_weights.items()} if self.multi_objective_weights else None,
            'population_size': self.population_size,
            'max_generations': self.max_generations,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
            'elitism_rate': self.elitism_rate,
            'selection_type': self.selection_type.value,
            'crossover_type': self.crossover_type.value,
            'mutation_type': self.mutation_type.value,
            'tournament_size': self.tournament_size,
            'selection_pressure': self.selection_pressure,
            'crossover_alpha': self.crossover_alpha,
            'crossover_points': self.crossover_points,
            'mutation_sigma': self.mutation_sigma,
            'mutation_boundary_prob': self.mutation_boundary_prob,
            'grid_search_step_size': self.grid_search_step_size,
            'grid_search_max_combinations': self.grid_search_max_combinations,
            'random_search_samples': self.random_search_samples,
            'random_search_seed': self.random_search_seed,
            'repair_invalid_solutions': self.repair_invalid_solutions,
            'memory_limit_mb': self.memory_limit_mb,
            'cpu_limit_percent': self.cpu_limit_percent,
            'disk_space_limit_gb': self.disk_space_limit_gb,
            'store_all_results': self.store_all_results,
            'store_equity_curves': self.store_equity_curves,
            'store_trade_logs': self.store_trade_logs,
            'result_storage_path': self.result_storage_path,
            'progress_reporting_interval': self.progress_reporting_interval,
            'enable_live_monitoring': self.enable_live_monitoring,
            'log_level': self.log_level,
            'distributed_execution': self.distributed_execution,
            'worker_nodes': self.worker_nodes,
            'fault_tolerance': self.fault_tolerance,
            'checkpoint_interval': self.checkpoint_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizerConfiguration':
        """Create configuration from dictionary."""
        config = cls()
        
        # Simple field mapping
        simple_fields = [
            'optimization_id', 'name', 'description', 'max_concurrent_backtests',
            'max_iterations', 'target_fitness', 'convergence_threshold', 'convergence_generations',
            'population_size', 'max_generations', 'mutation_rate', 'crossover_rate', 'elitism_rate',
            'tournament_size', 'selection_pressure', 'crossover_alpha', 'crossover_points',
            'mutation_sigma', 'mutation_boundary_prob', 'grid_search_step_size', 
            'grid_search_max_combinations', 'random_search_samples', 'random_search_seed',
            'repair_invalid_solutions', 'memory_limit_mb', 'cpu_limit_percent', 'disk_space_limit_gb',
            'store_all_results', 'store_equity_curves', 'store_trade_logs', 'result_storage_path',
            'progress_reporting_interval', 'enable_live_monitoring', 'log_level',
            'distributed_execution', 'worker_nodes', 'fault_tolerance', 'checkpoint_interval'
        ]
        
        for field in simple_fields:
            if field in data:
                setattr(config, field, data[field])
        
        # Enum fields
        if 'optimization_type' in data:
            config.optimization_type = OptimizationType(data['optimization_type'])
        
        if 'target_metric' in data:
            config.target_metric = FitnessMetric(data['target_metric'])
        
        if 'objective_direction' in data:
            config.objective_direction = ObjectiveDirection(data['objective_direction'])
        
        if 'selection_type' in data:
            config.selection_type = SelectionType(data['selection_type'])
        
        if 'crossover_type' in data:
            config.crossover_type = CrossoverType(data['crossover_type'])
        
        if 'mutation_type' in data:
            config.mutation_type = MutationType(data['mutation_type'])
        
        # Special handling for timedelta
        if 'max_execution_time' in data and data['max_execution_time']:
            config.max_execution_time = timedelta(seconds=data['max_execution_time'])
        
        # Multi-objective weights
        if 'multi_objective_weights' in data and data['multi_objective_weights']:
            config.multi_objective_weights = {
                FitnessMetric(k): v for k, v in data['multi_objective_weights'].items()
            }
        
        return config
    
    def copy(self) -> 'OptimizerConfiguration':
        """Create a deep copy of the configuration."""
        return OptimizerConfiguration.from_dict(self.to_dict())


@dataclass
class OptimizationNodePacket:
    """
    Data packet for distributed optimization nodes.
    Contains all information needed to execute optimization on a remote node.
    """
    # Identification
    packet_id: str = field(default_factory=lambda: str(uuid4()))
    optimization_id: str = ""
    node_id: str = ""
    
    # Algorithm Information
    algorithm_id: str = ""
    algorithm_name: str = ""
    algorithm_language: str = "python"
    algorithm_code: Optional[str] = None
    algorithm_path: Optional[str] = None
    
    # Parameter Information
    parameter_set_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution Configuration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_cash: float = 100000.0
    benchmark_symbol: Optional[str] = None
    
    # Data Configuration
    data_feeds: List[str] = field(default_factory=list)
    universe_symbols: List[str] = field(default_factory=list)
    resolution: str = "daily"
    
    # Brokerage Configuration
    brokerage_model: str = "default"
    commission_model: Optional[str] = None
    slippage_model: Optional[str] = None
    
    # Result Configuration
    result_handler: str = "default"
    result_destination: Optional[str] = None
    store_equity_curve: bool = False
    store_trade_log: bool = False
    
    # Execution Status
    status: str = "pending"
    created_time: datetime = field(default_factory=datetime.now)
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Resource Limits
    memory_limit: Optional[int] = None
    time_limit: Optional[int] = None
    
    # Authentication and Security
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    api_token: Optional[str] = None
    
    def mark_started(self) -> None:
        """Mark the packet as started."""
        self.status = "running"
        self.started_time = datetime.now()
    
    def mark_completed(self) -> None:
        """Mark the packet as completed."""
        self.status = "completed"
        self.completed_time = datetime.now()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark the packet as failed with error message."""
        self.status = "failed"
        self.completed_time = datetime.now()
        self.error_message = error_message
    
    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds."""
        if self.started_time and self.completed_time:
            return (self.completed_time - self.started_time).total_seconds()
        return None
    
    def is_complete(self) -> bool:
        """Check if packet execution is complete."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def is_successful(self) -> bool:
        """Check if packet execution was successful."""
        return self.status == "completed" and self.error_message is None
    
    def validate(self) -> List[str]:
        """Validate packet and return list of errors."""
        errors = []
        
        if not self.optimization_id:
            errors.append("optimization_id is required")
        
        if not self.algorithm_id:
            errors.append("algorithm_id is required")
        
        if not self.parameter_set_id:
            errors.append("parameter_set_id is required")
        
        if not self.algorithm_code and not self.algorithm_path:
            errors.append("Either algorithm_code or algorithm_path must be provided")
        
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors.append("start_date must be before end_date")
        
        if self.initial_cash <= 0:
            errors.append("initial_cash must be positive")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if packet is valid."""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for serialization."""
        return {
            'packet_id': self.packet_id,
            'optimization_id': self.optimization_id,
            'node_id': self.node_id,
            'algorithm_id': self.algorithm_id,
            'algorithm_name': self.algorithm_name,
            'algorithm_language': self.algorithm_language,
            'algorithm_code': self.algorithm_code,
            'algorithm_path': self.algorithm_path,
            'parameter_set_id': self.parameter_set_id,
            'parameters': self.parameters,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'initial_cash': self.initial_cash,
            'benchmark_symbol': self.benchmark_symbol,
            'data_feeds': self.data_feeds,
            'universe_symbols': self.universe_symbols,
            'resolution': self.resolution,
            'brokerage_model': self.brokerage_model,
            'commission_model': self.commission_model,
            'slippage_model': self.slippage_model,
            'result_handler': self.result_handler,
            'result_destination': self.result_destination,
            'store_equity_curve': self.store_equity_curve,
            'store_trade_log': self.store_trade_log,
            'status': self.status,
            'created_time': self.created_time.isoformat(),
            'started_time': self.started_time.isoformat() if self.started_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'error_message': self.error_message,
            'memory_limit': self.memory_limit,
            'time_limit': self.time_limit,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'api_token': self.api_token
        }
    
    def to_json(self) -> str:
        """Convert packet to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationNodePacket':
        """Create packet from dictionary."""
        packet = cls()
        
        # Simple field mapping
        simple_fields = [
            'packet_id', 'optimization_id', 'node_id', 'algorithm_id', 'algorithm_name',
            'algorithm_language', 'algorithm_code', 'algorithm_path', 'parameter_set_id',
            'parameters', 'initial_cash', 'benchmark_symbol', 'data_feeds', 'universe_symbols',
            'resolution', 'brokerage_model', 'commission_model', 'slippage_model',
            'result_handler', 'result_destination', 'store_equity_curve', 'store_trade_log',
            'status', 'error_message', 'memory_limit', 'time_limit', 'user_id', 'project_id',
            'api_token'
        ]
        
        for field in simple_fields:
            if field in data and data[field] is not None:
                setattr(packet, field, data[field])
        
        # Date fields
        if 'start_date' in data and data['start_date']:
            packet.start_date = datetime.fromisoformat(data['start_date'])
        
        if 'end_date' in data and data['end_date']:
            packet.end_date = datetime.fromisoformat(data['end_date'])
        
        if 'created_time' in data:
            packet.created_time = datetime.fromisoformat(data['created_time'])
        
        if 'started_time' in data and data['started_time']:
            packet.started_time = datetime.fromisoformat(data['started_time'])
        
        if 'completed_time' in data and data['completed_time']:
            packet.completed_time = datetime.fromisoformat(data['completed_time'])
        
        return packet
    
    @classmethod
    def from_json(cls, json_str: str) -> 'OptimizationNodePacket':
        """Create packet from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def __repr__(self) -> str:
        """String representation of the node packet."""
        return (f"OptimizationNodePacket(id='{self.packet_id}', "
                f"algorithm='{self.algorithm_name}', "
                f"status='{self.status}')")