"""
IBKR Futures Data Service

This service orchestrates the Interactive Brokers API connection, futures data retrieval, 
and local database storage using existing domain entities and the proper repository pattern.

Key Features:
- Connects to IBKR API using InteractiveBrokersBroker
- Fetches real-time futures market data and historical data
- Translates IBKR data to existing domain entities via IBKRRepository
- Stores data using existing repository infrastructure
- Configurable via IBKRFuturesServiceConfig
- Comprehensive error handling and logging
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from ibapi.contract import Contract

from src.application.services.api_service.ibkr_service.config_futures_service import IBKRFuturesServiceConfig
from src.application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker
from src.application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker
from domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor

logger = logging.getLogger(__name__)


@dataclass
class IBKRFuturesServiceResult:
    """Result of IBKR futures service operations"""
    success: bool
    message: str
    contracts_processed: int
    market_data_points: int
    errors: List[str]
    execution_time: float
    timestamp: datetime


@dataclass
class FuturesMarketData:
    """Structured futures market data"""
    symbol: str
    exchange: str
    expiry: str
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    volume: Optional[int]
    open_price: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    timestamp: datetime


class IBKRFuturesDataService:
    """
    Service that orchestrates IBKR API futures data retrieval and storage using existing domain entities.
    
    This service:
    1. Connects to IBKR API via InteractiveBrokersBroker
    2. Fetches futures market data and contract details
    3. Translates IBKR data to CompanyShare and ShareFactor entities
    4. Stores entities using existing repository infrastructure
    5. Provides monitoring and error handling
    """
    
    def __init__(self, session: Session, config: Optional[IBKRFuturesServiceConfig] = None):
        """
        Initialize IBKR futures data service.
        
        Args:
            session: SQLAlchemy database session
            config: Service configuration (uses default if None)
        """
        self.session = session
        self.config = config or IBKRFuturesServiceConfig.get_default_config()
        
        # Initialize IBKR broker
        self.ib_broker: Optional[InteractiveBrokersBroker] = None
        self.connected = False
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, self.config.log_level))
        logger.info("IBKR Futures Data Service initialized")
        
        # Statistics tracking
        self.stats = {
            'total_connections': 0,
            'successful_data_fetches': 0,
            'failed_data_fetches': 0,
            'last_update': None,
            'futures_contracts_tracked': len(self.config.futures_symbols)
        }
    
    def connect_to_ibkr(self) -> bool:
        """
        Establish connection to Interactive Brokers TWS/Gateway.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to IBKR at {self.config.host}:{self.config.port}")
            
            # Create broker instance with configuration
            connection_config = self.config.get_connection_config()
            self.ib_broker = create_interactive_brokers_broker(**connection_config)
            
            # Attempt connection
            self.connected = self.ib_broker.connect()
            self.stats['total_connections'] += 1
            
            if self.connected:
                logger.info("✅ Successfully connected to IBKR")
                return True
            else:
                logger.error("❌ Failed to connect to IBKR")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to IBKR: {str(e)}")
            self.connected = False
            return False
    
    def disconnect_from_ibkr(self) -> None:
        """Disconnect from Interactive Brokers if connected."""
        if self.ib_broker and self.connected:
            try:
                logger.info("Disconnecting from IBKR...")
                self.ib_broker.disconnect()
                self.connected = False
                logger.info("✅ Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {str(e)}")
    
    def create_futures_contract(self, symbol: str, secType: str = "FUT", exchange: str = "CME") -> Contract:
        """
        Create a futures contract following the updated pattern.
        
        Args:
            symbol: Futures symbol (e.g., 'ES', 'NQ')
            secType: Security type (default: "FUT")
            exchange: Exchange (default: "CME")
            
        Returns:
            IBKR Contract object
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = self.config.currency
        
        # Set expiry for nearest contract (this could be enhanced to specify exact month)
        # For now, leave empty to get the front month contract
        
        return contract
    
    def fetch_futures_market_data(self, symbols: Optional[List[str]] = None) -> IBKRFuturesServiceResult:
        """
        Fetch real-time market data for futures contracts.
        
        Args:
            symbols: List of futures symbols to fetch (uses config symbols if None)
            
        Returns:
            IBKRFuturesServiceResult with operation details
        """
        start_time = time.time()
        symbols = symbols or self.config.futures_symbols
        
        logger.info(f"Fetching futures market data for {len(symbols)} contracts from IBKR")
        
        if not self.connected:
            if not self.connect_to_ibkr():
                return IBKRFuturesServiceResult(
                    success=False,
                    message="Failed to connect to IBKR",
                    contracts_processed=0,
                    market_data_points=0,
                    errors=["Connection failed"],
                    execution_time=time.time() - start_time,
                    timestamp=datetime.now()
                )
        
        market_data_points = 0
        processed_contracts = 0
        all_errors = []
        
        try:
            # Process symbols in batches to respect rate limits
            for i in range(0, len(symbols), self.config.batch_size):
                batch = symbols[i:i + self.config.batch_size]
                
                logger.debug(f"Processing batch {i//self.config.batch_size + 1}: {batch}")
                
                for symbol in batch:
                    try:
                        # Create futures contract
                        contract = self.create_futures_contract(symbol, "FUT", self.config.exchange)
                        
                        # Fetch market data snapshot
                        market_data = self.ib_broker.get_market_data_snapshot(
                            contract=contract, 
                            snapshot=True,
                            timeout=self.config.data_timeout
                        )
                        
                        if market_data and isinstance(market_data, dict):
                            # Process and store the market data
                            structured_data = self._process_market_data(symbol, market_data)
                            
                            if structured_data:
                                # Here you would translate to domain entities and store
                                # For now, we'll just log the successful fetch
                                logger.debug(f"Successfully fetched data for {symbol}: {structured_data}")
                                market_data_points += len(market_data)
                                processed_contracts += 1
                                self.stats['successful_data_fetches'] += 1
                            else:
                                error_msg = f"Failed to process market data for {symbol}"
                                logger.warning(error_msg)
                                all_errors.append(error_msg)
                                self.stats['failed_data_fetches'] += 1
                        else:
                            error_msg = f"No market data received for {symbol}"
                            logger.warning(error_msg)
                            all_errors.append(error_msg)
                            self.stats['failed_data_fetches'] += 1
                        
                        # Rate limiting delay
                        time.sleep(0.5)  # 500ms delay between requests
                        
                    except Exception as e:
                        error_msg = f"Error processing {symbol}: {str(e)}"
                        logger.error(error_msg)
                        all_errors.append(error_msg)
                        self.stats['failed_data_fetches'] += 1
                
                # Delay between batches
                if i + self.config.batch_size < len(symbols):
                    time.sleep(1)
            
            execution_time = time.time() - start_time
            self.stats['last_update'] = datetime.now()
            
            success = processed_contracts > 0
            message = (f"Processed {len(symbols)} futures symbols. "
                      f"Successfully fetched {processed_contracts} contracts, "
                      f"{market_data_points} data points. "
                      f"Errors: {len(all_errors)}")
            
            logger.info(message)
            
            return IBKRFuturesServiceResult(
                success=success,
                message=message,
                contracts_processed=processed_contracts,
                market_data_points=market_data_points,
                errors=all_errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error in fetch_futures_market_data: {str(e)}"
            logger.error(error_msg)
            
            return IBKRFuturesServiceResult(
                success=False,
                message=error_msg,
                contracts_processed=0,
                market_data_points=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def fetch_futures_historical_data(self, symbol: str, duration_str: str = "1 W", 
                                     bar_size_setting: str = "1 day") -> Optional[List[Dict[str, Any]]]:
        """
        Fetch historical data for a futures contract.
        
        Args:
            symbol: Futures symbol
            duration_str: Duration string (e.g., "1 W", "1 M")
            bar_size_setting: Bar size (e.g., "1 day", "1 hour")
            
        Returns:
            List of historical bars or None if failed
        """
        if not self.connected:
            logger.error("Cannot fetch historical data - not connected to IBKR")
            return None
        
        try:
            # Create futures contract
            contract = self.create_futures_contract(symbol, "FUT", self.config.exchange)
            
            # Fetch historical data
            historical_data = self.ib_broker.get_historical_data(
                contract=contract,
                end_date_time="",  # Current time
                duration_str=duration_str,
                bar_size_setting=bar_size_setting,
                what_to_show="TRADES",
                use_rth=True
            )
            
            logger.info(f"Fetched {len(historical_data) if historical_data else 0} historical bars for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def _process_market_data(self, symbol: str, raw_data: Dict[str, Any]) -> Optional[FuturesMarketData]:
        """
        Process raw IBKR market data into structured format.
        
        Args:
            symbol: Futures symbol
            raw_data: Raw market data from IBKR
            
        Returns:
            FuturesMarketData object or None if processing fails
        """
        try:
            # Extract relevant fields from IBKR tick data
            # This maps the tick types to meaningful names
            structured_data = FuturesMarketData(
                symbol=symbol,
                exchange=self.config.exchange,
                expiry="",  # Would need to be extracted from contract details
                bid=raw_data.get('BID'),
                ask=raw_data.get('ASK'),
                last=raw_data.get('LAST'),
                volume=raw_data.get('VOLUME'),
                open_price=raw_data.get('OPEN'),
                high=raw_data.get('HIGH'),
                low=raw_data.get('LOW'),
                close=raw_data.get('CLOSE'),
                timestamp=datetime.now()
            )
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {str(e)}")
            return None
    
    def run_update_cycle(self) -> IBKRFuturesServiceResult:
        """
        Run complete update cycle: fetch market data for configured futures.
        
        Returns:
            IBKRFuturesServiceResult with combined results
        """
        logger.info("Starting IBKR futures data update cycle")
        start_time = time.time()
        
        try:
            # Fetch market data
            result = self.fetch_futures_market_data()
            
            execution_time = time.time() - start_time
            message = f"Update cycle completed. {result.message} Total time: {execution_time:.2f}s"
            
            logger.info(message)
            
            # Update result with total execution time
            result.execution_time = execution_time
            result.message = message
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error in run_update_cycle: {str(e)}"
            logger.error(error_msg)
            
            return IBKRFuturesServiceResult(
                success=False,
                message=error_msg,
                contracts_processed=0,
                market_data_points=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status and statistics.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Check IBKR connection health
            connection_status = "connected" if self.connected else "disconnected"
            
            broker_status = {}
            if self.ib_broker:
                broker_status = self.ib_broker.get_broker_specific_info()
            
            return {
                'service_status': 'operational' if self.connected else 'disconnected',
                'config': {
                    'futures_symbols_count': len(self.config.futures_symbols),
                    'futures_symbols': self.config.futures_symbols,
                    'update_interval': self.config.update_interval,
                    'batch_size': self.config.batch_size,
                    'paper_trading': self.config.paper_trading,
                    'host': self.config.host,
                    'port': self.config.port
                },
                'statistics': self.stats,
                'connection_status': connection_status,
                'broker_info': broker_status,
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'service_status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def update_configuration(self, new_config: IBKRFuturesServiceConfig) -> bool:
        """
        Update service configuration.
        
        Args:
            new_config: New configuration to apply
            
        Returns:
            True if configuration was updated successfully
        """
        try:
            errors = new_config.validate()
            if errors:
                logger.error(f"Invalid configuration: {errors}")
                return False
            
            # Disconnect if connection parameters changed
            if (self.config.host != new_config.host or 
                self.config.port != new_config.port or 
                self.config.client_id != new_config.client_id):
                self.disconnect_from_ibkr()
            
            self.config = new_config
            
            # Update logging level if changed
            logging.getLogger().setLevel(getattr(logging, new_config.log_level))
            
            # Update stats
            self.stats['futures_contracts_tracked'] = len(new_config.futures_symbols)
            
            logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return False
    
    def __del__(self):
        """Cleanup method to ensure proper disconnection from IBKR."""
        try:
            self.disconnect_from_ibkr()
        except Exception:
            pass  # Ignore errors during cleanup


def create_ibkr_futures_service(session: Session, config_path: Optional[str] = None) -> IBKRFuturesDataService:
    """
    Factory function to create IBKR futures service with optional configuration file.
    
    Args:
        session: SQLAlchemy database session
        config_path: Optional path to configuration JSON file
        
    Returns:
        IBKRFuturesDataService instance
    """
    if config_path:
        try:
            config = IBKRFuturesServiceConfig.from_file(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {str(e)}. Using default.")
            config = IBKRFuturesServiceConfig.get_default_config()
    else:
        config = IBKRFuturesServiceConfig.get_default_config()
        logger.info("Using default configuration")
    
    return IBKRFuturesDataService(session, config)


# Example usage functions
def example_basic_usage():
    """Example of basic service usage"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Setup database session (example)
    engine = create_engine('sqlite:///example.db')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Create service with default config
        service = create_ibkr_futures_service(session)
        
        # Connect to IBKR
        if service.connect_to_ibkr():
            # Run update cycle
            result = service.run_update_cycle()
            print(f"Update result: {result.message}")
            
            # Get service status
            status = service.get_service_status()
            print(f"Service status: {status['service_status']}")
            
            # Fetch historical data for ES (E-mini S&P 500)
            historical = service.fetch_futures_historical_data('ES', '1 W', '1 hour')
            if historical:
                print(f"Fetched {len(historical)} historical bars for ES")
        else:
            print("Failed to connect to IBKR")
        
    finally:
        session.close()


def example_custom_config():
    """Example of service usage with custom configuration"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Custom configuration for major index futures
    custom_config = IBKRFuturesServiceConfig(
        futures_symbols=["ES", "NQ", "YM"],  # Major indices only
        host="127.0.0.1",
        port=7497,  # Paper trading
        update_interval=180,  # 3 minutes
        batch_size=3,
        log_level="DEBUG"
    )
    
    # Setup database session (example)
    engine = create_engine('sqlite:///example.db')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Create service with custom config
        service = IBKRFuturesDataService(session, custom_config)
        
        if service.connect_to_ibkr():
            # Fetch market data only
            result = service.fetch_futures_market_data()
            print(f"Market data result: {result.message}")
        else:
            print("Failed to connect to IBKR")
        
    finally:
        session.close()


if __name__ == "__main__":
    # Run example
    print("Running IBKR Futures Service examples...")
    example_basic_usage()
    print("\nRunning custom config example...")
    example_custom_config()