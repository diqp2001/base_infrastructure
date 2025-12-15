"""
Engine configuration for Market Making Project Misbuffet framework.

This configuration file defines the engine parameters for running backtests
and live trading with the derivatives market making system.
"""

from datetime import datetime

# Misbuffet Engine Configuration for Market Making Project
MISBUFFET_ENGINE_CONFIG = {
    # Engine type and mode
    "engine_type": "backtesting",
    "execution_mode": "synchronous",
    
    # Backtest parameters - optimized for market making
    "start_date": datetime(2020, 1, 1),  # Recent data for derivatives
    "end_date": datetime(2023, 1, 1),
    "initial_capital": 1_000_000.0,
    "benchmark": "SPY",
    
    # Data resolution and feeds
    "resolution": "minute",  # Higher frequency for market making
    "data_feeds": ["interactive_brokers", "file_system"],
    "market": "USA",
    
    # Market making specific timing
    "backtest_interval": "minute",  # Frequent rebalancing
    "custom_interval_days": None,
    "custom_interval_hours": None,
    "custom_interval_minutes": 5,  # 5-minute cycles
    
    # Market making specific settings
    "quote_update_frequency": 1,  # Update quotes every minute
    "inventory_rebalancing_frequency": 60,  # Rebalance every hour
    "pricing_model_update_frequency": 1440,  # Daily pricing model updates
    
    # Risk management - critical for market making
    "enable_risk_management": True,
    "max_portfolio_leverage": 1.5,
    "max_position_size": 0.15,  # 15% max per position
    "max_sector_concentration": 0.30,  # 30% max per sector
    "inventory_limit_per_instrument": 0.05,  # 5% max inventory
    
    # Market making risk controls
    "enable_inventory_management": True,
    "target_inventory": 0.0,  # Neutral inventory target
    "max_inventory_deviation": 0.10,
    "stop_loss_threshold": 0.02,
    "profit_taking_threshold": 0.05,
    
    # Transaction costs - market making friendly
    "enable_transaction_costs": True,
    "commission_per_trade": 0.5,  # Lower for market makers
    "slippage_model": "linear",
    "slippage_basis_points": 2,  # Tighter spreads
    "market_making_rebates": 0.1,  # Maker rebates
    
    # Handlers configuration
    "data_handler": "InteractiveBrokersDataHandler",
    "execution_handler": "MarketMakingExecutionHandler",
    "portfolio_handler": "MarketMakingPortfolioHandler",
    "results_handler": "MarketMakingResultsHandler",
    
    # Derivatives pricing integration
    "pricing_handler": "DerivativesPricingHandler",
    "volatility_handler": "VolatilitySurfaceHandler",
    "curve_handler": "YieldCurveHandler",
    
    # Asset class specific settings
    "supported_asset_classes": ["equity", "fixed_income", "commodity"],
    "default_asset_class": "equity",
    
    # Derivatives specific
    "options_pricing": {
        "black_scholes_enabled": True,
        "binomial_tree_steps": 100,
        "monte_carlo_paths": 10000,
        "implied_vol_enabled": True
    },
    "futures_pricing": {
        "cost_of_carry_enabled": True,
        "storage_cost_enabled": True,
        "convenience_yield_enabled": True
    },
    "fixed_income_pricing": {
        "yield_curve_interpolation": "cubic_spline",
        "credit_spread_enabled": True,
        "duration_matching": True
    },
    
    # Performance and reporting
    "benchmark_symbol": "SPY",
    "enable_performance_reporting": True,
    "save_results": True,
    "output_directory": "./results/market_making_project",
    "enable_market_making_metrics": True,
    
    # Market making specific metrics
    "track_bid_ask_spreads": True,
    "track_fill_ratios": True,
    "track_inventory_turnover": True,
    "track_pnl_attribution": True,
    
    # Advanced settings
    "warm_up_period": 30,  # Days - shorter for market making
    "market_on_open_orders": True,
    "market_on_close_orders": True,
    "fill_forward_missing_data": True,
    "handle_corporate_actions": True,
    
    # Quote generation settings
    "quote_generation": {
        "spread_model": "volatility_based",
        "min_spread_bps": 5,
        "max_spread_bps": 50,
        "default_quote_size": 100,
        "size_scaling_factor": 1.0
    },
    
    # Market data settings
    "market_data": {
        "enable_level_2_data": True,
        "order_book_depth": 5,
        "tick_size_optimization": True,
        "real_time_pricing": True
    },
    
    # Backtesting enhancements
    "backtesting_enhancements": {
        "realistic_order_fill_simulation": True,
        "market_impact_modeling": True,
        "liquidity_constraints": True,
        "market_hours_enforcement": True
    }
}

# Live trading configuration (extends backtesting config)
LIVE_TRADING_CONFIG = MISBUFFET_ENGINE_CONFIG.copy()
LIVE_TRADING_CONFIG.update({
    "engine_type": "live_trading",
    "execution_mode": "asynchronous",
    "paper_trading": True,  # Start with paper trading
    
    # Real-time data settings
    "real_time_data_feeds": True,
    "data_update_frequency": "real_time",
    "order_management_system": "interactive_brokers",
    
    # Live risk management
    "enable_kill_switch": True,
    "max_daily_loss": 10000.0,
    "position_monitoring_frequency": 10,  # seconds
    
    # Connection settings
    "broker_connection": {
        "host": "127.0.0.1",
        "port": 7497,  # Paper trading port
        "client_id": 1,
        "timeout": 60
    }
})