"""
Configuration for IBKR Futures Service

This module defines the configuration structure for the Interactive Brokers futures data service,
including which futures to track, connection parameters, and other operational settings.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
from pathlib import Path


@dataclass
class IBKRFuturesServiceConfig:
    """Configuration for IBKR Futures Service operations"""
    
    # Futures contracts to track
    futures_symbols: List[str]
    
    # IBKR connection settings
    host: str = "127.0.0.1"
    port: int = 7497  # Paper trading port
    client_id: int = 1
    paper_trading: bool = False
    
    # Update intervals (in seconds)
    update_interval: int = 300  # 5 minutes
    batch_size: int = 5  # Number of contracts to fetch at once
    
    # Data retention
    max_days_to_keep: int = 365  # Keep data for 1 year
    cleanup_interval: int = 86400  # Daily cleanup (24 hours)
    
    # Service behavior
    auto_create_missing_entities: bool = True
    enable_factor_creation: bool = True
    log_level: str = "INFO"
    
    # Timeout settings
    connection_timeout: int = 60  # Connection timeout in seconds
    data_timeout: int = 10  # Market data timeout in seconds
    
    # Contract settings
    exchange: str = "CME"  # Default exchange for futures
    currency: str = "USD"  # Default currency
    
    # Default configuration with major futures
    @classmethod
    def get_default_config(cls) -> 'IBKRFuturesServiceConfig':
        """
        Get default configuration tracking major US futures contracts.
        
        Returns:
            IBKRFuturesServiceConfig with sensible defaults
        """
        return cls(
            futures_symbols=[
                "ES",    # E-mini S&P 500 Futures
                "NQ",    # E-mini Nasdaq-100 Futures
                "YM",    # E-mini Dow Jones Industrial Average Futures
                "VX",    # VIX Futures
                "ZN",    # 10-Year U.S. Treasury Note Futures
                "ZB",    # 30-Year U.S. Treasury Bond Futures
                "CL",    # Crude Oil Futures
                "GC",    # Gold Futures
                "SI",    # Silver Futures
                "ZW",    # Wheat Futures
            ],
            host="127.0.0.1",
            port=7497,  # Paper trading
            client_id=1,
            paper_trading=True,
            update_interval=300,  # 5 minutes
            batch_size=3,  # Conservative for real-time futures data
            max_days_to_keep=365,
            cleanup_interval=86400,
            auto_create_missing_entities=True,
            enable_factor_creation=True,
            log_level="INFO",
            connection_timeout=60,
            data_timeout=10,
            exchange="CME",
            currency="USD"
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'IBKRFuturesServiceConfig':
        """
        Create config from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            IBKRFuturesServiceConfig instance
        """
        return cls(
            futures_symbols=config_dict.get('futures_symbols', []),
            host=config_dict.get('host', "127.0.0.1"),
            port=config_dict.get('port', 7497),
            client_id=config_dict.get('client_id', 1),
            paper_trading=config_dict.get('paper_trading', True),
            update_interval=config_dict.get('update_interval', 300),
            batch_size=config_dict.get('batch_size', 5),
            max_days_to_keep=config_dict.get('max_days_to_keep', 365),
            cleanup_interval=config_dict.get('cleanup_interval', 86400),
            auto_create_missing_entities=config_dict.get('auto_create_missing_entities', True),
            enable_factor_creation=config_dict.get('enable_factor_creation', True),
            log_level=config_dict.get('log_level', "INFO"),
            connection_timeout=config_dict.get('connection_timeout', 60),
            data_timeout=config_dict.get('data_timeout', 10),
            exchange=config_dict.get('exchange', "CME"),
            currency=config_dict.get('currency', "USD")
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'IBKRFuturesServiceConfig':
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to configuration file
            
        Returns:
            IBKRFuturesServiceConfig instance
        """
        filepath = Path(filepath)
        with open(filepath, 'r') as f:
            config_data = json.load(f)
        return cls.from_dict(config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'futures_symbols': self.futures_symbols,
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'paper_trading': self.paper_trading,
            'update_interval': self.update_interval,
            'batch_size': self.batch_size,
            'max_days_to_keep': self.max_days_to_keep,
            'cleanup_interval': self.cleanup_interval,
            'auto_create_missing_entities': self.auto_create_missing_entities,
            'enable_factor_creation': self.enable_factor_creation,
            'log_level': self.log_level,
            'connection_timeout': self.connection_timeout,
            'data_timeout': self.data_timeout,
            'exchange': self.exchange,
            'currency': self.currency
        }
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            filepath: Path where to save the configuration
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def add_futures_symbol(self, symbol: str) -> None:
        """
        Add a futures symbol to the tracking list.
        
        Args:
            symbol: Futures symbol to add (e.g., 'ES', 'NQ')
        """
        symbol = symbol.upper()
        if symbol not in self.futures_symbols:
            self.futures_symbols.append(symbol)
    
    def remove_futures_symbol(self, symbol: str) -> bool:
        """
        Remove a futures symbol from the tracking list.
        
        Args:
            symbol: Futures symbol to remove
            
        Returns:
            True if symbol was removed, False if not found
        """
        symbol = symbol.upper()
        if symbol in self.futures_symbols:
            self.futures_symbols.remove(symbol)
            return True
        return False
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return any errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.futures_symbols:
            errors.append("futures_symbols list cannot be empty")
        
        if self.update_interval < 60:
            errors.append("update_interval should be at least 60 seconds")
        
        if self.batch_size < 1:
            errors.append("batch_size must be at least 1")
        
        if self.max_days_to_keep < 1:
            errors.append("max_days_to_keep must be at least 1 day")
        
        if self.port not in [7496, 7497]:
            errors.append("port should be 7496 (live) or 7497 (paper)")
        
        if self.client_id < 1:
            errors.append("client_id must be positive integer")
        
        if self.connection_timeout < 10:
            errors.append("connection_timeout should be at least 10 seconds")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if configuration is valid.
        
        Returns:
            True if configuration is valid
        """
        return len(self.validate()) == 0
    
    def get_connection_config(self) -> Dict[str, Any]:
        """
        Get IBKR connection configuration.
        
        Returns:
            Dictionary with connection parameters
        """
        return {
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'paper_trading': self.paper_trading,
            'timeout': self.connection_timeout,
            'account_id': 'DEFAULT',
            'enable_logging': True,
        }


# Example configurations for different use cases

def get_major_indices_config() -> IBKRFuturesServiceConfig:
    """Get configuration focused on major index futures"""
    return IBKRFuturesServiceConfig(
        futures_symbols=["ES", "NQ", "YM"],  # S&P500, Nasdaq, Dow
        update_interval=180,  # 3 minutes for more frequent updates
        batch_size=3,
        log_level="INFO"
    )

def get_treasury_futures_config() -> IBKRFuturesServiceConfig:
    """Get configuration for US Treasury futures"""
    return IBKRFuturesServiceConfig(
        futures_symbols=["ZT", "ZF", "ZN", "TN", "ZB", "UB"],  # 2Y, 5Y, 10Y, Ultra 10Y, 30Y, Ultra 30Y
        update_interval=600,  # 10 minutes for bonds
        batch_size=3,
        log_level="INFO"
    )

def get_commodities_config() -> IBKRFuturesServiceConfig:
    """Get configuration for commodity futures"""
    return IBKRFuturesServiceConfig(
        futures_symbols=["CL", "NG", "GC", "SI", "ZW", "ZC", "ZS"],  # Oil, Gas, Gold, Silver, Wheat, Corn, Soybeans
        update_interval=300,  # 5 minutes
        batch_size=4,
        log_level="INFO"
    )

def get_volatility_config() -> IBKRFuturesServiceConfig:
    """Get configuration for volatility products"""
    return IBKRFuturesServiceConfig(
        futures_symbols=["VX"],  # VIX futures
        update_interval=120,  # 2 minutes for high-frequency vol products
        batch_size=1,
        log_level="DEBUG"
    )

def get_minimal_config() -> IBKRFuturesServiceConfig:
    """Get minimal configuration for testing"""
    return IBKRFuturesServiceConfig(
        futures_symbols=["ES"],  # Just S&P 500 E-mini
        update_interval=600,
        batch_size=1,
        max_days_to_keep=30,
        log_level="DEBUG"
    )