"""
SQLAlchemy models for backtest tracking persistence.

Database schema definitions for storing backtest configurations,
results, datasets, and related metadata.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import BLOB
from datetime import datetime

Base = declarative_base()


class BacktestExperimentModel(Base):
    """Experiment grouping for related backtest runs."""
    
    __tablename__ = 'backtest_experiments'
    
    id = Column(Integer, primary_key=True)
    experiment_id = Column(String(36), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), default='system')
    tags = Column(JSON)
    
    # Relationships
    configs = relationship("BacktestConfigModel", back_populates="experiment")
    results = relationship("BacktestResultModel", back_populates="experiment")


class BacktestConfigModel(Base):
    """Backtest configuration storage."""
    
    __tablename__ = 'backtest_configs'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(String(36), unique=True, nullable=False)
    experiment_id = Column(String(36), ForeignKey('backtest_experiments.experiment_id'))
    
    # Basic info
    run_name = Column(String(255))
    algorithm_name = Column(String(100), nullable=False)
    algorithm_version = Column(String(20), default='1.0')
    
    # Strategy configuration (JSON)
    strategy_params = Column(JSON)
    
    # Time configuration
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    benchmark_period = Column(String(10))
    
    # Universe and filters (JSON)
    universe = Column(JSON)  # List of symbols
    universe_filter = Column(JSON)
    
    # Portfolio settings
    initial_capital = Column(String(20))  # Store as string to preserve precision
    position_sizing = Column(String(50), default='equal_weight')
    max_positions = Column(Integer, default=20)
    
    # Risk settings
    max_position_size = Column(String(10))  # Decimal as string
    stop_loss = Column(String(10))
    take_profit = Column(String(10))
    var_limit = Column(String(10))
    
    # Trading settings
    commission_rate = Column(String(10))
    slippage_model = Column(String(50), default='linear')
    market_impact_factor = Column(String(10))
    
    # Data configuration
    data_frequency = Column(String(20), default='daily')
    lookback_window = Column(Integer, default=252)
    warmup_period = Column(Integer, default=50)
    
    # Features (JSON)
    factors = Column(JSON)
    feature_selection = Column(JSON)
    
    # ML configuration (JSON)
    model_type = Column(String(100))
    model_params = Column(JSON)
    training_frequency = Column(String(20))
    
    # Environment
    random_seed = Column(Integer, default=42)
    parallel_processing = Column(Boolean, default=True)
    num_cores = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), default='system')
    tags = Column(JSON)
    description = Column(Text)
    
    # Relationships
    experiment = relationship("BacktestExperimentModel", back_populates="configs")
    results = relationship("BacktestResultModel", back_populates="config")


class BacktestResultModel(Base):
    """Backtest execution results and performance metrics."""
    
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    result_id = Column(String(36), unique=True, nullable=False)
    config_id = Column(String(36), ForeignKey('backtest_configs.config_id'))
    experiment_id = Column(String(36), ForeignKey('backtest_experiments.experiment_id'))
    
    # Basic info
    run_name = Column(String(255))
    
    # Execution metadata
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    execution_duration_seconds = Column(Float)
    status = Column(String(20), default='completed')  # running, completed, failed, cancelled
    error_message = Column(Text)
    
    # Performance metrics (stored as strings for precision)
    total_return = Column(String(20))
    total_return_pct = Column(String(20))
    annualized_return = Column(String(20))
    volatility = Column(String(20))
    sharpe_ratio = Column(String(20))
    sortino_ratio = Column(String(20))
    max_drawdown = Column(String(20))
    max_drawdown_pct = Column(String(20))
    
    # Trade statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(String(10))
    profit_factor = Column(String(20))
    
    # Risk metrics
    var_95 = Column(String(20))
    cvar_95 = Column(String(20))
    calmar_ratio = Column(String(20))
    
    # Benchmark comparison
    benchmark_return = Column(String(20))
    alpha = Column(String(20))
    beta = Column(String(20))
    information_ratio = Column(String(20))
    
    # Complex data (JSON)
    factor_exposures = Column(JSON)
    sector_attribution = Column(JSON)
    monthly_returns = Column(JSON)
    risk_metrics = Column(JSON)
    model_metrics = Column(JSON)
    feature_importance = Column(JSON)
    
    # System info
    system_info = Column(JSON)
    resource_usage = Column(JSON)
    
    # User metadata
    created_by = Column(String(255), default='system')
    tags = Column(JSON)
    notes = Column(Text)
    
    # Relationships
    experiment = relationship("BacktestExperimentModel", back_populates="results")
    config = relationship("BacktestConfigModel", back_populates="results")
    trades = relationship("TradeRecordModel", back_populates="result")
    equity_curve_points = relationship("EquityCurvePointModel", back_populates="result")


class TradeRecordModel(Base):
    """Individual trade records."""
    
    __tablename__ = 'trade_records'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(String(36), unique=True, nullable=False)
    result_id = Column(String(36), ForeignKey('backtest_results.result_id'))
    
    # Trade details
    symbol = Column(String(20), nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    side = Column(String(10), nullable=False)  # 'long' or 'short'
    quantity = Column(Integer, nullable=False)
    
    # Prices (stored as strings for precision)
    entry_price = Column(String(20), nullable=False)
    exit_price = Column(String(20))
    
    # Performance
    pnl = Column(String(20))
    pnl_pct = Column(String(10))
    
    # Costs
    entry_commission = Column(String(20), default='0')
    exit_commission = Column(String(20), default='0')
    slippage = Column(String(20), default='0')
    
    # Signals and metadata
    entry_signal = Column(String(100))
    exit_signal = Column(String(100))
    tags = Column(JSON)
    
    # Relationship
    result = relationship("BacktestResultModel", back_populates="trades")


class EquityCurvePointModel(Base):
    """Time series points for equity curve data."""
    
    __tablename__ = 'equity_curve_points'
    
    id = Column(Integer, primary_key=True)
    result_id = Column(String(36), ForeignKey('backtest_results.result_id'))
    
    # Time series data
    timestamp = Column(DateTime, nullable=False)
    portfolio_value = Column(String(20), nullable=False)
    daily_return = Column(String(20))
    drawdown = Column(String(20))
    
    # Position data
    gross_exposure = Column(String(20))
    net_exposure = Column(String(20))
    num_positions = Column(Integer)
    
    # Relationship
    result = relationship("BacktestResultModel", back_populates="equity_curve_points")


class BacktestDatasetModel(Base):
    """Dataset definitions and metadata."""
    
    __tablename__ = 'backtest_datasets'
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(36), unique=True, nullable=False)
    
    # Basic info
    name = Column(String(255), nullable=False)
    version = Column(String(20), default='1.0')
    description = Column(Text)
    
    # Data characteristics
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    frequency = Column(String(20), default='daily')
    timezone = Column(String(50), default='UTC')
    
    # Universe (JSON)
    symbols = Column(JSON)
    universe_filter = Column(JSON)
    
    # Data sources (JSON)
    primary_source = Column(JSON)
    auxiliary_sources = Column(JSON)
    
    # Schema (JSON)
    fields = Column(JSON)
    
    # Feature engineering (JSON)
    feature_pipeline = Column(JSON)
    features_generated = Column(JSON)
    
    # Quality metrics
    quality_report = Column(JSON)
    
    # Configuration
    benchmark_symbol = Column(String(20))
    risk_free_rate_source = Column(String(100))
    factor_sources = Column(JSON)
    
    # Storage
    storage_location = Column(String(500))
    cache_enabled = Column(Boolean, default=True)
    compression = Column(String(20), default='parquet')
    
    # Statistics
    total_data_points = Column(Integer, default=0)
    memory_usage_mb = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), default='system')
    last_updated = Column(DateTime, default=datetime.utcnow)
    tags = Column(JSON)


class BacktestArtifactModel(Base):
    """File artifacts associated with backtest runs."""
    
    __tablename__ = 'backtest_artifacts'
    
    id = Column(Integer, primary_key=True)
    artifact_id = Column(String(36), unique=True, nullable=False)
    result_id = Column(String(36), ForeignKey('backtest_results.result_id'))
    
    # Artifact info
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(50))  # plot, report, data, model, etc.
    file_format = Column(String(20))    # png, pdf, csv, pickle, etc.
    
    # Storage
    file_path = Column(String(1000))
    file_size_bytes = Column(Integer)
    
    # Content (for small artifacts)
    content_data = Column(BLOB)  # Binary data
    content_text = Column(Text)  # Text data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    tags = Column(JSON)


class BacktestComparisonModel(Base):
    """Comparison analysis between multiple backtest results."""
    
    __tablename__ = 'backtest_comparisons'
    
    id = Column(Integer, primary_key=True)
    comparison_id = Column(String(36), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    
    # Results being compared (JSON array of result_ids)
    result_ids = Column(JSON)
    
    # Comparative analysis (JSON)
    relative_performance = Column(JSON)
    correlation_matrix = Column(JSON)
    significance_tests = Column(JSON)
    risk_adjusted_rankings = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), default='system')
    description = Column(Text)
    tags = Column(JSON)


class BacktestMetricModel(Base):
    """Time series metrics for detailed performance tracking."""
    
    __tablename__ = 'backtest_metrics'
    
    id = Column(Integer, primary_key=True)
    result_id = Column(String(36), ForeignKey('backtest_results.result_id'))
    
    # Metric identification
    metric_name = Column(String(100), nullable=False)
    metric_category = Column(String(50))  # performance, risk, trade, etc.
    
    # Time series data
    timestamp = Column(DateTime)
    value = Column(String(20))  # Store as string for precision
    
    # Additional context
    symbol = Column(String(20))  # If metric is symbol-specific
    meta_data = Column("metadata", JSON) 


class BacktestParameterModel(Base):
    """Parameter tracking for experiment management."""
    
    __tablename__ = 'backtest_parameters'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(String(36), ForeignKey('backtest_configs.config_id'))
    
    # Parameter info
    parameter_name = Column(String(100), nullable=False)
    parameter_value = Column(String(500))
    parameter_type = Column(String(50))  # string, int, float, bool, json
    
    # Metadata
    description = Column(String(500))
    is_hyperparameter = Column(Boolean, default=False)


class BacktestTagModel(Base):
    """Tag management for organizing experiments and results."""
    
    __tablename__ = 'backtest_tags'
    
    id = Column(Integer, primary_key=True)
    tag_name = Column(String(100), nullable=False)
    tag_value = Column(String(500))
    
    # Entity association
    entity_type = Column(String(50), nullable=False)  # experiment, config, result, dataset
    entity_id = Column(String(36), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), default='system')


# Create indexes for better query performance
from sqlalchemy import Index

# Performance-critical indexes
Index('idx_config_experiment', BacktestConfigModel.experiment_id)
Index('idx_result_config', BacktestResultModel.config_id)
Index('idx_result_experiment', BacktestResultModel.experiment_id)
Index('idx_result_status', BacktestResultModel.status)
Index('idx_trade_result', TradeRecordModel.result_id)
Index('idx_equity_result', EquityCurvePointModel.result_id)
Index('idx_equity_timestamp', EquityCurvePointModel.timestamp)
Index('idx_metric_result', BacktestMetricModel.result_id)
Index('idx_metric_name', BacktestMetricModel.metric_name)
Index('idx_parameter_config', BacktestParameterModel.config_id)
Index('idx_tag_entity', BacktestTagModel.entity_type, BacktestTagModel.entity_id)
Index('idx_tag_name', BacktestTagModel.tag_name)