"""
Result management for optimization.
Handles optimization results, performance metrics, and statistical analysis.
"""

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from collections import defaultdict

from .enums import OptimizationStatus, FitnessMetric, ObjectiveDirection
from .parameter_management import OptimizationParameterSet


@dataclass
class PerformanceMetrics:
    """
    Performance metrics from backtest results.
    Contains all relevant trading performance indicators.
    """
    # Core Performance Metrics
    total_return: float = 0.0
    annual_return: float = 0.0
    cumulative_return: float = 0.0
    
    # Risk Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    maximum_drawdown: float = 0.0
    maximum_drawdown_duration: int = 0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    
    # Trading Metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Market Exposure Metrics
    beta: float = 0.0
    alpha: float = 0.0
    treynor_ratio: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    
    # Time-based Metrics
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0
    
    # Additional Custom Metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def calculate_fitness(self, 
                         target_metric: FitnessMetric = FitnessMetric.SHARPE_RATIO,
                         direction: ObjectiveDirection = ObjectiveDirection.MAXIMIZE) -> float:
        """Calculate fitness score based on target metric and direction."""
        metric_value = self.get_metric_value(target_metric)
        
        if direction == ObjectiveDirection.MAXIMIZE:
            return metric_value
        else:
            return -metric_value
    
    def get_metric_value(self, metric: FitnessMetric) -> float:
        """Get the value of a specific metric."""
        metric_map = {
            FitnessMetric.SHARPE_RATIO: self.sharpe_ratio,
            FitnessMetric.TOTAL_RETURN: self.total_return,
            FitnessMetric.MAXIMUM_DRAWDOWN: self.maximum_drawdown,
            FitnessMetric.PROFIT_LOSS_RATIO: self.profit_loss_ratio,
            FitnessMetric.WIN_RATE: self.win_rate,
            FitnessMetric.VOLATILITY: self.volatility,
            FitnessMetric.CALMAR_RATIO: self.calmar_ratio,
            FitnessMetric.SORTINO_RATIO: self.sortino_ratio,
            FitnessMetric.BETA: self.beta,
            FitnessMetric.ALPHA: self.alpha,
            FitnessMetric.TREYNOR_RATIO: self.treynor_ratio,
            FitnessMetric.INFORMATION_RATIO: self.information_ratio,
        }
        
        return metric_map.get(metric, 0.0)
    
    def is_valid(self) -> bool:
        """Check if metrics are valid (not NaN or infinite)."""
        core_metrics = [
            self.total_return, self.sharpe_ratio, self.maximum_drawdown,
            self.volatility, self.win_rate, self.profit_loss_ratio
        ]
        
        for metric in core_metrics:
            if np.isnan(metric) or np.isinf(metric):
                return False
        
        return True
    
    def normalize_metrics(self) -> None:
        """Normalize metrics to handle NaN and infinite values."""
        def safe_float(value: float, default: float = 0.0) -> float:
            if np.isnan(value) or np.isinf(value):
                return default
            return value
        
        self.total_return = safe_float(self.total_return)
        self.annual_return = safe_float(self.annual_return)
        self.sharpe_ratio = safe_float(self.sharpe_ratio)
        self.sortino_ratio = safe_float(self.sortino_ratio)
        self.calmar_ratio = safe_float(self.calmar_ratio)
        self.maximum_drawdown = safe_float(self.maximum_drawdown)
        self.volatility = safe_float(self.volatility)
        self.win_rate = safe_float(self.win_rate, 0.0)
        self.profit_loss_ratio = safe_float(self.profit_loss_ratio, 1.0)
        self.beta = safe_float(self.beta, 1.0)
        self.alpha = safe_float(self.alpha)
        self.treynor_ratio = safe_float(self.treynor_ratio)
        self.information_ratio = safe_float(self.information_ratio)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'cumulative_return': self.cumulative_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'maximum_drawdown': self.maximum_drawdown,
            'maximum_drawdown_duration': self.maximum_drawdown_duration,
            'volatility': self.volatility,
            'downside_deviation': self.downside_deviation,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'average_win': self.average_win,
            'average_loss': self.average_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'beta': self.beta,
            'alpha': self.alpha,
            'treynor_ratio': self.treynor_ratio,
            'information_ratio': self.information_ratio,
            'tracking_error': self.tracking_error,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'trading_days': self.trading_days,
            'custom_metrics': self.custom_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        """Create metrics from dictionary."""
        metrics = cls()
        for key, value in data.items():
            if key in ['start_date', 'end_date'] and value:
                setattr(metrics, key, datetime.fromisoformat(value))
            elif hasattr(metrics, key):
                setattr(metrics, key, value)
        return metrics


@dataclass
class OptimizationResult:
    """
    Results from a single optimization run.
    Contains parameter set, performance metrics, and execution details.
    """
    parameter_set: OptimizationParameterSet
    performance_metrics: PerformanceMetrics
    backtest_id: str
    execution_time: float
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    error_message: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    fitness: Optional[float] = None
    rank: Optional[int] = None
    
    # Additional result data
    equity_curve: Optional[List[float]] = None
    trade_log: Optional[List[Dict[str, Any]]] = None
    benchmark_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Calculate fitness and end time if not set."""
        if self.fitness is None:
            self.fitness = self.performance_metrics.calculate_fitness()
        
        if self.end_time is None:
            self.end_time = self.start_time + timedelta(seconds=self.execution_time)
    
    def is_successful(self) -> bool:
        """Check if the optimization run was successful."""
        return (self.status == OptimizationStatus.COMPLETED and 
                self.error_message is None and
                self.performance_metrics.is_valid())
    
    def get_fitness_score(self, 
                         metric: FitnessMetric = FitnessMetric.SHARPE_RATIO,
                         direction: ObjectiveDirection = ObjectiveDirection.MAXIMIZE) -> float:
        """Get fitness score for a specific metric."""
        return self.performance_metrics.calculate_fitness(metric, direction)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for storage/serialization."""
        return {
            'parameter_set': self.parameter_set.to_dict(),
            'performance_metrics': self.performance_metrics.to_dict(),
            'backtest_id': self.backtest_id,
            'execution_time': self.execution_time,
            'status': self.status.value,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'fitness': self.fitness,
            'rank': self.rank,
            'equity_curve': self.equity_curve,
            'trade_log': self.trade_log,
            'benchmark_data': self.benchmark_data
        }
    
    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationResult':
        """Create result from dictionary."""
        return cls(
            parameter_set=OptimizationParameterSet.from_dict(data['parameter_set']),
            performance_metrics=PerformanceMetrics.from_dict(data['performance_metrics']),
            backtest_id=data['backtest_id'],
            execution_time=data['execution_time'],
            status=OptimizationStatus(data['status']),
            error_message=data.get('error_message'),
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            fitness=data.get('fitness'),
            rank=data.get('rank'),
            equity_curve=data.get('equity_curve'),
            trade_log=data.get('trade_log'),
            benchmark_data=data.get('benchmark_data')
        )


@dataclass
class OptimizationStatistics:
    """
    Aggregated statistics across multiple optimization runs.
    Provides summary and analysis of optimization session.
    """
    optimization_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Run Statistics
    total_runs_requested: int = 0
    total_runs_completed: int = 0
    total_runs_failed: int = 0
    total_runs_cancelled: int = 0
    
    # Performance Statistics
    best_result: Optional[OptimizationResult] = None
    worst_result: Optional[OptimizationResult] = None
    mean_fitness: float = 0.0
    median_fitness: float = 0.0
    std_fitness: float = 0.0
    
    # Timing Statistics
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    min_execution_time: float = 0.0
    max_execution_time: float = 0.0
    
    # Convergence Statistics
    generations_completed: int = 0
    convergence_achieved: bool = False
    convergence_generation: Optional[int] = None
    improvement_rate: float = 0.0
    
    # Additional Statistics
    parameter_importance: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Optional[np.ndarray] = None
    pareto_front: Optional[List[OptimizationResult]] = None
    
    def update_with_results(self, results: List[OptimizationResult]) -> None:
        """Update statistics with a list of optimization results."""
        if not results:
            return
        
        # Filter successful results
        successful_results = [r for r in results if r.is_successful()]
        
        self.total_runs_completed = len(successful_results)
        self.total_runs_failed = len([r for r in results if r.status == OptimizationStatus.FAILED])
        
        if not successful_results:
            return
        
        # Calculate fitness statistics
        fitness_values = [r.fitness for r in successful_results if r.fitness is not None]
        if fitness_values:
            self.mean_fitness = mean(fitness_values)
            self.median_fitness = median(fitness_values)
            if len(fitness_values) > 1:
                self.std_fitness = stdev(fitness_values)
        
        # Find best and worst results
        self.best_result = max(successful_results, key=lambda r: r.fitness or 0)
        self.worst_result = min(successful_results, key=lambda r: r.fitness or 0)
        
        # Calculate timing statistics
        execution_times = [r.execution_time for r in successful_results]
        if execution_times:
            self.total_execution_time = sum(execution_times)
            self.average_execution_time = mean(execution_times)
            self.min_execution_time = min(execution_times)
            self.max_execution_time = max(execution_times)
        
        # Calculate parameter importance
        self._calculate_parameter_importance(successful_results)
    
    def _calculate_parameter_importance(self, results: List[OptimizationResult]) -> None:
        """Calculate parameter importance using correlation with fitness."""
        if len(results) < 2:
            return
        
        # Create parameter matrix
        parameter_names = set()
        for result in results:
            parameter_names.update(result.parameter_set.parameters.keys())
        
        parameter_names = list(parameter_names)
        parameter_matrix = []
        fitness_values = []
        
        for result in results:
            if result.fitness is not None:
                param_values = []
                for param_name in parameter_names:
                    value = result.parameter_set.get_parameter_value(param_name, 0)
                    # Convert to numeric if possible
                    try:
                        param_values.append(float(value))
                    except (ValueError, TypeError):
                        param_values.append(0.0)
                
                parameter_matrix.append(param_values)
                fitness_values.append(result.fitness)
        
        if len(parameter_matrix) < 2:
            return
        
        # Calculate correlations
        try:
            param_df = pd.DataFrame(parameter_matrix, columns=parameter_names)
            fitness_series = pd.Series(fitness_values)
            
            correlations = param_df.corrwith(fitness_series)
            self.parameter_importance = correlations.abs().to_dict()
        except Exception:
            # Fallback to simple importance calculation
            self.parameter_importance = {name: 0.0 for name in parameter_names}
    
    def get_success_rate(self) -> float:
        """Get the success rate of optimization runs."""
        total_runs = self.total_runs_completed + self.total_runs_failed + self.total_runs_cancelled
        if total_runs == 0:
            return 0.0
        return self.total_runs_completed / total_runs
    
    def get_improvement_over_time(self, results: List[OptimizationResult]) -> List[Tuple[datetime, float]]:
        """Get best fitness improvement over time."""
        if not results:
            return []
        
        sorted_results = sorted(results, key=lambda r: r.start_time)
        improvements = []
        best_so_far = float('-inf')
        
        for result in sorted_results:
            if result.fitness and result.fitness > best_so_far:
                best_so_far = result.fitness
                improvements.append((result.start_time, best_so_far))
        
        return improvements
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'optimization_id': self.optimization_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_runs_requested': self.total_runs_requested,
            'total_runs_completed': self.total_runs_completed,
            'total_runs_failed': self.total_runs_failed,
            'total_runs_cancelled': self.total_runs_cancelled,
            'best_result': self.best_result.to_dict() if self.best_result else None,
            'worst_result': self.worst_result.to_dict() if self.worst_result else None,
            'mean_fitness': self.mean_fitness,
            'median_fitness': self.median_fitness,
            'std_fitness': self.std_fitness,
            'total_execution_time': self.total_execution_time,
            'average_execution_time': self.average_execution_time,
            'min_execution_time': self.min_execution_time,
            'max_execution_time': self.max_execution_time,
            'generations_completed': self.generations_completed,
            'convergence_achieved': self.convergence_achieved,
            'convergence_generation': self.convergence_generation,
            'improvement_rate': self.improvement_rate,
            'parameter_importance': self.parameter_importance,
            'success_rate': self.get_success_rate()
        }
    
    def to_json(self) -> str:
        """Convert statistics to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    def __repr__(self) -> str:
        """String representation of optimization statistics."""
        return (f"OptimizationStatistics(id='{self.optimization_id}', "
                f"completed={self.total_runs_completed}, "
                f"success_rate={self.get_success_rate():.2%}, "
                f"best_fitness={self.best_result.fitness if self.best_result else 'N/A'})")