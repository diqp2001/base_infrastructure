"""
Configuration settings for Market Making SPX Call Spread Project
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
# Base configuration
BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
DATA_PATH = BASE_PROJECT_ROOT / "data"
# Database Configuration
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db'
}

# Default configuration for market making SPX call spread project
DEFAULT_CONFIG = {
    # Project settings
    'project_name': 'market_making_spx_call_spread',
    'version': '1.0.0',
    
    # SPX Configuration
    'underlying_symbol': 'SPX',
    'underlying_exchange': 'CBOE',
    'underlying_currency': 'USD',
    
    # Call Spread Configuration
    'spread_type': 'bull_call_spread',  # or 'bear_call_spread'
    'default_dte_range': (7, 45),  # Days to expiration range
    'default_delta_range': (0.15, 0.45),  # Delta range for strikes
    'max_spread_width': 50,  # Maximum spread width in points
    
    # Market Data Configuration
    'historical_data_duration': '6 M',  # 6 months of historical data
    'bar_size_setting': '5 mins',
    'option_data_duration': '30 D',  # 30 days of option data
    
    # Risk Management
    'max_position_size': 10,  # Maximum number of spreads
    'max_daily_loss': 5000,  # Maximum daily loss in USD
    'max_gamma_exposure': 1000,  # Maximum gamma exposure
    'min_time_to_expiry': 7,  # Minimum days to expiry before closing
    
    # Pricing Configuration
    'volatility_model': 'implied',  # 'implied' or 'historical'
    'interest_rate': 0.05,  # Risk-free rate
    'dividend_yield': 0.015,  # SPX dividend yield
    
    # Trading Configuration
    'trading_hours': {
        'start': '09:30',
        'end': '16:00',
        'timezone': 'US/Eastern'
    },
    
    # Backtesting Configuration
    'backtest_start': '2023-01-01',
    'backtest_end': '2024-12-31',
    'initial_capital': 100000,
    'commission_per_contract': 0.65,
    
    # Model Training
    'model_types': ['tft', 'mlp'],
    'training_window': 252,  # 1 year of trading days
    'validation_split': 0.2,
    'test_split': 0.2,
    
    # Factors for modeling
    'price_factors': ['open', 'high', 'low', 'close', 'volume'],
    'technical_factors': ['sma_10', 'sma_20', 'rsi', 'macd', 'bb_upper', 'bb_lower'],
    'volatility_factors': ['realized_vol_10', 'realized_vol_20', 'vix', 'term_structure'],
    'market_factors': ['put_call_ratio', 'skew', 'term_structure_slope'],
    
    # MLflow tracking
    'mlflow_experiment_name': 'market_making_spx_call_spread',
    'mlflow_tracking_uri': './mlruns',
    
    # Web interface
    'web_interface_port': 5001,
    'enable_web_interface': True,
}

def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return DEFAULT_CONFIG.copy()

def get_spx_contract_config() -> Dict[str, Any]:
    """Get SPX-specific contract configuration."""
    return {
        'symbol': DEFAULT_CONFIG['underlying_symbol'],
        'exchange': DEFAULT_CONFIG['underlying_exchange'],
        'currency': DEFAULT_CONFIG['underlying_currency'],
        'sec_type': 'IND',  # Index
        'multiplier': 100,
    }

def get_option_chain_config() -> Dict[str, Any]:
    """Get option chain configuration for SPX options."""
    return {
        'symbol': 'SPX',
        'exchange': 'CBOE', 
        'currency': 'USD',
        'sec_type': 'OPT',
        'multiplier': 100,
        'dte_range': DEFAULT_CONFIG['default_dte_range'],
        'delta_range': DEFAULT_CONFIG['default_delta_range'],
    }

def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration."""
    return {
        'max_position_size': DEFAULT_CONFIG['max_position_size'],
        'max_daily_loss': DEFAULT_CONFIG['max_daily_loss'],
        'max_gamma_exposure': DEFAULT_CONFIG['max_gamma_exposure'],
        'commission_per_contract': DEFAULT_CONFIG['commission_per_contract'],
        'trading_hours': DEFAULT_CONFIG['trading_hours'],
    }