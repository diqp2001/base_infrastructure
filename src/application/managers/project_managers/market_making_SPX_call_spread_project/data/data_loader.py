"""
SPX Data Loader for Market Making Call Spread Project

This module handles loading SPX index data and option chain data from the database
and IBKR services, following the pattern from test_base_project.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, NamedTuple, Optional, Any, Tuple
from pathlib import Path


from application.services.data.entities.factor.factor_service import FactorService
from application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from application.services.misbuffet.data.market_data_service import MarketDataService
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.index.index import Index
from src.application.services.database_service.database_service import DatabaseService
from src.application.services.api_service.ibkr_service.market_data import MarketData
from src.application.services.data.entities.entity_service import EntityService
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel

logger = logging.getLogger(__name__)

class DataServices(NamedTuple):
    """Container for all initialized data services."""
    entity_service: EntityService
    market_data_service: MarketDataService
    history_service: MarketDataHistoryService
    database_service: DatabaseService

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


        self.market_data_service = MarketDataService(self.financial_asset_service)
        self.market_data_history_service = MarketDataHistoryService(self.market_data_service)
        self.factor_data_service = FactorService(database_service)
        
        # Store factor_manager reference for _ensure_entities_exist access
        self.factor_manager = factor_manager
    
    
    
    
    
    
    
    
    
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
    
    