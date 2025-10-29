"""
Launch configuration for test_base_project Misbuffet backtesting framework.

This configuration file defines the launch parameters for the Misbuffet package
specifically tailored for the hybrid spatiotemporal momentum system.
"""

# Misbuffet Launch Configuration for test_base_project
MISBUFFET_LAUNCH_CONFIG = {
    # Environment settings
    "environment": "backtesting",
    "debug_mode": True,
    "log_level": "INFO",
    
    # Data settings
    "data_folder": "./downloads",
    "results_folder": "./results/test_base_project",
    
    # System settings
    "max_concurrent_algorithms": 1,
    "memory_limit_mb": 4096,  # Higher memory for ML models
    
    # Backtesting specific settings
    "allow_historical_data": True,
    "enable_logging": True,
    "log_trades": True,
    "enable_factor_integration": True,  # Custom setting for our factor system
    
    # ML Model settings (custom for test_base_project)
    "enable_spatiotemporal_models": True,
    "model_training_interval": "weekly",
    "ensemble_models": True,
    
    # Optional API settings (for live trading)
    "api_enabled": False,
    "api_key": None,
    "api_secret": None,
}