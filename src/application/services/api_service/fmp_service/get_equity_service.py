"""
FMP Equity Data Service

This service orchestrates the FMP API connection, data retrieval, and local database storage
using existing domain entities (CompanyShare, ShareFactor) and the proper repository pattern.

Key Features:
- Connects to FMP API using FinancialModelingPrepApiService
- Translates FMP data to existing domain entities via FmpRepository
- Stores data using existing repository infrastructure
- Configurable via FmpEquityServiceConfig
- Comprehensive error handling and logging
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import FinancialModelingPrepApiService
from src.application.services.api_service.fmp_service.config_equity_service import FmpEquityServiceConfig
from src.infrastructure.repositories.fmp_repository import FmpRepository, FmpDataTranslation
from src.domain.entities.finance.financial_assets.company_share import CompanyShare
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor

logger = logging.getLogger(__name__)


@dataclass
class FmpEquityServiceResult:
    """Result of FMP equity service operations"""
    success: bool
    message: str
    company_shares_created: int
    share_factors_created: int
    errors: List[str]
    execution_time: float
    timestamp: datetime


class FmpEquityDataService:
    """
    Service that orchestrates FMP API data retrieval and storage using existing domain entities.
    
    This service:
    1. Connects to FMP API via FinancialModelingPrepApiService
    2. Translates FMP data to CompanyShare and ShareFactor entities via FmpRepository
    3. Stores entities using existing repository infrastructure
    4. Provides monitoring and error handling
    """
    
    def __init__(self, session: Session, config: Optional[FmpEquityServiceConfig] = None):
        """
        Initialize FMP equity data service.
        
        Args:
            session: SQLAlchemy database session
            config: Service configuration (uses default if None)
        """
        self.session = session
        self.config = config or FmpEquityServiceConfig.get_default_config()
        
        # Initialize FMP API service
        self.fmp_api_service = FinancialModelingPrepApiService()
        
        # Initialize FMP repository for translation
        self.fmp_repository = FmpRepository(session)
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, self.config.log_level))
        logger.info("FMP Equity Data Service initialized")
        
        # Statistics tracking
        self.stats = {
            'total_api_calls': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'last_update': None
        }
    
    def fetch_and_store_quotes(self, symbols: Optional[List[str]] = None) -> FmpEquityServiceResult:
        """
        Fetch quotes from FMP API and store as CompanyShare and ShareFactor entities.
        
        Args:
            symbols: List of symbols to fetch (uses config symbols if None)
            
        Returns:
            FmpEquityServiceResult with operation details
        """
        start_time = time.time()
        symbols = symbols or self.config.symbols
        
        logger.info(f"Fetching quotes for {len(symbols)} symbols from FMP API")
        
        all_company_shares = []
        all_share_factors = []
        all_errors = []
        
        try:
            # Process symbols in batches to respect rate limits
            for i in range(0, len(symbols), self.config.batch_size):
                batch = symbols[i:i + self.config.batch_size]
                
                logger.debug(f"Processing batch {i//self.config.batch_size + 1}: {batch}")
                
                # Fetch quotes for batch
                if len(batch) == 1:
                    # Single quote
                    quote_data = self.fmp_api_service.get_quote(batch[0])
                    if quote_data:
                        quotes_data = [quote_data]
                    else:
                        quotes_data = []
                else:
                    # Multiple quotes
                    quotes_data = self.fmp_api_service.get_quotes(batch) or []
                
                self.stats['total_api_calls'] += 1
                
                if not quotes_data:
                    error_msg = f"No data received for batch: {batch}"
                    logger.warning(error_msg)
                    all_errors.append(error_msg)
                    self.stats['failed_translations'] += len(batch)
                    continue
                
                # Translate and store quotes
                translation_result = self.fmp_repository.translate_and_store_quotes_batch(quotes_data)
                
                all_company_shares.extend(translation_result.company_shares)
                all_share_factors.extend(translation_result.share_factors)
                all_errors.extend(translation_result.errors)
                
                self.stats['successful_translations'] += translation_result.processed_count
                self.stats['failed_translations'] += translation_result.skipped_count
                
                # Rate limiting delay between batches
                if i + self.config.batch_size < len(symbols):
                    time.sleep(1)  # 1 second delay between batches
            
            execution_time = time.time() - start_time
            self.stats['last_update'] = datetime.now()
            
            success = len(all_company_shares) > 0 or len(all_share_factors) > 0
            message = (f"Processed {len(symbols)} symbols. "
                      f"Created {len(all_company_shares)} company shares, "
                      f"{len(all_share_factors)} share factors. "
                      f"Errors: {len(all_errors)}")
            
            logger.info(message)
            
            return FmpEquityServiceResult(
                success=success,
                message=message,
                company_shares_created=len(all_company_shares),
                share_factors_created=len(all_share_factors),
                errors=all_errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error in fetch_and_store_quotes: {str(e)}"
            logger.error(error_msg)
            
            return FmpEquityServiceResult(
                success=False,
                message=error_msg,
                company_shares_created=0,
                share_factors_created=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def fetch_and_store_company_profiles(self, symbols: Optional[List[str]] = None) -> FmpEquityServiceResult:
        """
        Fetch company profiles from FMP API and store as CompanyShare entities.
        
        Args:
            symbols: List of symbols to fetch (uses config symbols if None)
            
        Returns:
            FmpEquityServiceResult with operation details
        """
        start_time = time.time()
        symbols = symbols or self.config.symbols
        
        logger.info(f"Fetching company profiles for {len(symbols)} symbols from FMP API")
        
        company_shares_created = 0
        errors = []
        
        try:
            for symbol in symbols:
                try:
                    # Fetch company profile
                    profile_data = self.fmp_api_service.get_company_profile(symbol)
                    self.stats['total_api_calls'] += 1
                    
                    if not profile_data:
                        error_msg = f"No profile data received for {symbol}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # Translate to CompanyShare
                    company_share = self.fmp_repository.translate_profile_to_company_share(profile_data)
                    
                    if company_share:
                        # Store in repository (handled by FmpRepository.translate_and_store methods)
                        company_shares_created += 1
                        self.stats['successful_translations'] += 1
                        logger.debug(f"Successfully processed profile for {symbol}")
                    else:
                        error_msg = f"Failed to translate profile for {symbol}"
                        errors.append(error_msg)
                        self.stats['failed_translations'] += 1
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error processing profile for {symbol}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    self.stats['failed_translations'] += 1
            
            execution_time = time.time() - start_time
            self.stats['last_update'] = datetime.now()
            
            success = company_shares_created > 0
            message = f"Processed profiles for {len(symbols)} symbols. Created {company_shares_created} company shares. Errors: {len(errors)}"
            
            logger.info(message)
            
            return FmpEquityServiceResult(
                success=success,
                message=message,
                company_shares_created=company_shares_created,
                share_factors_created=0,  # Profiles don't create factors
                errors=errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error in fetch_and_store_company_profiles: {str(e)}"
            logger.error(error_msg)
            
            return FmpEquityServiceResult(
                success=False,
                message=error_msg,
                company_shares_created=0,
                share_factors_created=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def run_update_cycle(self) -> FmpEquityServiceResult:
        """
        Run complete update cycle: fetch quotes and profiles for configured symbols.
        
        Returns:
            FmpEquityServiceResult with combined results
        """
        logger.info("Starting FMP equity data update cycle")
        start_time = time.time()
        
        all_errors = []
        total_company_shares = 0
        total_share_factors = 0
        
        try:
            # Fetch quotes
            quotes_result = self.fetch_and_store_quotes()
            total_company_shares += quotes_result.company_shares_created
            total_share_factors += quotes_result.share_factors_created
            all_errors.extend(quotes_result.errors)
            
            # Fetch profiles for additional company information
            profiles_result = self.fetch_and_store_company_profiles()
            total_company_shares += profiles_result.company_shares_created
            all_errors.extend(profiles_result.errors)
            
            execution_time = time.time() - start_time
            success = total_company_shares > 0 or total_share_factors > 0
            message = f"Update cycle completed. Total: {total_company_shares} company shares, {total_share_factors} share factors. Errors: {len(all_errors)}"
            
            logger.info(message)
            
            return FmpEquityServiceResult(
                success=success,
                message=message,
                company_shares_created=total_company_shares,
                share_factors_created=total_share_factors,
                errors=all_errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error in run_update_cycle: {str(e)}"
            logger.error(error_msg)
            
            return FmpEquityServiceResult(
                success=False,
                message=error_msg,
                company_shares_created=0,
                share_factors_created=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def get_latest_data(self, symbol: str) -> Optional[CompanyShare]:
        """
        Get latest CompanyShare data for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            CompanyShare entity or None if not found
        """
        try:
            shares = self.fmp_repository.company_share_repo.get_by_ticker(symbol.upper())
            return shares[0] if shares else None
        except Exception as e:
            logger.error(f"Error retrieving data for {symbol}: {str(e)}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status and statistics.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Get repository statistics
            repo_stats = self.fmp_repository.get_statistics()
            
            # Check FMP API health
            api_health = self.fmp_api_service.check_api_health()
            
            return {
                'service_status': 'operational',
                'config': {
                    'symbols_count': len(self.config.symbols),
                    'symbols': self.config.symbols,
                    'update_interval': self.config.update_interval,
                    'batch_size': self.config.batch_size,
                    'use_free_tier': self.config.use_free_tier
                },
                'statistics': self.stats,
                'database_summary': repo_stats,
                'api_health': api_health,
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'service_status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def cleanup_old_data(self) -> Dict[str, Any]:
        """
        Cleanup old data based on configuration settings.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting data cleanup")
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.max_days_to_keep)
            
            # This would implement cleanup logic
            # For now, return placeholder
            return {
                'cleanup_completed': True,
                'cutoff_date': cutoff_date.isoformat(),
                'records_cleaned': 0,
                'message': 'Cleanup functionality placeholder - would clean data older than cutoff date'
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {
                'cleanup_completed': False,
                'error': str(e)
            }
    
    def update_configuration(self, new_config: FmpEquityServiceConfig) -> bool:
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
            
            self.config = new_config
            
            # Update logging level if changed
            logging.getLogger().setLevel(getattr(logging, new_config.log_level))
            
            logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return False


def create_fmp_equity_service(session: Session, config_path: Optional[str] = None) -> FmpEquityDataService:
    """
    Factory function to create FMP equity service with optional configuration file.
    
    Args:
        session: SQLAlchemy database session
        config_path: Optional path to configuration JSON file
        
    Returns:
        FmpEquityDataService instance
    """
    if config_path:
        try:
            config = FmpEquityServiceConfig.from_file(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {str(e)}. Using default.")
            config = FmpEquityServiceConfig.get_default_config()
    else:
        config = FmpEquityServiceConfig.get_default_config()
        logger.info("Using default configuration")
    
    return FmpEquityDataService(session, config)


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
        service = create_fmp_equity_service(session)
        
        # Run update cycle
        result = service.run_update_cycle()
        print(f"Update result: {result.message}")
        
        # Get service status
        status = service.get_service_status()
        print(f"Service status: {status['service_status']}")
        
        # Get latest data for a symbol
        aapl_data = service.get_latest_data('AAPL')
        if aapl_data:
            print(f"AAPL data: {aapl_data}")
        
    finally:
        session.close()


def example_custom_config():
    """Example of service usage with custom configuration"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Custom configuration
    custom_config = FmpEquityServiceConfig(
        symbols=["AAPL", "MSFT", "GOOGL"],
        update_interval=600,  # 10 minutes
        batch_size=3,
        use_free_tier=True,
        log_level="DEBUG"
    )
    
    # Setup database session (example)
    engine = create_engine('sqlite:///example.db')
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Create service with custom config
        service = FmpEquityDataService(session, custom_config)
        
        # Fetch quotes only
        result = service.fetch_and_store_quotes()
        print(f"Quotes result: {result.message}")
        
    finally:
        session.close()


if __name__ == "__main__":
    # Run example
    print("Running FMP Equity Service examples...")
    example_basic_usage()
    print("\nRunning custom config example...")
    example_custom_config()