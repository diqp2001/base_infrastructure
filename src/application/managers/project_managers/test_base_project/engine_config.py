"""
Engine configuration for test_base_project Misbuffet backtesting framework.

This configuration file defines the engine parameters for running backtests
with the hybrid spatiotemporal momentum system.
"""

from datetime import datetime

# Misbuffet Engine Configuration for test_base_project
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "backtesting",
    "execution_mode": "synchronous",
    
    # Backtest parameters - optimized for ML system
    "start_date": datetime(2018, 1, 1),  # Recent data for ML training
    "end_date": datetime(2019, 1, 1),
    "initial_capital": 100_000.0,
    "benchmark": "SPY",
    
    # Data resolution and feeds
    "resolution": "daily",
    "data_feeds": ["file_system", "factor_system"],  # Include our factor system
    "market": "USA",
    
    # Backtesting time interval configuration
    "backtest_interval": "daily",
    "custom_interval_days": None,
    "custom_interval_hours": None,
    "custom_interval_minutes": None,
    
    # ML-specific settings
    "ml_retraining_frequency": 7,  # Retrain models every 7 days
    "ensemble_prediction_method": "weighted_average",
    "factor_lookback_period": 252,  # 1 year of factor history
    
    # Risk management - enhanced for ML system
    "enable_risk_management": True,
    "max_portfolio_leverage": 2.0,
    "max_position_size": 0.25,  # 25% max per position
    "ml_confidence_threshold": 0.6,  # Minimum ML confidence for trades
    
    # Transaction costs
    "enable_transaction_costs": True,
    "commission_per_trade": 1.0,
    "slippage_model": "constant",
    "slippage_basis_points": 5,
    
    # Handlers configuration
    "data_handler": "FileSystemDataHandler",
    "execution_handler": "BacktestExecutionHandler", 
    "portfolio_handler": "BacktestPortfolioHandler",
    "results_handler": "BacktestResultsHandler",
    
    # Factor system integration
    "factor_data_handler": "TestBaseProjectFactorHandler",
    "enable_factor_features": True,
    "factor_update_frequency": "daily",
    
    # Performance and reporting
    "benchmark_symbol": "SPY",
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./results/test_base_project",
    "enable_ml_performance_metrics": True,
    
    # Advanced settings
    "warm_up_period": 60,  # Days - longer for ML training
    "market_on_open_orders": True,
    "market_on_close_orders": True,
    "fill_forward_missing_data": True,
    
    # Model-specific settings
    "tft_model_settings": {
        "attention_heads": 4,
        "hidden_size": 64,
        "dropout": 0.1
    },
    "mlp_model_settings": {
        "hidden_layers": [128, 64, 32],
        "dropout": 0.2
    },
    "ensemble_weights": {
        "tft": 0.6,
        "mlp": 0.4
    }
}