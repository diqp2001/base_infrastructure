"""
Engine configuration for Misbuffet live trading framework.

This configuration file defines the engine parameters for running live trading
with Interactive Brokers.
"""

from datetime import datetime

# Misbuffet Engine Configuration for Live Trading
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "live_trading",
    "execution_mode": "asynchronous",
    "brokerage": "interactive_brokers",
    
    # Live trading parameters
    "live_mode": True,
    "paper_trading": True,  # Set to False for real money
    "initial_capital": 100_000,
    "benchmark": "SPY",
    
    # Data resolution and feeds
    "resolution": "second",  # Higher resolution for live trading
    "data_feeds": ["interactive_brokers", "file_system"],  # Primary + backup
    "market": "USA",
    
    # Interactive Brokers specific settings
    "ib_host": "127.0.0.1",
    "ib_port": 7497,  # Paper trading port
    "ib_client_id": 1,
    "ib_timeout": 60,
    "ib_enable_logging": True,
    
    # Risk management
    "enable_risk_management": True,
    "max_portfolio_leverage": 2.0,
    "max_position_size": 0.20,  # 20% max per position
    "max_orders_per_second": 10,
    "order_timeout_seconds": 30,
    
    # Transaction costs (live trading fees)
    "enable_transaction_costs": True,
    "commission_per_share": 0.005,  # IB commission structure
    "minimum_commission": 1.0,
    "slippage_model": "market_impact",
    "slippage_basis_points": 2,  # Lower for live trading
    
    # Handlers configuration for live trading
    "data_handler": "InteractiveBrokersDataHandler",
    "execution_handler": "LiveExecutionHandler", 
    "portfolio_handler": "LivePortfolioHandler",
    "results_handler": "LiveResultsHandler",
    "brokerage_handler": "InteractiveBrokersBrokerage",
    
    # Performance and reporting
    "benchmark_symbol": "SPY",
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./live_results",
    "real_time_charts": True,
    
    # Live trading specific settings
    "market_hours_only": True,
    "pre_market_trading": False,
    "after_hours_trading": False,
    "extended_market_hours": False,
    
    # Data validation and error handling
    "validate_data": True,
    "max_data_age_seconds": 30,
    "enable_heartbeat": True,
    "heartbeat_interval_seconds": 60,
    
    # Connection management
    "auto_reconnect": True,
    "max_reconnect_attempts": 5,
    "reconnect_delay_seconds": 10,
    
    # Warm-up and initialization
    "warm_up_period": 5,  # Shorter for live trading
    "initialization_timeout_seconds": 120,
}