"""
Engine configuration for Misbuffet backtesting framework in test_base_project.

This configuration file defines the engine parameters for running hybrid backtests
combining spatiotemporal ML models with factor-based momentum strategies.
"""

from datetime import datetime

# Misbuffet Engine Configuration for BaseProject
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "backtesting",
    "execution_mode": "synchronous",
    "algorithm_type": "hybrid_ml_factor",
    
    # Backtest parameters - Extended timeframe for ML training
    "start_date": datetime(2020, 1, 1),
    "end_date": datetime(2023, 12, 31),
    "initial_capital": 100_000,
    "benchmark": "SPY",
    
    # Data resolution and feeds
    "resolution": "daily",
    "data_feeds": ["factor_system", "file_system", "database"],
    "market": "USA",
    "universe": ["AAPL", "MSFT", "AMZN", "GOOGL"],
    
    # Backtesting time interval configuration
    "backtest_interval": "daily",
    "custom_interval_days": None,
    "custom_interval_hours": None,
    "custom_interval_minutes": None,
    
    # ML Model Configuration
    "ml_models": {
        "tft_enabled": True,
        "mlp_enabled": True,
        "ensemble_mode": "both",  # "tft", "mlp", "both"
        "model_seeds": [42, 123, 456],  # For ensemble diversity
        "retrain_frequency": "weekly",
        "lookback_window": 60,
        "prediction_horizon": 5
    },
    
    # Factor System Configuration
    "factor_system": {
        "enabled": True,
        "populate_on_start": True,
        "factor_groups": ['price', 'momentum', 'technical', 'engineered'],
        "update_frequency": "daily",
        "historical_range_days": 1000
    },
    
    # Strategy Configuration
    "strategy": {
        "momentum_weight": 0.6,
        "ml_signal_weight": 0.4,
        "rebalance_frequency": "weekly",
        "portfolio_optimizer": "black_litterman",
        "risk_adjustment": True
    },
    
    # Risk management - Enhanced for ML strategies
    "enable_risk_management": True,
    "max_portfolio_leverage": 1.5,
    "max_position_size": 0.25,  # 25% max per position
    "volatility_scaling": True,
    "drawdown_limit": 0.15,  # 15% max drawdown
    
    # Transaction costs
    "enable_transaction_costs": True,
    "commission_per_trade": 1.0,
    "slippage_model": "constant",
    "slippage_basis_points": 5,
    
    # Handlers configuration
    "data_handler": "HybridFactorDataHandler",
    "execution_handler": "MLAwareExecutionHandler", 
    "portfolio_handler": "FactorPortfolioHandler",
    "results_handler": "EnhancedResultsHandler",
    
    # Performance and reporting
    "benchmark_symbol": "SPY",
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./results",
    "detailed_metrics": True,
    
    # Advanced settings
    "warm_up_period": 60,  # Days - longer for ML model training
    "market_on_open_orders": True,
    "market_on_close_orders": True,
    "fill_forward_missing_data": True,
    
    # Web Interface Settings
    "web_interface_enabled": True,
    "progress_reporting": True,
    "real_time_updates": True
}