"""
Configuration settings for Test Base Project Manager.

This module contains database configurations, model parameters, and system settings
for the hybrid trading system combining spatiotemporal modeling, factor creation,
and backtesting capabilities.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

# Base configuration
BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
DATA_PATH = BASE_PROJECT_ROOT / "data"

# Database Configuration
CONFIG_TEST = {
    'DB_TYPE': 'sqlite',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db'
}

CONFIG_PRODUCTION = {
    'DB_TYPE': 'postgresql',
    'HOST': os.getenv('DB_HOST', 'localhost'),
    'PORT': os.getenv('DB_PORT', '5432'),
    'NAME': os.getenv('DB_NAME', 'base_infrastructure'),
    'USER': os.getenv('DB_USER', 'postgres'),
    'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
}

# Data Configuration
DATA_CONFIG = {
    'STOCK_DATA_DIR': DATA_PATH / 'stock_data',
    'FX_DATA_PATH': DATA_PATH / 'fx_data' / 'currency_exchange_rates_02-01-1995_-_02-05-2018.csv',
    'DEFAULT_UNIVERSE': ['AAPL', 'MSFT', 'AMZN', 'GOOGL'],
    'DATE_FORMAT': '%Y-%m-%d',
    'LOOKBACK_DAYS': 252 * 3,  # 3 years of data
}

# Spatiotemporal Model Configuration
SPATIOTEMPORAL_CONFIG = {
    'TFT_PARAMS': {
        'hidden_size': 160,
        'attention_head_size': 4,
        'dropout': 0.3,
        'hidden_continuous_size': 8,
        'output_size': 7,
        'loss': 'MAE',
        'learning_rate': 0.03,
        'reduce_on_plateau_patience': 4,
    },
    'MLP_PARAMS': {
        'hidden_layers': [128, 64, 32],
        'dropout_rate': 0.3,
        'learning_rate': 0.001,
        'activation': 'relu',
        'batch_size': 64,
    },
    'TRAINING_CONFIG': {
        'history_size': 63,
        'encoder_length': 42,
        'validation_delta_days': 365,
        'test_delta_days': 365,
        'train_date_range': ('2017-01-01', '2020-12-31'),
        'batch_size': 64,
        'max_epochs': 100,
    },
    'FEATURES': {
        'momentum_features': [
            'norm_daily_return',
            'norm_monthly_return', 
            'norm_quarterly_return',
            'norm_biannual_return',
            'norm_annual_return'
        ],
        'technical_features': [
            'macd_8_24',
            'macd_16_48',
            'macd_32_96'
        ],
        'volatility_features': [
            'daily_vol',
            'monthly_vol'
        ]
    }
}

# Factor System Configuration
FACTOR_CONFIG = {
    'PRICE_FACTORS': [
        {'name': 'Open', 'group': 'price', 'subgroup': 'ohlc'},
        {'name': 'High', 'group': 'price', 'subgroup': 'ohlc'},
        {'name': 'Low', 'group': 'price', 'subgroup': 'ohlc'},
        {'name': 'Close', 'group': 'price', 'subgroup': 'ohlc'},
        {'name': 'Adj Close', 'group': 'price', 'subgroup': 'adjusted'}
    ],
    'MOMENTUM_FACTORS': [
        {'name': 'deep_momentum_1d', 'group': 'momentum', 'subgroup': 'short_term','period': 1},
        {'name': 'deep_momentum_5d', 'group': 'momentum', 'subgroup': 'short_term','period': 5},
        {'name': 'deep_momentum_21d', 'group': 'momentum', 'subgroup': 'medium_term','period': 21},
        {'name': 'deep_momentum_63d', 'group': 'momentum', 'subgroup': 'long_term','period': 63},
    ],
    'TECHNICAL_FACTORS': [
        {'name': 'macd_8_24', 'group': 'technical', 'subgroup': 'momentum'},
        {'name': 'macd_16_48', 'group': 'technical', 'subgroup': 'momentum'},
        {'name': 'macd_32_96', 'group': 'technical', 'subgroup': 'momentum'},
        {'name': 'rsi_14', 'group': 'technical', 'subgroup': 'momentum'},
        {'name': 'bollinger_upper', 'group': 'technical', 'subgroup': 'volatility'},
        {'name': 'bollinger_lower', 'group': 'technical', 'subgroup': 'volatility'},
    ]
}

# Backtesting Configuration
BACKTEST_CONFIG = {
    'START_DATE': '2018-01-01',
    'END_DATE': '2023-12-31',
    'INITIAL_CAPITAL': 100000.0,
    'BENCHMARK_TICKER': 'SPY',
    'COMMISSION_MODEL': 'equity_commission',
    'SLIPPAGE_MODEL': 'volume_share_slippage',
    'REBALANCE_FREQUENCY': 'weekly',
    'MAX_POSITION_SIZE': 0.25,  # 25% maximum per position
    'MIN_POSITION_SIZE': 0.01,  # 1% minimum per position
}

# Portfolio Optimization Configuration
PORTFOLIO_CONFIG = {
    'BLACK_LITTERMAN': {
        'risk_aversion': 3.0,
        'tau': 0.025,
        'confidence_level': 0.95,
        'lookback_days': 252,
        'min_weight': 0.0,
        'max_weight': 0.3,
    },
    'RISK_MANAGEMENT': {
        'max_volatility': 0.20,
        'max_drawdown': 0.15,
        'var_confidence': 0.05,
        'position_concentration': 0.25,
    }
}

# Web Interface Configuration
WEB_CONFIG = {
    'HOST': '127.0.0.1',
    'PORT': 5000,
    'DEBUG': True,
    'TEMPLATES_DIR': 'templates',
    'STATIC_DIR': 'static',
    'UPDATE_INTERVAL_SECONDS': 5,
    'CHART_CONFIG': {
        'width': 800,
        'height': 600,
        'dpi': 100,
        'style': 'seaborn-v0_8',
        'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    }
}

# Performance Analytics Configuration
ANALYTICS_CONFIG = {
    'METRICS': [
        'total_return',
        'sharpe_ratio',
        'max_drawdown',
        'volatility',
        'win_rate',
        'profit_factor',
        'calmar_ratio'
    ],
    'BENCHMARK_METRICS': True,
    'ATTRIBUTION_ANALYSIS': True,
    'RISK_DECOMPOSITION': True,
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'handlers': ['console', 'file'],
    'file_path': BASE_PROJECT_ROOT / 'logs' / 'test_base_project.log'
}

# Environment-specific configuration
def get_config(env: str = 'test') -> Dict[str, Any]:
    """Get configuration for specified environment."""
    base_config = {
        'DATA': DATA_CONFIG,
        'SPATIOTEMPORAL': SPATIOTEMPORAL_CONFIG,
        'FACTORS': FACTOR_CONFIG,
        'BACKTEST': BACKTEST_CONFIG,
        'PORTFOLIO': PORTFOLIO_CONFIG,
        'WEB': WEB_CONFIG,
        'ANALYTICS': ANALYTICS_CONFIG,
        'LOGGING': LOGGING_CONFIG,
    }
    
    if env == 'test':
        base_config['DATABASE'] = CONFIG_TEST
    elif env == 'production':
        base_config['DATABASE'] = CONFIG_PRODUCTION
    else:
        raise ValueError(f"Unknown environment: {env}")
    
    return base_config

# Default configuration
DEFAULT_CONFIG = get_config('test')