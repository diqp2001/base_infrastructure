"""
Engine configuration for Misbuffet backtesting framework.

This configuration file defines the engine parameters for running backtests.
"""

from datetime import datetime

# Misbuffet Engine Configuration
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "backtesting",
    "execution_mode": "synchronous",
    
    # Backtest parameters
    "start_date": datetime(2015, 1, 1),
    "end_date": datetime(2017, 1, 1),
    "initial_capital": 100_000,
    "benchmark": "SPY",
    
    # Data resolution and feeds
    "resolution": "daily",
    "data_feeds": ["file_system"],
    "market": "USA",
    
    # Risk management
    "enable_risk_management": True,
    "max_portfolio_leverage": 2.0,
    "max_position_size": 0.20,  # 20% max per position
    
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
    
    # Performance and reporting
    "benchmark_symbol": "SPY",
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./results",
    
    # Advanced settings
    "warm_up_period": 30,  # Days
    "market_on_open_orders": True,
    "market_on_close_orders": True,
    "fill_forward_missing_data": True,
}