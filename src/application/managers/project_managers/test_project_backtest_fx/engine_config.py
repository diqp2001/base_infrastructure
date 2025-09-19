"""
Engine configuration for Misbuffet FX backtesting framework.

This configuration file defines the engine parameters for running FX backtests
using the LightGBM + Mean Reversion algorithm.
"""

from datetime import datetime

# Misbuffet Engine Configuration for FX Trading
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "backtesting",
    "execution_mode": "synchronous",
    
    # Backtest parameters - FX data spans 1995-2018
    "start_date": datetime(2000, 1, 1),  # Start after initial years for model warmup
    "end_date": datetime(2015, 1, 1),    # End before recent market changes
    "initial_capital": 100_000,
    "benchmark": "EURUSD",  # Use major FX pair as benchmark
    
    # Data resolution and feeds
    "resolution": "daily",
    "data_feeds": ["file_system"],
    "market": "FX",  # Foreign Exchange market
    
    # Backtesting time interval configuration
    # Supported intervals: daily, weekly, monthly, quarterly, semi_yearly, minutes, seconds
    "backtest_interval": "daily",  # Default to daily for backward compatibility
    "custom_interval_days": None,  # Custom interval in days (overrides backtest_interval if set)
    "custom_interval_hours": None, # Custom interval in hours
    "custom_interval_minutes": None, # Custom interval in minutes
    
    # Examples of different configurations:
    # For weekly backtests: "backtest_interval": "weekly"
    # For monthly backtests: "backtest_interval": "monthly" 
    # For quarterly backtests: "backtest_interval": "quarterly"
    # For custom 3-day interval: "custom_interval_days": 3
    # For hourly backtests: "custom_interval_hours": 1
    # For 30-minute intervals: "custom_interval_minutes": 30
    
    # FX-specific risk management
    "enable_risk_management": True,
    "max_portfolio_leverage": 3.0,  # Higher leverage for FX
    "max_position_size": 0.40,  # 40% max per position (algorithm uses 0.4 per side)
    
    # FX transaction costs (spreads and commissions)
    "enable_transaction_costs": True,
    "commission_per_trade": 0.5,  # Lower commission for FX
    "slippage_model": "spread_based",
    "slippage_basis_points": 2,  # Tighter spreads for major pairs
    
    # Handlers configuration
    "data_handler": "FileSystemDataHandler",
    "execution_handler": "BacktestExecutionHandler",
    "portfolio_handler": "BacktestPortfolioHandler",
    "results_handler": "BacktestResultsHandler",
    
    # Performance and reporting
    "benchmark_symbol": "EURUSD",  # FX benchmark
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./results/fx_backtest",
    
    # Advanced settings for FX
    "warm_up_period": 60,  # Longer warmup period for ML models
    "market_on_open_orders": True,
    "market_on_close_orders": True,
    "fill_forward_missing_data": True,
    
    # FX-specific settings
    "fx_currencies": ["EUR", "GBP", "AUD", "USD", "MXN", "JPY", "CAD"],
    "fx_base_currency": "USD",
    "fx_data_path": "data/fx_data",
}