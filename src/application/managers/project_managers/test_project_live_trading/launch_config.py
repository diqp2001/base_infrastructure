"""
Launch configuration for Misbuffet live trading framework.

This configuration file defines the launch parameters for the Misbuffet package
in live trading mode with Interactive Brokers.
"""

# Misbuffet Launch Configuration for Live Trading
MISBUFFET_LAUNCH_CONFIG = {
    # Environment settings
    "environment": "live_trading",
    "debug_mode": True,
    "log_level": "INFO",
    
    # Data settings
    "data_folder": "./live_data",
    "results_folder": "./live_results",
    "backup_folder": "./backups",
    
    # System settings
    "max_concurrent_algorithms": 1,  # Single algorithm for live trading
    "memory_limit_mb": 4096,        # Higher for live data
    "cpu_cores": 2,
    
    # Live trading specific settings
    "allow_historical_data": True,
    "enable_logging": True,
    "log_trades": True,
    "log_market_data": True,
    "enable_real_time_monitoring": True,
    
    # Interactive Brokers API settings
    "api_enabled": True,
    "api_type": "interactive_brokers",
    "api_host": "127.0.0.1",
    "api_port": 7497,  # Paper trading port
    "api_client_id": 1,
    "api_timeout": 60,
    
    # Security and authentication
    "enable_authentication": True,
    "require_two_factor": False,  # IB handles 2FA separately
    
    # Risk management at launcher level
    "enable_position_limits": True,
    "max_daily_loss": 5000,  # USD
    "max_drawdown_percent": 10,
    "emergency_stop_enabled": True,
    
    # Performance monitoring
    "enable_performance_alerts": True,
    "performance_check_interval_minutes": 5,
    
    # Backup and recovery
    "auto_backup": True,
    "backup_interval_minutes": 15,
    "max_backup_files": 100,
    
    # Network and connectivity
    "connection_timeout_seconds": 30,
    "max_retry_attempts": 3,
    "retry_delay_seconds": 5,
    
    # Market data settings
    "enable_market_data": True,
    "market_data_subscriptions": [
        "Level1",  # Basic quotes
        "Level2",  # Market depth (if subscribed with IB)
    ],
    "enable_news_feed": False,  # Can be enabled if IB news is subscribed
}