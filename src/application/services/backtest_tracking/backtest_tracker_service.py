"""
Backtest tracking service for integration with test managers.

High-level service providing MLflow-style experiment tracking
functionality for backtest configurations and results.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import logging
import json
from pathlib import Path

from src.domain.backtest.config import BacktestConfig
from src.domain.backtest.result import BacktestResult, PerformanceMetrics, TradeRecord, EquityCurve
from src.domain.backtest.dataset import BacktestDataset
from src.infrastructure.backtest.repositories import BacktestRepository

logger = logging.getLogger(__name__)


class BacktestTrackerService:
    """
    High-level service for tracking backtest experiments and results.
    
    Provides MLflow-style experiment management with custom domain models
    and infrastructure implementations.
    """
    
    def __init__(self, database_url: str = None):
        """Initialize the tracker service."""
        if database_url is None:
            # Default to SQLite database in project root
            project_root = Path(__file__).parents[4]
            database_url = f"sqlite:///{project_root}/backtest_tracking.db"
        
        self.repository = BacktestRepository(database_url)
        logger.info(f"BacktestTrackerService initialized with database: {database_url}")
    
    # Experiment Management
    
    def create_experiment(self, name: str, description: str = "", tags: Dict[str, str] = None) -> str:
        """Create a new experiment for organizing related backtest runs."""
        experiment_id = self.repository.create_experiment(
            name=name,
            description=description,
            tags=tags or {}
        )
        logger.info(f"Created experiment '{name}' with ID: {experiment_id}")
        return experiment_id
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details by ID."""
        return self.repository.get_experiment(experiment_id)
    
    def list_experiments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all experiments with basic metadata."""
        return self.repository.list_experiments(limit=limit)
    
    # Run Management
    
    def start_run(self, experiment_name: str, run_name: str = None, 
                  config: Dict[str, Any] = None) -> str:
        """
        Start a new backtest run within an experiment.
        
        Args:
            experiment_name: Name of the experiment (will be created if doesn't exist)
            run_name: Optional name for this specific run
            config: Configuration dictionary for the backtest
            
        Returns:
            run_id (config_id) for tracking this run
        """
        # Create experiment if it doesn't exist
        experiments = self.list_experiments()
        experiment_exists = any(exp['name'] == experiment_name for exp in experiments)
        
        if not experiment_exists:
            self.create_experiment(
                name=experiment_name,
                description=f"Automatically created for experiment: {experiment_name}"
            )
        
        # Create configuration
        backtest_config = BacktestConfig(
            config_id=None,  # Will be auto-generated
            experiment_name=experiment_name,
            run_name=run_name,
            created_at=datetime.utcnow()
        )
        
        # Update configuration with provided parameters
        if config:
            self._update_config_from_dict(backtest_config, config)
        
        # Validate and store configuration
        errors = backtest_config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        
        config_id = self.repository.store_config(backtest_config)
        logger.info(f"Started run '{run_name}' in experiment '{experiment_name}' with config ID: {config_id}")
        return config_id
    
    def _update_config_from_dict(self, config: BacktestConfig, config_dict: Dict[str, Any]):
        """Update BacktestConfig object from dictionary."""
        # Map common configuration parameters
        mapping = {
            'algorithm_name': 'algorithm',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'initial_capital': 'initial_capital',
            'universe': 'universe',
            'lookback_window': 'lookback',
            'commission_rate': 'commission_rate',
            'random_seed': 'random_seed'
        }
        
        for attr_name, dict_key in mapping.items():
            if dict_key in config_dict:
                value = config_dict[dict_key]
                
                # Handle type conversions
                if attr_name in ['initial_capital', 'commission_rate'] and value is not None:
                    value = Decimal(str(value))
                elif attr_name in ['start_date', 'end_date'] and isinstance(value, str):
                    value = datetime.fromisoformat(value) if value else None
                
                setattr(config, attr_name, value)
        
        # Handle strategy parameters
        if 'strategy_params' in config_dict:
            config.strategy_params = config_dict['strategy_params']
        
        # Handle universe as list
        if 'symbols' in config_dict:
            config.universe = config_dict['symbols']
    
    def end_run(self, run_id: str, status: str = "completed", error_message: str = None):
        """Mark a run as completed and update its status."""
        result = self.repository.get_result(run_id)
        if result:
            result.status = status
            result.end_time = datetime.utcnow()
            if error_message:
                result.error_message = error_message
            
            # Calculate execution duration
            if result.start_time:
                duration = result.end_time - result.start_time
                result.execution_duration_seconds = duration.total_seconds()
            
            self.repository.store_result(result)
        logger.info(f"Ended run {run_id} with status: {status}")
    
    # Logging Methods (MLflow-style)
    
    def log_parameters(self, run_id: str, params: Dict[str, Any]):
        """Log parameters for a run."""
        config = self.repository.get_config(run_id)
        if config:
            # Update strategy parameters
            if config.strategy_params is None:
                config.strategy_params = {}
            config.strategy_params.update(params)
            self.repository.store_config(config)
        logger.debug(f"Logged parameters for run {run_id}: {list(params.keys())}")
    
    def log_metrics(self, run_id: str, metrics: Dict[str, float]):
        """Log performance metrics for a run."""
        # Create or update result with metrics
        result = self.repository.get_result(run_id)
        if not result:
            # Create new result if it doesn't exist
            config = self.repository.get_config(run_id)
            if config:
                result = BacktestResult(
                    result_id=run_id,
                    config_id=run_id,
                    experiment_name=config.experiment_name,
                    run_name=config.run_name,
                    start_time=datetime.utcnow()
                )
        
        if result:
            # Convert metrics to PerformanceMetrics object
            if not result.performance_metrics:
                result.performance_metrics = PerformanceMetrics(
                    total_return=Decimal("0"),
                    total_return_pct=Decimal("0"),
                    annualized_return=Decimal("0"),
                    volatility=Decimal("0"),
                    sharpe_ratio=Decimal("0"),
                    sortino_ratio=Decimal("0"),
                    max_drawdown=Decimal("0"),
                    max_drawdown_pct=Decimal("0"),
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=Decimal("0"),
                    profit_factor=Decimal("0"),
                    average_trade=Decimal("0"),
                    average_win=Decimal("0"),
                    average_loss=Decimal("0"),
                    largest_win=Decimal("0"),
                    largest_loss=Decimal("0"),
                    calmar_ratio=Decimal("0"),
                    var_95=Decimal("0"),
                    cvar_95=Decimal("0")
                )
            
            # Update metrics
            pm = result.performance_metrics
            for metric_name, value in metrics.items():
                if hasattr(pm, metric_name):
                    if isinstance(value, (int, float)):
                        setattr(pm, metric_name, Decimal(str(value)))
                    else:
                        setattr(pm, metric_name, value)
            
            self.repository.store_result(result)
        
        logger.debug(f"Logged metrics for run {run_id}: {list(metrics.keys())}")
    
    def log_trades(self, run_id: str, trades: List[Dict[str, Any]]):
        """Log trade records for a run."""
        result = self.repository.get_result(run_id)
        if not result:
            # Create new result if needed
            config = self.repository.get_config(run_id)
            if config:
                result = BacktestResult(
                    result_id=run_id,
                    config_id=run_id,
                    experiment_name=config.experiment_name,
                    run_name=config.run_name,
                    start_time=datetime.utcnow()
                )
        
        if result:
            # Convert trade dictionaries to TradeRecord objects
            for trade_dict in trades:
                trade = TradeRecord(
                    trade_id=trade_dict.get('trade_id'),
                    symbol=trade_dict['symbol'],
                    entry_time=trade_dict['entry_time'],
                    exit_time=trade_dict.get('exit_time'),
                    side=trade_dict['side'],
                    quantity=trade_dict['quantity'],
                    entry_price=Decimal(str(trade_dict['entry_price'])),
                    exit_price=Decimal(str(trade_dict['exit_price'])) if trade_dict.get('exit_price') else None,
                    pnl=Decimal(str(trade_dict['pnl'])) if trade_dict.get('pnl') else None,
                    pnl_pct=Decimal(str(trade_dict['pnl_pct'])) if trade_dict.get('pnl_pct') else None,
                    entry_commission=Decimal(str(trade_dict.get('entry_commission', 0))),
                    exit_commission=Decimal(str(trade_dict.get('exit_commission', 0))),
                    slippage=Decimal(str(trade_dict.get('slippage', 0))),
                    entry_signal=trade_dict.get('entry_signal', ''),
                    exit_signal=trade_dict.get('exit_signal', ''),
                    tags=trade_dict.get('tags', {})
                )
                result.add_trade(trade)
            
            self.repository.store_result(result)
        
        logger.debug(f"Logged {len(trades)} trades for run {run_id}")
    
    def log_equity_curve(self, run_id: str, timestamps: List[datetime], 
                        portfolio_values: List[float], returns: List[float] = None, 
                        drawdowns: List[float] = None):
        """Log equity curve data for a run."""
        result = self.repository.get_result(run_id)
        if not result:
            config = self.repository.get_config(run_id)
            if config:
                result = BacktestResult(
                    result_id=run_id,
                    config_id=run_id,
                    experiment_name=config.experiment_name,
                    run_name=config.run_name,
                    start_time=datetime.utcnow()
                )
        
        if result:
            equity_curve = EquityCurve(
                timestamps=timestamps,
                portfolio_values=[Decimal(str(pv)) for pv in portfolio_values],
                daily_returns=[Decimal(str(r)) for r in (returns or [0] * len(timestamps))],
                drawdowns=[Decimal(str(dd)) for dd in (drawdowns or [0] * len(timestamps))]
            )
            result.equity_curve = equity_curve
            self.repository.store_result(result)
        
        logger.debug(f"Logged equity curve with {len(timestamps)} data points for run {run_id}")
    
    def set_tags(self, run_id: str, tags: Dict[str, str]):
        """Set tags for a run."""
        result = self.repository.get_result(run_id)
        if result:
            result.tags.update(tags)
            self.repository.store_result(result)
        
        config = self.repository.get_config(run_id)
        if config:
            if config.tags is None:
                config.tags = {}
            config.tags.update(tags)
            self.repository.store_config(config)
        
        logger.debug(f"Set tags for run {run_id}: {list(tags.keys())}")
    
    # Query Methods
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a run."""
        result = self.repository.get_result(run_id)
        config = self.repository.get_config(run_id)
        
        if not result and not config:
            return None
        
        run_data = {
            'run_id': run_id,
            'config': config.to_dict() if config else {},
            'result': result.to_summary_dict() if result else {},
            'status': result.status if result else 'not_started'
        }
        
        if result and result.performance_metrics:
            run_data['metrics'] = result.performance_metrics.to_dict()
        
        return run_data
    
    def list_runs(self, experiment_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List runs, optionally filtered by experiment."""
        return self.repository.list_results(experiment_name=experiment_name, limit=limit)
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple runs and return comparative analysis."""
        return self.repository.compare_results(run_ids)
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data."""
        success = self.repository.delete_result(run_id)
        if success:
            logger.info(f"Deleted run {run_id}")
        return success
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all tracked runs."""
        return self.repository.get_result_summary_stats()
    
    # Integration helper methods
    
    def create_run_from_manager_config(self, experiment_name: str, manager_config: Dict[str, Any]) -> str:
        """Create a run from a test manager configuration."""
        # Generate unique run name with microseconds to avoid collisions
        current_time = datetime.now()
        run_name = manager_config.get('run_name', f"Run_{current_time.strftime('%Y%m%d_%H%M%S_%f')}")
        
        # Convert manager config to backtest config format
        backtest_config = {
            'algorithm': manager_config.get('algorithm', 'momentum'),
            'lookback': manager_config.get('lookback', 20),
            'initial_capital': manager_config.get('initial_capital', 100000),
            'start_date': manager_config.get('start_date'),
            'end_date': manager_config.get('end_date'),
            'universe': manager_config.get('universe', ['AAPL', 'MSFT', 'GOOGL', 'AMZN']),
            'commission_rate': manager_config.get('commission_rate', 0.001),
            'random_seed': manager_config.get('random_seed', 42),
            'strategy_params': manager_config.get('strategy_params', {})
        }
        
        return self.start_run(experiment_name, run_name, backtest_config)
    
    def store_manager_results(self, run_id: str, manager_results: Dict[str, Any]):
        """Store results from a test manager execution."""
        # Extract metrics from manager results
        metrics = {}
        if 'total_return' in manager_results:
            metrics['total_return_pct'] = manager_results['total_return']
        if 'sharpe_ratio' in manager_results:
            metrics['sharpe_ratio'] = manager_results['sharpe_ratio']
        if 'max_drawdown' in manager_results:
            metrics['max_drawdown_pct'] = manager_results['max_drawdown']
        if 'volatility' in manager_results:
            metrics['volatility'] = manager_results['volatility']
        
        # Log metrics
        if metrics:
            self.log_metrics(run_id, metrics)
        
        # Log trades if available
        if 'trades' in manager_results:
            self.log_trades(run_id, manager_results['trades'])
        
        # Log equity curve if available
        if 'equity_curve' in manager_results:
            ec = manager_results['equity_curve']
            if 'timestamps' in ec and 'values' in ec:
                self.log_equity_curve(
                    run_id=run_id,
                    timestamps=ec['timestamps'],
                    portfolio_values=ec['values'],
                    returns=ec.get('returns'),
                    drawdowns=ec.get('drawdowns')
                )
        
        # Set additional tags
        tags = {
            'execution_date': datetime.now().strftime('%Y-%m-%d'),
            'data_source': manager_results.get('data_source', 'unknown')
        }
        self.set_tags(run_id, tags)
        
        logger.info(f"Stored manager results for run {run_id}")


# Global tracker instance for easy access
_global_tracker = None

def get_tracker(database_url: str = None) -> BacktestTrackerService:
    """Get global tracker instance (singleton pattern)."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = BacktestTrackerService(database_url)
    return _global_tracker