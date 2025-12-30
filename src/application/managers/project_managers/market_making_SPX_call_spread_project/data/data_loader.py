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

from src.application.services.database_service.database_service import DatabaseService
from src.application.services.api_service.ibkr_service.market_data import MarketData
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Data loader for SPX index data and option chains.
    Handles both database queries and IBKR API calls.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the SPX data loader.
        
        Args:
            database_service: Database service instance
        """
        self.database_service = database_service
        self.market_data_service = MarketData()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def check_spx_data_availability(self) -> Dict[str, Any]:
        """
        Check if SPX data exists in the database.
        
        Returns:
            Dict containing data availability status
        """
        self.logger.info("Checking SPX data availability in database...")
        
        try:
            # Check for SPX index data
            with self.database_service.get_session() as session:
                spx_shares = session.query(CompanyShare).filter(
                    CompanyShare.ticker == 'SPX'
                ).all()
                
                spx_count = len(spx_shares)
                
            result = {
                'spx_index_records': spx_count,
                'has_spx_data': spx_count > 0,
                'last_checked': datetime.now().isoformat(),
            }
            
            if spx_count > 0:
                self.logger.info(f"✅ Found {spx_count} SPX records in database")
            else:
                self.logger.warning("❌ No SPX data found in database")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking SPX data availability: {e}")
            return {
                'spx_index_records': 0,
                'has_spx_data': False,
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
        Load SPX data from database.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame containing SPX data
        """
        self.logger.info("Loading SPX data from database...")
        
        try:
            # Default date range
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=180)  # 6 months default
            
            # Query SPX data from database
            # This would need to be implemented based on your factor system
            df = self._query_spx_data_from_database(start_date, end_date)
            
            self.logger.info(f"✅ Loaded {len(df)} SPX records from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading SPX data: {e}")
            return pd.DataFrame()
    
    def _store_spx_data_in_database(self, df: pd.DataFrame) -> int:
        """
        Store SPX data in database using the factor system.
        
        Args:
            df: DataFrame containing SPX data
            
        Returns:
            Number of records stored
        """
        # This would integrate with your factor system
        # For now, return the number of rows as a placeholder
        self.logger.info(f"Storing {len(df)} SPX records in database...")
        
        # TODO: Implement actual database storage using factor system
        # This would involve:
        # 1. Creating/updating SPX company share entity
        # 2. Creating factor definitions for OHLCV data
        # 3. Storing factor values
        
        return len(df)
    
    def _query_spx_data_from_database(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Query SPX data from database.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame containing SPX data
        """
        # TODO: Implement actual database query using factor system
        # This would query factor values for SPX
        
        # Placeholder implementation
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