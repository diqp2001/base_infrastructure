"""
Configuration for FMP Equity Service.
Defines symbols to track and service parameters.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class FmpEquityServiceConfig:
    """Configuration class for FMP Equity Service."""
    
    # Symbols to track
    symbols: List[str]
    
    # Service parameters
    update_interval_minutes: int = 60  # How often to fetch data
    max_records_per_symbol: int = 1000  # Max historical records to keep
    enable_real_time: bool = False  # Enable real-time updates
    data_retention_days: int = 365  # Days to retain historical data
    
    # API configuration
    rate_limit_delay: float = 0.2  # Delay between API calls in seconds
    timeout_seconds: int = 30  # Request timeout
    
    # Database configuration
    batch_size: int = 100  # Number of records to process in batch
    enable_bulk_updates: bool = True  # Use bulk operations for better performance


# Default configuration
DEFAULT_CONFIG = FmpEquityServiceConfig(
    symbols=[
        'AAPL',   # Apple Inc.
        'MSFT',   # Microsoft Corporation
        'GOOGL',  # Alphabet Inc. Class A
        'AMZN',   # Amazon.com Inc.
        'TSLA',   # Tesla Inc.
        'META',   # Meta Platforms Inc.
        'NVDA',   # NVIDIA Corporation
        'BRK.B',  # Berkshire Hathaway Inc. Class B
        'JNJ',    # Johnson & Johnson
        'V'       # Visa Inc.
    ],
    update_interval_minutes=60,
    max_records_per_symbol=1000,
    enable_real_time=False,
    data_retention_days=365,
    rate_limit_delay=0.2,
    timeout_seconds=30,
    batch_size=100,
    enable_bulk_updates=True
)


def load_config_from_dict(config_dict: Dict[str, Any]) -> FmpEquityServiceConfig:
    """
    Load configuration from dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        FmpEquityServiceConfig instance
    """
    return FmpEquityServiceConfig(
        symbols=config_dict.get('symbols', DEFAULT_CONFIG.symbols),
        update_interval_minutes=config_dict.get('update_interval_minutes', DEFAULT_CONFIG.update_interval_minutes),
        max_records_per_symbol=config_dict.get('max_records_per_symbol', DEFAULT_CONFIG.max_records_per_symbol),
        enable_real_time=config_dict.get('enable_real_time', DEFAULT_CONFIG.enable_real_time),
        data_retention_days=config_dict.get('data_retention_days', DEFAULT_CONFIG.data_retention_days),
        rate_limit_delay=config_dict.get('rate_limit_delay', DEFAULT_CONFIG.rate_limit_delay),
        timeout_seconds=config_dict.get('timeout_seconds', DEFAULT_CONFIG.timeout_seconds),
        batch_size=config_dict.get('batch_size', DEFAULT_CONFIG.batch_size),
        enable_bulk_updates=config_dict.get('enable_bulk_updates', DEFAULT_CONFIG.enable_bulk_updates)
    )


def get_default_config() -> FmpEquityServiceConfig:
    """Get the default configuration for FMP Equity Service."""
    return DEFAULT_CONFIG