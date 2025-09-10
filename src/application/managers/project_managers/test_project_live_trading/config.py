"""
Configuration for the Live Trading Test Project.

This configuration file defines the settings for live trading operations
using the Interactive Brokers platform.
"""

CONFIG_LIVE_TRADING = {
    'DB_TYPE': 'sqlite',
    'dataset_name': "live-trading-data",
    
    # Trading environment settings
    'TRADING_MODE': 'live',
    'PAPER_TRADING': True,  # Set to False for real money trading
    
    # Interactive Brokers settings
    'IB_HOST': '127.0.0.1',  # TWS or IB Gateway host
    'IB_PORT': 7497,         # 7497 for paper trading, 7496 for live trading
    'IB_CLIENT_ID': 1,       # Unique client ID
    
    # Risk management
    'MAX_POSITION_SIZE': 0.20,  # 20% max per position
    'MAX_PORTFOLIO_LEVERAGE': 2.0,
    'ENABLE_RISK_CHECKS': True,
    
    # Trading session settings
    'TRADING_HOURS_START': '09:30:00',  # NYSE open time (ET)
    'TRADING_HOURS_END': '16:00:00',    # NYSE close time (ET)
    'TIMEZONE': 'America/New_York',
    
    # Data refresh intervals
    'MARKET_DATA_REFRESH_SECONDS': 1,
    'PORTFOLIO_UPDATE_SECONDS': 5,
    
    # Logging and monitoring
    'LOG_TRADES': True,
    'LOG_MARKET_DATA': False,  # Set to True for debugging
    'ENABLE_PERFORMANCE_TRACKING': True,
    
    # Backup and recovery
    'BACKUP_TRADES': True,
    'BACKUP_INTERVAL_MINUTES': 15,
}