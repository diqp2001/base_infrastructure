"""
Launch configuration for Misbuffet backtesting framework in test_base_project.

This configuration file defines the launch parameters for the hybrid
spatiotemporal momentum + factor creation + backtesting system.
"""

# Misbuffet Launch Configuration for BaseProject
MISBUFFET_LAUNCH_CONFIG = {
    # Environment settings
    "environment": "backtesting",
    "debug_mode": True,
    "log_level": "INFO",
    
    # Data settings - enhanced for factor integration
    "data_folder": "./downloads",
    "results_folder": "./results", 
    "factor_data_enabled": True,
    "csv_data_fallback": True,
    
    # System settings
    "max_concurrent_algorithms": 1,
    "memory_limit_mb": 4096,  # Increased for ML models
    
    # Backtesting specific settings
    "allow_historical_data": True,
    "enable_logging": True,
    "log_trades": True,
    "log_factor_data": True,
    
    # ML/AI settings
    "enable_ml_models": True,
    "model_cache_enabled": True,
    "ensemble_mode": True,
    
    # Factor system settings
    "populate_factors_on_start": True,
    "factor_groups": ['price', 'momentum', 'technical', 'engineered'],
    "overwrite_existing_factors": False,
    
    # Optional API settings (for live trading)
    "api_enabled": False,
    "api_key": None,
    "api_secret": None,
}