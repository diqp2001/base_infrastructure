"""
Configuration settings for Market Making SPX Call Spread Project
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.index.index import Index
from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
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
    'universe' : {
        IndexFutureOption: [
            # ES future options - use underlying root 'ES' for options, not future symbol 'ESZ6'
            {"symbol": "ES", "strike_price": 6860.0, "expiry": "20261218", "option_type": "C"},  # ATM Call (December expiry for ES options)
            {"symbol": "ES", "strike_price": 6860.0, "expiry": "20261218", "option_type": "P"},  # ATM Put
            # Additional strikes for spread strategies
            {"symbol": "ES", "strike_price": 6900.0, "expiry": "20261218", "option_type": "C"},  # OTM Call
            {"symbol": "ES", "strike_price": 6820.0, "expiry": "20261218", "option_type": "C"},  # ITM Call
        ],
        Index: ["SPX"],
        IndexFuture: ["ESZ6"]
    },
    'target_factor': {
        IndexFutureOption: [
            {"symbol": "ES", "strike_price": 6860.0, "expiry": "20261218", "option_type": "C"},  # ATM Call
            {"symbol": "ES", "strike_price": 6860.0, "expiry": "20261218", "option_type": "P"},  # ATM Put
        ],
        Index: ["SPX"],
        IndexFuture: ["ESZ6"]
    },
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
    'backtest_start': '2026-02-02 09:30:00',
    'backtest_end': '2026-02-04 14:30:00',
    # frequence
    'config_interval' : {'custom_interval_minutes': 5},
    'initial_capital': 100000,
    'commission_per_contract': 0.65,
    
    # Model Training
    'model_type' : "pricing",
    'training_window': 252,  # 1 year of trading days
    'validation_split': 0.2,
    'test_split': 0.2,
    
    # Factors for modeling - only future_index_library and index_library factors
    'factors': [
        # Price factors from future_index_library
        FACTOR_LIBRARY["future_index_library"]["open"],
        FACTOR_LIBRARY["future_index_library"]["high"],
        FACTOR_LIBRARY["future_index_library"]["low"],
        FACTOR_LIBRARY["future_index_library"]["close"],
        FACTOR_LIBRARY["future_index_library"]["volume"],
        
        # Future return factors (daily, weekly, monthly)
        FACTOR_LIBRARY["future_index_library"]["return_daily"],
        
        # Index return factors (daily, weekly, monthly)
        FACTOR_LIBRARY["index_library"]["return_daily"],
        FACTOR_LIBRARY["future_index_option_library"]["return_daily"],
    ],

    
    
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

# def get_spx_contract_config() -> Dict[str, Any]:
#     """Get SPX-specific contract configuration."""
#     return {
#         'symbol': DEFAULT_CONFIG['underlying_symbol'],
#         'exchange': DEFAULT_CONFIG['underlying_exchange'],
#         'currency': DEFAULT_CONFIG['underlying_currency'],
#         'sec_type': 'IND',  # Index
#         'multiplier': 100,
#     }

# def get_option_chain_config() -> Dict[str, Any]:
#     """Get option chain configuration for SPX options."""
#     return {
#         'symbol': 'SPX',
#         'exchange': 'CBOE', 
#         'currency': 'USD',
#         'sec_type': 'OPT',
#         'multiplier': 100,
#         'dte_range': DEFAULT_CONFIG['default_dte_range'],
#         'delta_range': DEFAULT_CONFIG['default_delta_range'],
#     }

def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration."""
    return {
        'max_position_size': DEFAULT_CONFIG['max_position_size'],
        'max_daily_loss': DEFAULT_CONFIG['max_daily_loss'],
        'max_gamma_exposure': DEFAULT_CONFIG['max_gamma_exposure'],
        'commission_per_contract': DEFAULT_CONFIG['commission_per_contract'],
        'trading_hours': DEFAULT_CONFIG['trading_hours'],
    }