"""
Configuration for FMP Equity Service

This module defines the configuration structure for the FMP equity data service,
including which symbols to track, update intervals, and other operational parameters.
"""


from typing import List, Optional, Dict, Any
import json
from pathlib import Path



class FmpEquityServiceConfig:
    """Configuration for FMP Equity Service operations"""
    def __init__(self):

        # Symbols to track
        self.symbols: List[str] = ["AAPL"]
        
        # Update intervals (in seconds)
        self.update_interval: int = 300  # 5 minutes
        self.batch_size: int = 10  # Number of symbols to fetch at once
        
        # Data retention
        self.max_days_to_keep: int = 365  # Keep data for 1 year
        self.cleanup_interval: int = 86400  # Daily cleanup (24 hours)
        
        # FMP API settings
        self.use_free_tier: bool = True
        self.max_daily_calls: int = 250  # Free tier limit
        
        # Service behavior
        self.auto_create_missing_entities: bool = True
        self.enable_factor_creation: bool = True
        self.log_level: str = "INFO"
        self.DB_TYPE= 'sql_server'
    
    
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'symbols': self.symbols,
            'update_interval': self.update_interval,
            'batch_size': self.batch_size,
            'max_days_to_keep': self.max_days_to_keep,
            'cleanup_interval': self.cleanup_interval,
            'use_free_tier': self.use_free_tier,
            'max_daily_calls': self.max_daily_calls,
            'auto_create_missing_entities': self.auto_create_missing_entities,
            'enable_factor_creation': self.enable_factor_creation,
            'log_level': self.log_level
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
    
    def add_symbol(self, symbol: str) -> None:
        """
        Add a symbol to the tracking list.
        
        Args:
            symbol: Stock symbol to add
        """
        symbol = symbol.upper()
        if symbol not in self.symbols:
            self.symbols.append(symbol)
    
    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove a symbol from the tracking list.
        
        Args:
            symbol: Stock symbol to remove
            
        Returns:
            True if symbol was removed, False if not found
        """
        symbol = symbol.upper()
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            return True
        return False
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return any errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.symbols:
            errors.append("symbols list cannot be empty")
        
        if self.update_interval < 60:
            errors.append("update_interval should be at least 60 seconds")
        
        if self.batch_size < 1:
            errors.append("batch_size must be at least 1")
        
        if self.max_days_to_keep < 1:
            errors.append("max_days_to_keep must be at least 1 day")
        
        if self.use_free_tier and self.max_daily_calls > 250:
            errors.append("max_daily_calls cannot exceed 250 for free tier")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if configuration is valid.
        
        Returns:
            True if configuration is valid
        """
        return len(self.validate()) == 0


# Example configurations for different use cases

def get_tech_stocks_config() -> FmpEquityServiceConfig:
    """Get configuration focused on technology stocks"""
    return FmpEquityServiceConfig(
        symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "ADBE", "CRM"],
        update_interval=300,
        batch_size=5,
        log_level="INFO"
    )

def get_dow_jones_config() -> FmpEquityServiceConfig:
    """Get configuration for Dow Jones components"""
    return FmpEquityServiceConfig(
        symbols=[
            "AAPL", "MSFT", "UNH", "GS", "HD", "CAT", "CRM", "V", "MCD", "AXP",
            "BA", "IBM", "JPM", "JNJ", "WMT", "PG", "TRV", "CVX", "NKE", "MMM",
            "KO", "DIS", "DOW", "CSCO", "VZ", "WBA", "MRK", "INTC", "HON", "AMGN"
        ],
        update_interval=600,  # 10 minutes for larger list
        batch_size=5,
        log_level="INFO"
    )

def get_minimal_config() -> FmpEquityServiceConfig:
    """Get minimal configuration for testing"""
    return FmpEquityServiceConfig(
        symbols=["AAPL"],
        update_interval=600,
        batch_size=1,
        max_days_to_keep=30,
        log_level="DEBUG"
    )