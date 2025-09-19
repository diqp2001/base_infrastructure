"""
Launch configuration for Misbuffet backtesting framework.

This configuration file defines the launch parameters for the Misbuffet package.
"""

# Misbuffet Launch Configuration
MISBUFFET_LAUNCH_CONFIG = {
    # Environment settings
    "environment": "backtesting",
    "debug_mode": True,
    "log_level": "INFO",
    
    # Data settings
    "data_folder": "./downloads",
    "results_folder": "./results",
    
    # System settings
    "max_concurrent_algorithms": 1,
    "memory_limit_mb": 2048,
    
    # Backtesting specific settings
    "allow_historical_data": True,
    "enable_logging": True,
    "log_trades": True,
    
    # Optional API settings (for live trading)
    "api_enabled": False,
    "api_key": None,
    "api_secret": None,
}