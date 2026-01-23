"""
Data Loader - Initializes and configures all data services for the trading engine.
This is the main entry point for setting up the data infrastructure.
"""

from datetime import datetime
from typing import Optional, Dict, Any, NamedTuple
from dataclasses import dataclass

from ...data.entities.entity_service import EntityService
from ...database_service.database_service import DatabaseService
from .market_data_service import MarketDataService
from .market_data_history_service import MarketDataHistoryService


@dataclass
class DataConfiguration:
    """Configuration for data services initialization."""
    # Database configuration
    database_type: str = 'sqlite'
    database_connection_string: Optional[str] = None
    
    # Backtest configuration
    data_folder: Optional[str] = None
    backtest_start: Optional[datetime] = None
    backtest_end: Optional[datetime] = None
    
    # Live trading configuration
    broker_connection: Optional[Any] = None
    
    # Additional settings
    enable_caching: bool = True
    max_cache_size: int = 100
    max_history_days: int = 730  # 2 years default


class DataServices(NamedTuple):
    """Container for all initialized data services."""
    entity_service: EntityService
    market_data_service: MarketDataService
    history_service: MarketDataHistoryService
    database_service: DatabaseService


class DataLoader:
    """
    Factory class for initializing and configuring all data services.
    This class orchestrates the setup of EntityService, MarketDataService,
    and MarketDataHistoryService based on the provided configuration.
    """
    
    def __init__(self):
        self._initialized_services: Optional[DataServices] = None
        self._configuration: Optional[DataConfiguration] = None
    
    def load_for_backtest(self, 
                         data_folder: str,
                         start_time: datetime,
                         end_time: datetime,
                         database_type: str = 'sqlite',
                         database_connection: Optional[str] = None) -> DataServices:
        """
        Initialize all data services for backtesting.
        
        Args:
            data_folder: Path to historical data files
            start_time: Backtest start time
            end_time: Backtest end time
            database_type: Type of database to use
            database_connection: Optional database connection string
            
        Returns:
            DataServices containing all initialized services
        """
        config = DataConfiguration(
            database_type=database_type,
            database_connection_string=database_connection,
            data_folder=data_folder,
            backtest_start=start_time,
            backtest_end=end_time
        )
        
        return self._initialize_services(config, mode='backtest')
    
    def load_for_live_trading(self,
                            broker_connection=None,
                            database_type: str = 'sqlite',
                            database_connection: Optional[str] = None) -> DataServices:
        """
        Initialize all data services for live trading.
        
        Args:
            broker_connection: Broker connection for live data
            database_type: Type of database to use
            database_connection: Optional database connection string
            
        Returns:
            DataServices containing all initialized services
        """
        config = DataConfiguration(
            database_type=database_type,
            database_connection_string=database_connection,
            broker_connection=broker_connection
        )
        
        return self._initialize_services(config, mode='live')
    
    def load_with_config(self, config: DataConfiguration, mode: str = 'backtest') -> DataServices:
        """
        Initialize services with a custom configuration.
        
        Args:
            config: DataConfiguration object
            mode: Either 'backtest' or 'live'
            
        Returns:
            DataServices containing all initialized services
        """
        return self._initialize_services(config, mode)
    
    def _initialize_services(self, config: DataConfiguration, mode: str) -> DataServices:
        """
        Internal method to initialize all services.
        
        Args:
            config: Configuration for services
            mode: Operation mode ('backtest' or 'live')
            
        Returns:
            Initialized DataServices
        """
        try:
            self._configuration = config
            
            # 1. Initialize Database Service
            database_service = self._create_database_service(config)
            
            # 2. Initialize Entity Service
            entity_service = self._create_entity_service(database_service)
            
            # 3. Initialize Market Data Service
            market_data_service = self._create_market_data_service(entity_service)
            
            # 4. Configure Market Data Service based on mode
            if mode == 'backtest':
                success = self._setup_backtest_mode(market_data_service, config)
            elif mode == 'live':
                success = self._setup_live_mode(market_data_service, config)
            else:
                raise ValueError(f"Unknown mode: {mode}")
            
            if not success:
                raise RuntimeError(f"Failed to setup {mode} mode")
            
            # 5. Get History Service (created by MarketDataService)
            history_service = market_data_service.get_history_service()
            if not history_service:
                raise RuntimeError("Failed to initialize history service")
            
            # 6. Apply additional configuration
            self._apply_additional_config(config, market_data_service, history_service)
            
            # Create services container
            services = DataServices(
                entity_service=entity_service,
                market_data_service=market_data_service,
                history_service=history_service,
                database_service=database_service
            )
            
            self._initialized_services = services
            return services
            
        except Exception as e:
            print(f"Error initializing data services: {e}")
            raise
    
    def _create_database_service(self, config: DataConfiguration) -> DatabaseService:
        """Create and initialize database service."""
        try:
            if config.database_connection_string:
                # Use custom connection string
                database_service = DatabaseService(config.database_type)
                # In a real implementation, you would set the connection string
                # database_service.set_connection_string(config.database_connection_string)
            else:
                # Use default configuration
                database_service = DatabaseService(config.database_type)
            
            return database_service
            
        except Exception as e:
            raise RuntimeError(f"Failed to create database service: {e}")
    
    def _create_entity_service(self, database_service: DatabaseService) -> EntityService:
        """Create and initialize entity service."""
        try:
            entity_service = EntityService(database_service=database_service)
            return entity_service
            
        except Exception as e:
            raise RuntimeError(f"Failed to create entity service: {e}")
    
    def _create_market_data_service(self, entity_service: EntityService) -> MarketDataService:
        """Create market data service."""
        try:
            market_data_service = MarketDataService(entity_service)
            return market_data_service
            
        except Exception as e:
            raise RuntimeError(f"Failed to create market data service: {e}")
    
    def _setup_backtest_mode(self, market_data_service: MarketDataService, 
                           config: DataConfiguration) -> bool:
        """Setup market data service for backtesting."""
        if not config.data_folder or not config.backtest_start or not config.backtest_end:
            raise ValueError("Backtest mode requires data_folder, backtest_start, and backtest_end")
        
        try:
            return market_data_service.initialize_backtest(
                config.data_folder,
                config.backtest_start,
                config.backtest_end
            )
        except Exception as e:
            print(f"Error setting up backtest mode: {e}")
            return False
    
    def _setup_live_mode(self, market_data_service: MarketDataService, 
                        config: DataConfiguration) -> bool:
        """Setup market data service for live trading."""
        try:
            return market_data_service.initialize_live_trading(config.broker_connection)
        except Exception as e:
            print(f"Error setting up live mode: {e}")
            return False
    
    def _apply_additional_config(self, config: DataConfiguration,
                               market_data_service: MarketDataService,
                               history_service: MarketDataHistoryService):
        """Apply additional configuration settings."""
        try:
            # Configure history service cache
            if hasattr(history_service, '_cache_max_size'):
                history_service._cache_max_size = config.max_cache_size
            
            if hasattr(history_service, '_max_history_days'):
                history_service._max_history_days = config.max_history_days
            
            # Configure market data service error handling
            market_data_service.on_error = self._default_error_handler
            
        except Exception as e:
            print(f"Warning: Could not apply additional configuration: {e}")
    
    def _default_error_handler(self, error_message: str):
        """Default error handler for data services."""
        print(f"DataLoader Error: {error_message}")
    
    def get_services(self) -> Optional[DataServices]:
        """Get the currently initialized services."""
        return self._initialized_services
    
    def dispose(self):
        """Clean up all initialized services."""
        if self._initialized_services:
            try:
                self._initialized_services.market_data_service.dispose()
                self._initialized_services.history_service.dispose()
                # Note: Database and Entity services don't typically need explicit disposal
            except Exception as e:
                print(f"Error during disposal: {e}")
        
        self._initialized_services = None
        self._configuration = None
    
    def get_configuration(self) -> Optional[DataConfiguration]:
        """Get the current configuration."""
        return self._configuration
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from all services."""
        if not self._initialized_services:
            return {'error': 'No services initialized'}
        
        try:
            return {
                'market_data_service': self._initialized_services.market_data_service.get_statistics(),
                'history_service': self._initialized_services.history_service.get_statistics(),
                'configuration': {
                    'database_type': self._configuration.database_type if self._configuration else None,
                    'mode': 'backtest' if (self._configuration and self._configuration.data_folder) else 'live',
                    'cache_enabled': self._configuration.enable_caching if self._configuration else None
                }
            }
        except Exception as e:
            return {'error': f'Failed to get statistics: {e}'}


# Convenience functions for common use cases

def create_backtest_data_services(data_folder: str, 
                                start_time: datetime, 
                                end_time: datetime,
                                database_type: str = 'sqlite') -> DataServices:
    """
    Convenience function to create data services for backtesting.
    
    Args:
        data_folder: Path to historical data
        start_time: Backtest start time
        end_time: Backtest end time
        database_type: Database type to use
        
    Returns:
        Initialized DataServices
    """
    loader = DataLoader()
    return loader.load_for_backtest(data_folder, start_time, end_time, database_type)


def create_live_trading_data_services(broker_connection=None,
                                    database_type: str = 'sqlite') -> DataServices:
    """
    Convenience function to create data services for live trading.
    
    Args:
        broker_connection: Broker connection for live data
        database_type: Database type to use
        
    Returns:
        Initialized DataServices
    """
    loader = DataLoader()
    return loader.load_for_live_trading(broker_connection, database_type)


# Example usage
if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    # Example 1: Backtest setup
    print("Example 1: Setting up for backtesting")
    try:
        services = create_backtest_data_services(
            data_folder="/path/to/data",
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 12, 31)
        )
        print("Backtest services initialized successfully")
        print(f"Statistics: {DataLoader().get_statistics()}")
    except Exception as e:
        print(f"Failed to initialize backtest services: {e}")
    
    # Example 2: Live trading setup
    print("\nExample 2: Setting up for live trading")
    try:
        services = create_live_trading_data_services()
        print("Live trading services initialized successfully")
    except Exception as e:
        print(f"Failed to initialize live services: {e}")
    
    # Example 3: Custom configuration
    print("\nExample 3: Custom configuration")
    try:
        config = DataConfiguration(
            database_type='postgresql',
            data_folder="/custom/data/path",
            backtest_start=datetime(2023, 6, 1),
            backtest_end=datetime(2023, 12, 31),
            enable_caching=True,
            max_cache_size=200
        )
        
        loader = DataLoader()
        services = loader.load_with_config(config, mode='backtest')
        print("Custom configuration services initialized successfully")
        
        # Clean up
        loader.dispose()
        
    except Exception as e:
        print(f"Failed with custom configuration: {e}")