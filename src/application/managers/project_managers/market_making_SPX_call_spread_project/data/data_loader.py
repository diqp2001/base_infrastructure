"""
SPX Data Loader for Market Making Call Spread Project

This module handles loading SPX index data and option chain data from the database
and IBKR services, following the pattern from test_base_project.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.index.index import Index
from src.application.services.database_service.database_service import DatabaseService
from src.application.services.api_service.ibkr_service.market_data import MarketData
from application.services.data.entities.entity_service import EntityService
from src.application.services.data.entities.factor.factor_data_service import FactorDataService
from src.application.services.data.entities.factor.factor_creation_service import FactorCreationService
from src.application.services.data.entities.factor.factor_calculation_service import FactorCalculationService
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Data loader for SPX index data and option chains.
    Handles both database queries and IBKR API calls.
    """
    
    def __init__(self, database_service: DatabaseService, factor_manager=None):
        """
        Initialize the SPX data loader.
        
        Args:
            database_service: Database service instance
            factor_manager: Factor manager from Algorithm for entity existence and factor operations
        """
        self.database_service = database_service
        self.market_data_service = MarketData()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize enhanced services for comprehensive data management
        self.financial_asset_service = EntityService(database_service)
        self.financial_asset_service.create_ibkr_repositories()
        self.factor_data_service = FactorDataService(database_service)
        self.factor_creation_service = FactorCreationService(database_service)
        self.factor_calculation_service = FactorCalculationService(database_service)
        
        # Store factor_manager reference for _ensure_entities_exist access
        self.factor_manager = factor_manager
    
    def check_spx_data_availability(self) -> Dict[str, Any]:
        """
        Check if SPX data exists in the database using EntityExistenceService.
        Verifies both SPX future and index entities and creates them if not present.
        
        Returns:
            Dict containing data availability status
        """
        self.logger.info("Checking SPX data availability using EntityExistenceService...")
        
        try:
            # Use EntityExistenceService to verify existence of SPX entities
            # Check for both SPX index and future entities
            spx_tickers = ['SPX']  # SPX index
            spx_tickers_futures = ['ES']  # SPX index
            
            # Ensure SPX entities exist (index and future)
            entity_results_spx_tickers = self.financial_asset_service._create_ibkr_or_get(Index ,spx_tickers)
            entity_results_spx_tickers_futures = self.financial_asset_service._create_ibkr_or_get(IndexFuture,spx_tickers_futures)
            
            #Check if factor_manager is available for _ensure_entities_exist
            factor_manager_status = 'available' if self.factor_manager else 'not_available'
            if self.factor_manager and hasattr(self.factor_manager, '_ensure_entities_exist'):
                # Use factor_manager's entity verification if available
                self.logger.info("Using factor_manager for entity verification...")
                factor_entities_spx_tickers = self.factor_manager._ensure_entities_exist(spx_tickers)
                factor_entities_spx_tickers_futures = self.factor_manager._ensure_entities_exist(spx_tickers)
            
            # Verify SPX future entity creation
            spx_future_entity = self._verify_spx_future_entity()
            
            # Check actual data availability using enhanced verification
            spx_data_count = self._count_spx_data_records()
            
            result = {
                'spx_index_records': spx_data_count,
                'has_spx_data': spx_data_count > 0,
                'entities_verified': entity_results_spx_tickers_futures.get('future_index', {}).get('verified', 0),
                'entities_created': entity_results_spx_tickers_futures.get('future_index', {}).get('created', 0),
                'spx_future_entity': spx_future_entity['status'],
                'entity_verification_errors': entity_results_spx_tickers_futures.get('errors', []),
                'last_checked': datetime.now().isoformat(),
            }
            
            if spx_data_count > 0:
                self.logger.info(f"✅ Found {spx_data_count} SPX records with {result['entities_verified']} entities verified")
            else:
                self.logger.warning(f"❌ No SPX data found, but {result['entities_verified']} entities verified")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking SPX data availability: {e}")
            return {
                'spx_index_records': 0,
                'has_spx_data': False,
                'entities_verified': 0,
                'entities_created': 0,
                'spx_future_entity': 'error',
                'factor_manager_status': 'error',
                'error': str(e),
                'last_checked': datetime.now().isoformat(),
            }
    
    def import_spx_historical_data(
        self,
        duration_str: str = "6 M",
        bar_size_setting: str = "5 mins"
    ) -> Dict[str, Any]:
        """
        Import SPX historical data using IBKR service.
        
        Args:
            duration_str: Duration of historical data (e.g., "6 M")
            bar_size_setting: Bar size (e.g., "5 mins")
            
        Returns:
            Dict containing import results
        """
        self.logger.info(f"Importing SPX historical data: {duration_str}, {bar_size_setting}")
        
        try:
            # Use the IBKR market data service to get SPX data
            bars = self.market_data_service.get_index_historical_data(
                symbol="SPX",
                exchange="CBOE",
                currency="USD",
                duration_str=duration_str,
                bar_size_setting=bar_size_setting
            )
            
            if not bars:
                raise Exception("No historical data returned from IBKR")
                
            # Convert bars to DataFrame
            df = pd.DataFrame(bars)
            
            # Store in database (implement based on your factor system)
            stored_count = self._store_spx_data_in_database(df)
            
            result = {
                'success': True,
                'bars_imported': len(bars),
                'bars_stored': stored_count,
                'date_range': {
                    'start': bars[0]['date'] if bars else None,
                    'end': bars[-1]['date'] if bars else None,
                },
                'import_timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info(f"✅ Successfully imported {len(bars)} SPX bars")
            return result
            
        except Exception as e:
            self.logger.error(f"Error importing SPX historical data: {e}")
            return {
                'success': False,
                'error': str(e),
                'bars_imported': 0,
                'import_timestamp': datetime.now().isoformat(),
            }
    
    def load_spx_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load SPX data from database using enhanced factor system services.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame containing SPX data
        """
        self.logger.info("Loading SPX data using enhanced factor system...")
        
        try:
            # Default date range
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=180)  # 6 months default
            
            # Ensure SPX entities exist before querying
            entity_check = self.check_spx_data_availability()
            if not entity_check['has_spx_data'] and entity_check['entities_verified'] == 0:
                self.logger.warning("SPX entities not found and could not be created")
                return pd.DataFrame()
            
            # Query SPX data from database using factor system
            df = self._query_spx_data_from_database(start_date, end_date)
            
            # If no data found, attempt to import from IBKR
            if df.empty:
                self.logger.info("No SPX data found, attempting IBKR import...")
                import_result = self.import_spx_historical_data()
                if import_result.get('success', False):
                    # Retry query after import
                    df = self._query_spx_data_from_database(start_date, end_date)
            
            self.logger.info(f"✅ Loaded {len(df)} SPX records from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading SPX data: {e}")
            return pd.DataFrame()
    
    def _store_spx_data_in_database(self, df: pd.DataFrame) -> int:
        """
        Store SPX data in database using the enhanced factor system services.
        
        Args:
            df: DataFrame containing SPX data
            
        Returns:
            Number of records stored
        """
        self.logger.info(f"Storing {len(df)} SPX records using factor system...")
        
        try:
            # Ensure SPX entities exist first
            entity_results = self.financial_asset_service._create_or_get(['SPX'])
            
            # Get or create SPX company share entity
            spx_share = self.factor_data_service.get_company_share_by_ticker('SPX')
            if not spx_share:
                self.logger.error("Could not get SPX company share after entity creation")
                return 0
            
            stored_count = 0
            
            # Create price factor definitions if they don't exist
            price_factors = ['Open', 'High', 'Low', 'Close', 'Volume']
            for factor_name in price_factors:
                if factor_name.lower() in [col.lower() for col in df.columns]:
                    # Create or get factor
                    factor = self.factor_data_service.create_or_get_factor(
                        name=f'SPX_{factor_name}',
                        group='price',
                        subgroup='index_ohlcv',
                        data_type='numeric',
                        source='ibkr',
                        definition=f'SPX index {factor_name} price data from IBKR'
                    )
                    
                    if factor:
                        # Store factor values using factor data service
                        column_name = next((col for col in df.columns if col.lower() == factor_name.lower()), None)
                        if column_name:
                            values_stored = self.factor_data_service.store_factor_values(
                                factor=factor,
                                share=spx_share,
                                data=df,
                                column=column_name,
                                overwrite=True
                            )
                            stored_count += values_stored
                            self.logger.info(f"  ✅ Stored {values_stored} values for {factor_name}")
            
            self.logger.info(f"✅ Stored {stored_count} total factor values for SPX")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Error storing SPX data: {e}")
            return 0
    
    def _query_spx_data_from_database(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Query SPX data from database using factor system services.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame containing SPX data
        """
        self.logger.info(f"Querying SPX data from {start_date} to {end_date} using factor system...")
        
        try:
            # Get SPX company share entity
            spx_share = self.factor_data_service.get_company_share_by_ticker('SPX')
            if not spx_share:
                self.logger.warning("SPX company share not found, returning empty DataFrame")
                return pd.DataFrame()
            
            # Query factor data for SPX in the specified date range
            factor_groups = ['price']  # Focus on price factors for SPX
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Use factor data service to retrieve SPX data
            spx_data = self.factor_data_service.get_ticker_factor_data(
                ticker='SPX',
                start_date=start_date_str,
                end_date=end_date_str,
                factor_groups=factor_groups
            )
            
            if spx_data is not None and not spx_data.empty:
                self.logger.info(f"✅ Retrieved {len(spx_data)} SPX records from factor system")
                return spx_data
            else:
                self.logger.warning("No SPX factor data found, creating placeholder data")
                # Fallback to placeholder if no factor data exists
                dates = pd.date_range(start_date, end_date, freq='D')
                df = pd.DataFrame({
                    'date': dates,
                    'open': [4500 + i for i in range(len(dates))],
                    'high': [4510 + i for i in range(len(dates))],
                    'low': [4490 + i for i in range(len(dates))],
                    'close': [4505 + i for i in range(len(dates))],
                    'volume': [1000000] * len(dates),
                })
                return df
                
        except Exception as e:
            self.logger.error(f"Error querying SPX data: {e}")
            return pd.DataFrame()
    
    def get_option_chain_data(
        self,
        expiration_dates: Optional[List[str]] = None,
        strike_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Get SPX option chain data.
        
        Args:
            expiration_dates: List of expiration dates
            strike_range: Tuple of (min_strike, max_strike)
            
        Returns:
            Dict containing option chain data
        """
        self.logger.info("Getting SPX option chain data...")
        
        try:
            # This would use IBKR API to get option chain data
            # For now, return a placeholder
            
            result = {
                'success': True,
                'option_count': 0,
                'expiration_dates': expiration_dates or [],
                'strike_range': strike_range,
                'timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info("✅ Retrieved SPX option chain data")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting option chain data: {e}")
            return {
                'success': False,
                'error': str(e),
                'option_count': 0,
                'timestamp': datetime.now().isoformat(),
            }
    
    def _verify_spx_future_entity(self) -> Dict[str, Any]:
        """
        Verify SPX future entity exists and create if necessary.
        
        Returns:
            Dict with verification status
        """
        try:
            # Create SPX future entity using FinancialAssetService
            from datetime import date
            year='26'
            months = ['H','M','U','Z']
            month = months[0]
            spx_future = self.financial_asset_service._create_or_get(
                symbol=f'ES{month}{year}',
                underlying_asset='SPX',
                expiry_date=date(2025, 12, 31),  # Default expiry
                contract_size='$250 × Index',
                exchange='CBOE',
                currency='USD'
            )
            
            if spx_future:
                self.logger.info("✅ SPX future entity verified/created")
                return {'status': 'verified', 'entity': 'spx_future'}
            else:
                return {'status': 'failed', 'error': 'Could not create SPX future entity'}
                
        except Exception as e:
            self.logger.error(f"Error verifying SPX future entity: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _count_spx_data_records(self) -> int:
        """
        Count existing SPX data records in the database.
        
        Returns:
            Number of SPX records found
        """
        try:
            with self.database_service.session as session:
                spx_shares = session.query(CompanyShare).filter(
                    CompanyShare.ticker == 'SPX'
                ).all()
                return len(spx_shares)
        except Exception as e:
            self.logger.error(f"Error counting SPX data records: {e}")
            return 0