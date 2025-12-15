"""
Launch configuration for Market Making Project Misbuffet framework.

This configuration file defines the launch parameters for the Misbuffet package
specifically tailored for the derivatives market making system.
"""

# Misbuffet Launch Configuration for Market Making Project
MISBUFFET_LAUNCH_CONFIG = {
    # Environment settings
    "environment": "backtesting",  # Can be "backtesting" or "live_trading"
    "debug_mode": True,
    "log_level": "INFO",
    
    # Data settings
    "data_folder": "./downloads/market_making",
    "results_folder": "./results/market_making_project",
    
    # System settings
    "max_concurrent_algorithms": 3,  # Support multiple asset classes
    "memory_limit_mb": 8192,  # Higher memory for derivatives pricing
    
    # Market making specific settings
    "allow_historical_data": True,
    "enable_logging": True,
    "log_trades": True,
    "log_quotes": True,  # Market making specific
    "enable_derivatives_pricing": True,
    
    # Asset class settings
    "supported_asset_classes": ["equity", "fixed_income", "commodity"],
    "enable_multi_asset_trading": True,
    "cross_asset_risk_management": True,
    
    # Derivatives pricing settings
    "pricing_models": {
        "black_scholes": True,
        "binomial_tree": True,
        "monte_carlo": True,
        "finite_difference": True
    },
    "volatility_models": {
        "implied_vol": True,
        "garch": True,
        "stochastic_vol": True
    },
    "curve_models": {
        "yield_curve": True,
        "forward_curve": True,
        "volatility_surface": True
    },
    
    # Market making execution settings
    "quote_management": {
        "auto_quote_updates": True,
        "inventory_aware_quoting": True,
        "dynamic_spread_adjustment": True
    },
    "order_management": {
        "cancel_replace_orders": True,
        "partial_fill_handling": True,
        "order_size_optimization": True
    },
    
    # Risk management settings
    "risk_management": {
        "enable_position_limits": True,
        "enable_var_limits": True,
        "enable_greeks_limits": True,
        "enable_sector_limits": True
    },
    
    # Interactive Brokers settings
    "broker_settings": {
        "enable_ib_integration": True,
        "paper_trading_default": True,
        "connection_timeout": 60,
        "heartbeat_interval": 30
    },
    
    # Performance monitoring
    "performance_tracking": {
        "enable_real_time_pnl": True,
        "track_greeks_exposure": True,
        "inventory_monitoring": True,
        "spread_performance_tracking": True
    },
    
    # Data feeds configuration
    "data_feeds": {
        "market_data": "interactive_brokers",
        "reference_data": "file_system", 
        "corporate_actions": "interactive_brokers",
        "earnings_calendar": "external_api"
    },
    
    # Backtesting enhancements
    "backtesting": {
        "realistic_fills": True,
        "market_impact_simulation": True,
        "liquidity_modeling": True,
        "transaction_cost_modeling": True
    },
    
    # Live trading settings (when environment = "live_trading")
    "live_trading": {
        "enable_kill_switch": True,
        "max_daily_drawdown": 0.05,
        "position_reconciliation": True,
        "real_time_risk_checks": True
    },
    
    # Optional API settings
    "api_enabled": False,
    "api_key": None,
    "api_secret": None,
    
    # Reporting and analytics
    "reporting": {
        "generate_daily_reports": True,
        "enable_attribution_analysis": True,
        "greek_sensitivity_reports": True,
        "inventory_turnover_analysis": True
    },
    
    # Advanced features
    "advanced_features": {
        "machine_learning_signals": False,  # Can be enabled for ML integration
        "alternative_data_feeds": False,
        "sentiment_analysis": False,
        "news_impact_modeling": False
    }
}

# Live trading launch configuration
LIVE_TRADING_LAUNCH_CONFIG = MISBUFFET_LAUNCH_CONFIG.copy()
LIVE_TRADING_LAUNCH_CONFIG.update({
    "environment": "live_trading",
    "debug_mode": False,
    "log_level": "WARNING",
    
    # Enhanced live trading settings
    "live_trading": {
        "enable_kill_switch": True,
        "max_daily_drawdown": 0.02,  # Stricter for live trading
        "position_reconciliation": True,
        "real_time_risk_checks": True,
        "enable_circuit_breakers": True,
        "max_order_size": 1000,
        "pre_trade_risk_checks": True
    },
    
    # Production API settings
    "api_enabled": True,
    "broker_settings": {
        "enable_ib_integration": True,
        "paper_trading_default": False,  # Live trading
        "connection_timeout": 30,
        "heartbeat_interval": 15
    }
})