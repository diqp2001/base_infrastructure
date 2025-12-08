"""
Broker factory for creating broker instances based on configuration.

This module provides a factory pattern for creating different broker implementations
while maintaining the abstraction layer and supporting extensibility.
"""

import logging
from typing import Dict, Any, Optional, Type
from enum import Enum

from application.services.misbuffet.launcher.interfaces import LauncherConfiguration

from .base_broker import BaseBroker
from .interactive_brokers_broker import InteractiveBrokersBroker


class SupportedBrokers(Enum):
    """Enumeration of supported brokers."""
    INTERACTIVE_BROKERS = "interactive_brokers"
    MOCK_BROKER = "mock_broker" 
    # Future brokers can be added here:
    # TD_AMERITRADE = "td_ameritrade"
    # CHARLES_SCHWAB = "charles_schwab"
    # ALPACA = "alpaca"
    # ROBINHOOD = "robinhood"


class BrokerFactory:
    """
    Factory class for creating broker instances.
    
    This factory supports multiple broker implementations and provides
    a unified way to create and configure brokers based on settings.
    """
    
    # Registry of available brokers
    _broker_registry: Dict[str, Type[BaseBroker]] = {
        SupportedBrokers.INTERACTIVE_BROKERS.value: InteractiveBrokersBroker,
        # Future brokers will be registered here
    }
    
    @classmethod
    def create_broker(cls, broker_type: str, config: Dict[str, Any]) -> BaseBroker:
        """
        Create a broker instance based on type and configuration.
        
        Args:
            broker_type: Type of broker to create (e.g., "interactive_brokers")
            config: Configuration dictionary for the broker
            
        Returns:
            Configured broker instance
            
        Raises:
            ValueError: If broker type is not supported
            Exception: If broker initialization fails
        """
        logger = logging.getLogger(cls.__name__)
        
        if broker_type not in cls._broker_registry:
            supported_types = list(cls._broker_registry.keys())
            raise ValueError(f"Unsupported broker type: {broker_type}. "
                           f"Supported types: {supported_types}")
        
        try:
            broker_class = cls._broker_registry[broker_type]
            
            # Validate broker-specific configuration
            cls._validate_broker_config(broker_type, config)
            
            # Create broker instance
            broker = broker_class(config)
            
            logger.info(f"Created {broker_type} broker instance")
            return broker
            
        except Exception as e:
            logger.error(f"Failed to create {broker_type} broker: {e}")
            raise
    
    @classmethod
    def _validate_broker_config(cls, broker_type: str, config: Dict[str, Any]) -> None:
        """
        Validate broker-specific configuration.
        
        Args:
            broker_type: Type of broker
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if broker_type == SupportedBrokers.INTERACTIVE_BROKERS.value:
            cls._validate_ib_config(config)
        # Add validation for other brokers here
    
    @classmethod
    def _validate_ib_config(cls, config: Dict[str, Any]) -> None:
        """Validate Interactive Brokers configuration."""
        required_fields = ['host', 'port', 'client_id']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Interactive Brokers config missing fields: {missing_fields}")
        
        # Validate port range
        port = config.get('port')
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Invalid port number: {port}")
        
        # Validate client ID
        client_id = config.get('client_id')
        if not isinstance(client_id, int) or client_id < 0:
            raise ValueError(f"Invalid client ID: {client_id}")
    
    @classmethod
    def register_broker(cls, broker_name: str, broker_class: Type[BaseBroker]) -> None:
        """
        Register a new broker implementation.
        
        This allows for extending the framework with additional brokers
        without modifying the core factory code.
        
        Args:
            broker_name: Unique name for the broker
            broker_class: Broker class that extends BaseBroker
            
        Raises:
            ValueError: If broker_name already exists or broker_class is invalid
        """
        logger = logging.getLogger(cls.__name__)
        
        if broker_name in cls._broker_registry:
            raise ValueError(f"Broker {broker_name} is already registered")
        
        if not issubclass(broker_class, BaseBroker):
            raise ValueError(f"Broker class must extend BaseBroker")
        
        cls._broker_registry[broker_name] = broker_class
        logger.info(f"Registered new broker: {broker_name}")
    
    @classmethod
    def get_supported_brokers(cls) -> list[str]:
        """
        Get list of supported broker types.
        
        Returns:
            List of supported broker names
        """
        return list(cls._broker_registry.keys())
    
    @classmethod
    def create_mock_broker(cls, config: Optional[Dict[str, Any]] = None) -> BaseBroker:
        """
        Create a mock broker for testing purposes.
        
        Args:
            config: Optional configuration (uses defaults if not provided)
            
        Returns:
            Mock broker instance
        """
        if config is None:
            config = {
                'host': 'localhost',
                'port': 7497,
                'client_id': 999,
                'paper_trading': True,
                'mock_mode': True
            }
        
        return cls.create_broker(SupportedBrokers.INTERACTIVE_BROKERS.value, config)
    
    @classmethod
    def create_from_launcher_config(cls, launcher_config: LauncherConfiguration) -> Optional[BaseBroker]:
        """
        Create broker from launcher configuration.
        
        Args:
            launcher_config: Launcher configuration object
            
        Returns:
            Broker instance or None if not configured for live trading
        """
        logger = logging.getLogger(cls.__name__)
        
        # Only create broker for live trading mode
        from ..launcher.interfaces import LauncherMode
        if launcher_config.mode != LauncherMode.LIVE_TRADING:
            logger.info("Skipping broker creation - not in live trading mode")
            return None
        
        # Get broker configuration from custom config
        custom_config = launcher_config.custom_config or {}
        broker_type = custom_config.get('brokerage', 'interactive_brokers')
        
        # Build broker-specific configuration
        broker_config = {
            'host': custom_config.get('ib_host', '127.0.0.1'),
            'port': custom_config.get('ib_port', 7497),
            'client_id': custom_config.get('ib_client_id', 1),
            'timeout': custom_config.get('ib_timeout', 60),
            'paper_trading': custom_config.get('paper_trading', True),
            'account_id': custom_config.get('account_id', 'DEFAULT'),
            'enable_logging': custom_config.get('ib_enable_logging', True),
        }
        
        try:
            return cls.create_broker(broker_type, broker_config)
        except Exception as e:
            logger.error(f"Failed to create broker from launcher config: {e}")
            return None


def create_interactive_brokers_broker(
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 1,
    paper_trading: bool = True,
    **kwargs
) -> InteractiveBrokersBroker:
    """
    Convenience function to create Interactive Brokers broker.
    
    Args:
        host: IB TWS/Gateway host
        port: IB TWS/Gateway port (7497 for paper, 7496 for live)
        client_id: Unique client ID
        paper_trading: Whether using paper trading account
        **kwargs: Additional configuration options
        
    Returns:
        Configured Interactive Brokers broker instance
    """
    config = {
        'host': host,
        'port': port,
        'client_id': client_id,
        'paper_trading': paper_trading,
        **kwargs
    }
    
    return BrokerFactory.create_broker(
        SupportedBrokers.INTERACTIVE_BROKERS.value,
        config
    )


# Example usage and configuration templates

INTERACTIVE_BROKERS_PAPER_CONFIG = {
    'host': '127.0.0.1',
    'port': 7497,  # Paper trading port
    'client_id': 1,
    'paper_trading': True,
    'timeout': 60,
    'account_id': 'DEFAULT',
    'enable_logging': True,
}

INTERACTIVE_BROKERS_LIVE_CONFIG = {
    'host': '127.0.0.1', 
    'port': 7496,  # Live trading port
    'client_id': 1,
    'paper_trading': False,
    'timeout': 60,
    'account_id': 'YOUR_ACCOUNT_ID',  # Replace with actual account ID
    'enable_logging': True,
    'require_confirmation': True,  # Extra safety for live trading
}

# Template for adding future brokers:
"""
BROKER_NAME_CONFIG = {
    'api_key': 'your_api_key',
    'secret_key': 'your_secret_key',
    'environment': 'sandbox',  # or 'live'
    'timeout': 30,
    # ... other broker-specific settings
}
"""