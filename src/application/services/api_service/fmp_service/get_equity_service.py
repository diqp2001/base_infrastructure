"""
FMP Equity Data Service
Orchestrates data retrieval from Financial Modeling Prep API and storage to local database.

This service:
1. Instantiates FMP API service and repository
2. Connects to FMP API to retrieve equity data
3. Parses and transforms data into domain entities
4. Stores data in local database via repository
5. Manages configuration and error handling
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from .financial_modeling_prep_api_service import FinancialModelingPrepApiService
from .config_equity_service import FmpEquityServiceConfig, get_default_config
from src.domain.entities.finance.fmp_equity_data import FmpEquityData
from src.infrastructure.repositories.local_repo.finance.fmp_equity_data_repository import FmpEquityDataRepository
from src.infrastructure.database.settings import get_session


class FmpEquityDataService:
    """
    Service for retrieving equity data from FMP API and storing in local database.
    
    This service follows the application layer pattern, orchestrating between:
    - FMP API service (external data source)
    - FmpEquityDataRepository (local database storage)
    - Configuration management
    """
    
    def __init__(self, 
                 session: Optional[Session] = None,
                 config: Optional[FmpEquityServiceConfig] = None):
        """
        Initialize FMP Equity Data Service.
        
        Args:
            session: Database session (creates new if None)
            config: Service configuration (uses default if None)
        """
        self.session = session or get_session()
        self.config = config or get_default_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize FMP API service and repository
        try:
            self.fmp_api = FinancialModelingPrepApiService()
            self.repository = FmpEquityDataRepository(self.session)
            self.logger.info("FMP Equity Data Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize FMP Equity Data Service: {e}")
            raise
    
    def fetch_and_store_quotes(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch current quotes for symbols and store in database.
        
        Args:
            symbols: List of symbols to fetch (uses config symbols if None)
            
        Returns:
            Dictionary with operation results and statistics
        """
        symbols = symbols or self.config.symbols
        results = {
            'success_count': 0,
            'error_count': 0,
            'processed_symbols': [],
            'errors': [],
            'timestamp': datetime.utcnow()
        }
        
        self.logger.info(f"Starting to fetch quotes for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                # Fetch quote data from FMP API
                quote_data = self.fmp_api.get_quote(symbol)
                
                if not quote_data:
                    self.logger.warning(f"No data received for symbol {symbol}")
                    results['error_count'] += 1
                    results['errors'].append(f"No data for {symbol}")
                    continue
                
                # Transform API response to domain entity
                equity_entity = self._transform_quote_to_entity(quote_data)
                
                # Store in database
                stored_entity = self.repository.add_or_update(equity_entity)
                
                results['success_count'] += 1
                results['processed_symbols'].append(symbol)
                
                self.logger.debug(f"Successfully processed {symbol}: {stored_entity.price}")
                
            except Exception as e:
                self.logger.error(f"Error processing symbol {symbol}: {e}")
                results['error_count'] += 1
                results['errors'].append(f"{symbol}: {str(e)}")
        
        self.logger.info(f"Completed quote fetch: {results['success_count']} success, {results['error_count']} errors")
        return results
    
    def fetch_and_store_multiple_quotes(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch multiple quotes in batch and store in database.
        More efficient for large symbol lists.
        
        Args:
            symbols: List of symbols to fetch (uses config symbols if None)
            
        Returns:
            Dictionary with operation results and statistics
        """
        symbols = symbols or self.config.symbols
        results = {
            'success_count': 0,
            'error_count': 0,
            'processed_symbols': [],
            'errors': [],
            'timestamp': datetime.utcnow()
        }
        
        try:
            # Fetch multiple quotes at once
            quotes_data = self.fmp_api.get_quotes(symbols)
            
            if not quotes_data:
                self.logger.error("No data received from bulk quote request")
                results['error_count'] = len(symbols)
                results['errors'].append("Bulk quote request failed")
                return results
            
            # Process each quote
            entities = []
            for quote_data in quotes_data:
                try:
                    entity = self._transform_quote_to_entity(quote_data)
                    entities.append(entity)
                    results['success_count'] += 1
                    results['processed_symbols'].append(entity.symbol)
                except Exception as e:
                    symbol = quote_data.get('symbol', 'UNKNOWN')
                    self.logger.error(f"Error transforming quote for {symbol}: {e}")
                    results['error_count'] += 1
                    results['errors'].append(f"{symbol}: {str(e)}")
            
            # Bulk store entities
            if entities:
                if self.config.enable_bulk_updates:
                    stored_entities = self.repository.bulk_add_or_update(entities)
                    self.logger.info(f"Bulk stored {len(stored_entities)} entities")
                else:
                    for entity in entities:
                        self.repository.add_or_update(entity)
                    self.logger.info(f"Individually stored {len(entities)} entities")
        
        except Exception as e:
            self.logger.error(f"Error in bulk quote fetch: {e}")
            results['error_count'] = len(symbols)
            results['errors'].append(f"Bulk operation failed: {str(e)}")
        
        return results
    
    def fetch_and_store_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company profile data and enhance stored equity data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Company profile data or None if failed
        """
        try:
            profile_data = self.fmp_api.get_company_profile(symbol)
            
            if not profile_data:
                self.logger.warning(f"No company profile data for {symbol}")
                return None
            
            # Update existing entity with company information
            existing_entity = self.repository.get_latest_by_symbol(symbol)
            if existing_entity:
                existing_entity.name = profile_data.get('companyName')
                existing_entity.exchange = profile_data.get('exchangeShortName')
                existing_entity.updated_at = datetime.utcnow()
                
                self.repository.add_or_update(existing_entity)
                self.logger.info(f"Updated company info for {symbol}")
            
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error fetching company profile for {symbol}: {e}")
            return None
    
    def get_stored_data(self, symbol: str, limit: Optional[int] = None) -> List[FmpEquityData]:
        """
        Retrieve stored equity data from database.
        
        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of records to return
            
        Returns:
            List of stored FmpEquityData entities
        """
        return self.repository.get_by_symbol(symbol, limit)
    
    def get_latest_data(self, symbol: str) -> Optional[FmpEquityData]:
        """
        Get the most recent data for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest FmpEquityData entity or None
        """
        return self.repository.get_latest_by_symbol(symbol)
    
    def get_multiple_latest_data(self, symbols: Optional[List[str]] = None) -> List[FmpEquityData]:
        """
        Get latest data for multiple symbols.
        
        Args:
            symbols: List of symbols (uses config symbols if None)
            
        Returns:
            List of latest FmpEquityData entities
        """
        symbols = symbols or self.config.symbols
        return self.repository.get_by_symbols(symbols, limit_per_symbol=1)
    
    def cleanup_old_data(self, symbol: Optional[str] = None) -> int:
        """
        Clean up old data based on retention policy.
        
        Args:
            symbol: Specific symbol to clean (all symbols if None)
            
        Returns:
            Number of records deleted
        """
        symbols_to_clean = [symbol] if symbol else self.config.symbols
        total_deleted = 0
        
        for sym in symbols_to_clean:
            deleted_count = self.repository.delete_old_data(
                sym, self.config.data_retention_days
            )
            total_deleted += deleted_count
            if deleted_count > 0:
                self.logger.info(f"Deleted {deleted_count} old records for {sym}")
        
        return total_deleted
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and statistics.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Check API health
            api_health = self.fmp_api.check_api_health()
            
            # Get database summary
            db_summary = self.repository.get_data_summary()
            
            # Get symbols list
            stored_symbols = self.repository.get_symbols_list()
            
            return {
                'service_status': 'healthy',
                'api_health': api_health,
                'database_summary': db_summary,
                'configured_symbols': self.config.symbols,
                'stored_symbols': stored_symbols,
                'config': {
                    'update_interval': self.config.update_interval_minutes,
                    'retention_days': self.config.data_retention_days,
                    'batch_size': self.config.batch_size
                },
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            return {
                'service_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }
    
    def _transform_quote_to_entity(self, quote_data: Dict[str, Any]) -> FmpEquityData:
        """
        Transform FMP API quote response to FmpEquityData domain entity.
        
        Args:
            quote_data: Quote data from FMP API
            
        Returns:
            FmpEquityData domain entity
        """
        def safe_decimal(value) -> Optional[Decimal]:
            """Safely convert value to Decimal."""
            if value is None or value == "":
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return None
        
        def safe_int(value) -> Optional[int]:
            """Safely convert value to int."""
            if value is None or value == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        
        return FmpEquityData(
            symbol=quote_data.get('symbol', '').upper(),
            price=safe_decimal(quote_data.get('price')),
            change=safe_decimal(quote_data.get('change')),
            changes_percentage=safe_decimal(quote_data.get('changesPercentage')),
            day_low=safe_decimal(quote_data.get('dayLow')),
            day_high=safe_decimal(quote_data.get('dayHigh')),
            year_high=safe_decimal(quote_data.get('yearHigh')),
            year_low=safe_decimal(quote_data.get('yearLow')),
            market_cap=safe_decimal(quote_data.get('marketCap')),
            price_avg_50=safe_decimal(quote_data.get('priceAvg50')),
            price_avg_200=safe_decimal(quote_data.get('priceAvg200')),
            volume=safe_int(quote_data.get('volume')),
            avg_volume=safe_int(quote_data.get('avgVolume')),
            exchange=quote_data.get('exchange'),
            name=quote_data.get('name'),
            pe=safe_decimal(quote_data.get('pe')),
            eps=safe_decimal(quote_data.get('eps')),
            timestamp=datetime.utcnow()
        )
    
    def run_update_cycle(self) -> Dict[str, Any]:
        """
        Run a complete update cycle: fetch data, store, and cleanup.
        This is the main method for scheduled operations.
        
        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.utcnow()
        self.logger.info("Starting FMP equity data update cycle")
        
        # Fetch and store latest quotes
        if self.config.enable_bulk_updates:
            fetch_results = self.fetch_and_store_multiple_quotes()
        else:
            fetch_results = self.fetch_and_store_quotes()
        
        # Cleanup old data
        cleanup_count = self.cleanup_old_data()
        
        # Get final status
        status = self.get_service_status()
        
        cycle_end = datetime.utcnow()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        results = {
            'cycle_start': cycle_start,
            'cycle_end': cycle_end,
            'duration_seconds': cycle_duration,
            'fetch_results': fetch_results,
            'cleanup_count': cleanup_count,
            'final_status': status
        }
        
        self.logger.info(f"Update cycle completed in {cycle_duration:.2f} seconds")
        return results


# Convenience function for external usage
def create_fmp_equity_service(config: Optional[FmpEquityServiceConfig] = None) -> FmpEquityDataService:
    """
    Factory function to create FmpEquityDataService with default configuration.
    
    Args:
        config: Optional service configuration
        
    Returns:
        Initialized FmpEquityDataService instance
    """
    return FmpEquityDataService(config=config)
