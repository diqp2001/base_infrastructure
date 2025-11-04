"""
Backtest configuration domain model.

Defines the schema for backtest configurations including strategy parameters,
timeframes, assets, and risk management settings.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4


@dataclass
class BacktestConfig:
    """
    Domain model representing a complete backtest configuration.
    
    This class encapsulates all parameters needed to reproduce a backtest,
    including strategy settings, time ranges, asset selection, and risk parameters.
    """
    
    # Unique identifiers
    config_id: str
    experiment_name: str
    run_name: Optional[str] = None
    
    # Strategy configuration
    algorithm_name: str = "momentum"
    algorithm_version: str = "1.0"
    strategy_params: Dict[str, Any] = None
    
    # Time configuration
    start_date: datetime = None
    end_date: datetime = None
    benchmark_period: Optional[str] = "1Y"
    
    # Asset selection
    universe: List[str] = None  # List of symbols/tickers
    universe_filter: Dict[str, Any] = None  # Market cap, sector filters, etc.
    
    # Portfolio configuration
    initial_capital: Decimal = Decimal("100000.00")
    position_sizing: str = "equal_weight"  # equal_weight, risk_parity, etc.
    max_positions: int = 20
    
    # Risk management
    max_position_size: Decimal = Decimal("0.20")  # 20% max per position
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    var_limit: Optional[Decimal] = None  # Value at Risk limit
    
    # Trading configuration
    commission_rate: Decimal = Decimal("0.001")  # 0.1%
    slippage_model: str = "linear"
    market_impact_factor: Decimal = Decimal("0.0001")
    
    # Data configuration
    data_frequency: str = "daily"  # daily, hourly, minute
    lookback_window: int = 252  # Trading days
    warmup_period: int = 50  # Days for indicators to warm up
    
    # Feature engineering
    factors: List[str] = None  # List of factor names to compute
    feature_selection: Dict[str, Any] = None
    
    # Machine Learning (if applicable)
    model_type: Optional[str] = None
    model_params: Dict[str, Any] = None
    training_frequency: Optional[str] = None  # monthly, quarterly
    
    # Environment settings
    random_seed: int = 42
    parallel_processing: bool = True
    num_cores: Optional[int] = None
    
    # Metadata
    created_at: datetime = None
    created_by: str = "system"
    tags: Dict[str, str] = None
    description: str = ""
    
    def __post_init__(self):
        """Initialize default values and validate configuration."""
        if self.config_id is None:
            self.config_id = str(uuid4())
        
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
        if self.strategy_params is None:
            self.strategy_params = {}
        
        if self.universe is None:
            self.universe = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        
        if self.factors is None:
            self.factors = ["momentum", "mean_reversion", "volatility"]
        
        if self.tags is None:
            self.tags = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'config_id': self.config_id,
            'experiment_name': self.experiment_name,
            'run_name': self.run_name,
            'algorithm_name': self.algorithm_name,
            'algorithm_version': self.algorithm_version,
            'strategy_params': self.strategy_params,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'benchmark_period': self.benchmark_period,
            'universe': self.universe,
            'universe_filter': self.universe_filter,
            'initial_capital': str(self.initial_capital),
            'position_sizing': self.position_sizing,
            'max_positions': self.max_positions,
            'max_position_size': str(self.max_position_size),
            'stop_loss': str(self.stop_loss) if self.stop_loss else None,
            'take_profit': str(self.take_profit) if self.take_profit else None,
            'var_limit': str(self.var_limit) if self.var_limit else None,
            'commission_rate': str(self.commission_rate),
            'slippage_model': self.slippage_model,
            'market_impact_factor': str(self.market_impact_factor),
            'data_frequency': self.data_frequency,
            'lookback_window': self.lookback_window,
            'warmup_period': self.warmup_period,
            'factors': self.factors,
            'feature_selection': self.feature_selection,
            'model_type': self.model_type,
            'model_params': self.model_params,
            'training_frequency': self.training_frequency,
            'random_seed': self.random_seed,
            'parallel_processing': self.parallel_processing,
            'num_cores': self.num_cores,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'tags': self.tags,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestConfig':
        """Create configuration from dictionary."""
        # Convert string dates back to datetime objects
        if data.get('start_date'):
            data['start_date'] = datetime.fromisoformat(data['start_date'])
        if data.get('end_date'):
            data['end_date'] = datetime.fromisoformat(data['end_date'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Convert string decimals back to Decimal objects
        decimal_fields = ['initial_capital', 'max_position_size', 'stop_loss', 
                         'take_profit', 'var_limit', 'commission_rate', 'market_impact_factor']
        for field in decimal_fields:
            if data.get(field):
                data[field] = Decimal(str(data[field]))
        
        return cls(**data)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.experiment_name:
            errors.append("experiment_name is required")
        
        if not self.algorithm_name:
            errors.append("algorithm_name is required")
        
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
        
        if self.max_positions <= 0:
            errors.append("max_positions must be positive")
        
        if not (0 < self.max_position_size <= 1):
            errors.append("max_position_size must be between 0 and 1")
        
        if self.commission_rate < 0:
            errors.append("commission_rate cannot be negative")
        
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors.append("start_date must be before end_date")
        
        if not self.universe or len(self.universe) == 0:
            errors.append("universe must contain at least one symbol")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


@dataclass 
class BacktestEnvironment:
    """
    Domain model for backtest execution environment settings.
    
    Contains system-level configuration for running backtests.
    """
    
    environment_id: str
    name: str
    description: str = ""
    
    # System configuration
    python_version: str = "3.11"
    dependencies: Dict[str, str] = None  # package: version
    
    # Data sources
    data_providers: List[str] = None  # List of data provider names
    data_cache_size: int = 1000  # MB
    
    # Compute resources  
    max_memory_mb: int = 4096
    max_cpu_cores: int = 4
    gpu_enabled: bool = False
    
    # Storage
    results_storage_path: str = "./backtest_results"
    temp_storage_path: str = "./temp"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = {
                "pandas": "2.0+",
                "numpy": "1.24+", 
                "matplotlib": "3.7+",
                "scikit-learn": "1.3+"
            }
        
        if self.data_providers is None:
            self.data_providers = ["yahoo", "alpha_vantage", "local_csv"]