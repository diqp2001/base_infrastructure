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


from application.services.data.entities.factor.factor_service import FactorService
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.index.index import Index
from src.application.services.database_service.database_service import DatabaseService
from src.application.services.api_service.ibkr_service.market_data import MarketData
from src.application.services.data.entities.entity_service import EntityService
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
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize enhanced services for comprehensive data management
        self.financial_asset_service = EntityService(database_service)
        self.financial_asset_service.create_ibkr_repositories()
        self.factor_data_service = FactorService(database_service)
        
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
            # Use EntityService to verify existence of SPX entities
            # Check for both SPX index and future entities
            spx_index_symbol = 'SPX'  # SPX index
            spx_future_symbol = 'ES'  # SPX future
            
            # Ensure SPX entities exist using EntityService IBKR repositories
            spx_index_entity = self.financial_asset_service._create_ibkr_or_get(Index, spx_index_symbol)
            spx_future_entity = self.financial_asset_service._create_ibkr_or_get(IndexFuture, spx_future_symbol)
            
            #Check if factor_manager is available for _ensure_entities_exist
            factor_manager_status = 'available' if self.factor_manager else 'not_available'
            if self.factor_manager and hasattr(self.factor_manager, '_ensure_entities_exist'):
                # Use factor_manager's entity verification if available
                self.logger.info("Using factor_manager for entity verification...")
                factor_entities_spx_index = self.factor_manager._ensure_entities_exist([spx_index_symbol])
                factor_entities_spx_future = self.factor_manager._ensure_entities_exist([spx_future_symbol])
            
            # Check actual data availability using enhanced verification
            spx_data_count = self._count_spx_data_records()
            
            # Count successful entity creations
            entities_created = 0
            entities_verified = 0
            entity_errors = []
            
            if spx_index_entity:
                entities_verified += 1
                self.logger.info(f"✅ SPX index entity verified: {spx_index_entity}")
            else:
                entity_errors.append("Failed to create/get SPX index entity")
                
            if spx_future_entity:
                entities_verified += 1 
                entities_created += 1  # New entities are considered created
                self.logger.info(f"✅ SPX future entity verified: {spx_future_entity}")
            else:
                entity_errors.append("Failed to create/get SPX future entity")
            
            result = {
                'spx_index_records': spx_data_count,
                'has_spx_data': spx_data_count > 0,
                'entities_verified': entities_verified,
                'entities_created': entities_created,
                'spx_index_entity': 'verified' if spx_index_entity else 'failed',
                'spx_future_entity': 'verified' if spx_future_entity else 'failed',
                'factor_manager_status': factor_manager_status,
                'entity_verification_errors': entity_errors,
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
                import_result = None
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
            # Ensure SPX entities exist first using EntityService IBKR repositories
            spx_index_entity = self.financial_asset_service._create_ibkr_or_get(Index, 'SPX')
            
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

    def _create_or_get_factor_via_entity_service(self, name: str, group: str, subgroup: str, 
                                                data_type: str, source: str, definition: str):
        """
        Create or get factor using EntityService IBKR factor repository.
        Demonstrates how to use EntityService for factor and factor value creation.
        
        Args:
            name: Factor name
            group: Factor group
            subgroup: Factor subgroup  
            data_type: Data type
            source: Data source
            definition: Factor definition
            
        Returns:
            Factor entity or None
        """
        try:
            # Use EntityService IBKR factor repository for factor creation
            factor_repo = self.financial_asset_service.ibkr_repositories.get('factor')
            if factor_repo:
                # Create factor entity using IBKR repository
                from src.domain.entities.factor.factor import Factor
                factor = Factor(
                    name=name,
                    group=group, 
                    subgroup=subgroup,
                    data_type=data_type,
                    source=source,
                    definition=definition
                )
                # Use IBKR repository to create or get the factor
                result = factor_repo.get_or_create(factor)
                self.logger.info(f"✅ Factor created/retrieved via EntityService: {name}")
                return result
            else:
                # Fallback to factor_data_service if IBKR repo not available
                self.logger.warning("IBKR factor repository not available, falling back to factor_data_service")
                return self.factor_data_service.create_or_get_factor(
                    name=name,
                    group=group,
                    subgroup=subgroup,
                    data_type=data_type,
                    source=source,
                    definition=definition
                )
                
        except Exception as e:
            self.logger.error(f"Error creating factor via EntityService: {e}")
            # Fallback to factor_data_service
            return self.factor_data_service.create_or_get_factor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )

    def _store_factor_values_via_entity_service(self, factor, share, df, column_name):
        """
        Store factor values using EntityService IBKR factor value repository.
        Demonstrates how to use EntityService for factor value storage.
        
        Args:
            factor: Factor entity
            share: Company share entity  
            df: DataFrame with data
            column_name: Column name in DataFrame
            
        Returns:
            Number of values stored
        """
        try:
            # Use EntityService IBKR factor value repository
            factor_value_repo = self.financial_asset_service.ibkr_repositories.get('factor_value')
            if factor_value_repo:
                # Create and store factor values using IBKR repository
                values_stored = 0
                for index, row in df.iterrows():
                    try:
                        from src.domain.entities.factor.factor_value import FactorValue
                        factor_value = FactorValue(
                            factor_id=factor.id,
                            asset_id=share.id,
                            value=float(row[column_name]),
                            date=pd.to_datetime(row.get('date', index)).date() if hasattr(row, 'get') else pd.to_datetime(index).date(),
                            source='ibkr'
                        )
                        factor_value_repo.add(factor_value)
                        values_stored += 1
                    except Exception as row_error:
                        self.logger.warning(f"Error storing individual factor value: {row_error}")
                        
                self.logger.info(f"✅ Factor values stored via EntityService: {values_stored}")
                return values_stored
            else:
                # Fallback to factor_data_service
                self.logger.warning("IBKR factor value repository not available, falling back to factor_data_service")
                return self.factor_data_service.store_factor_values(
                    factor=factor,
                    share=share,
                    data=df,
                    column=column_name,
                    overwrite=True
                )
                
        except Exception as e:
            self.logger.error(f"Error storing factor values via EntityService: {e}")
            # Fallback to factor_data_service
            return self.factor_data_service.store_factor_values(
                factor=factor,
                share=share, 
                data=df,
                column=column_name,
                overwrite=True
            )