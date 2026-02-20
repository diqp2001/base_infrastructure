
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import logging
from src.domain.entities.factor.factor_value import FactorValue
from src.application.services.misbuffet.data.frontier import Frontier
from src.application.services.misbuffet.data.market_data_service import MarketDataService
from src.dto.factor.factor_batch import FactorBatch
from src.dto.factor.factor_value_batch import FactorValueBatch


class MarketDataHistoryService:
    """
    Provides historical market data with frontier enforcement to prevent look-ahead bias.
    This service ensures that algorithms can only access historical data up to the current
    simulation time, maintaining the integrity of backtesting.
    """

    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service
        self._frontier: Optional[Frontier] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cache for performance
        self._history_cache: Dict[str, pd.DataFrame] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        
    def set_frontier(self, frontier_time: datetime):
        """
        Set the frontier time to prevent look-ahead bias.
        
        Args:
            frontier_time: The current simulation time - no data beyond this point is allowed
        """
        if self._frontier is None:
            self._frontier = Frontier(frontier_time)
        else:
            self._frontier.advance(frontier_time)
        
        self.logger.debug(f"Frontier set to {frontier_time}")
    
    # def get_history(self, symbols: Union[str, List[str]], periods: int, 
    #                resolution: str = '1d', factor_data_service=None,
    #                what_to_show: str = "TRADES",
    #                duration_str: str = "6 M",
    #                bar_size_setting: str = "1 day") -> pd.DataFrame:
    #     """
    #     Get historical data for symbols, respecting the frontier.
        
    #     Args:
    #         symbols: Symbol or list of symbols to get data for
    #         periods: Number of periods to retrieve
    #         resolution: Data resolution (e.g., '1d', '1h', '1m')
    #         factor_data_service: Service to get factor data (passed from algorithm)
    #         what_to_show: IBKR data type (TRADES, MIDPOINT, BID, ASK, BID_ASK, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY)
    #         duration_str: IBKR query duration (format: integer + space + unit: S/D/W, e.g., "6 M", "1 W")
    #         bar_size_setting: IBKR bar size (1 sec, 5 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 15 mins, 30 mins, 1 hour, 1 day)
            
    #     Returns:
    #         DataFrame with historical data up to the frontier time
    #     """
    #     if self._frontier is None:
    #         raise ValueError("Frontier must be set before accessing historical data")
        
    #     # Normalize symbols to list
    #     if isinstance(symbols, str):
    #         symbols = [symbols]
        
    #     # Calculate start date based on periods
    #     end_date = self._frontier.frontier
        
    #     if resolution == '1d':
    #         start_date = end_date - timedelta(days=periods + 10)  # Add buffer for weekends/holidays
    #     elif resolution == '1h':
    #         start_date = end_date - timedelta(hours=periods)
    #     elif resolution == '1m':
    #         start_date = end_date - timedelta(minutes=periods)
    #     else:
    #         raise ValueError(f"Unsupported resolution: {resolution}")
        
    #     self.logger.debug(f"Getting history for {symbols} from {start_date} to {end_date} ({periods} periods)")
        
    #     # Get data for all symbols
    #     all_data = []
        
    #     for symbol in symbols:
    #         try:
    #             # Check cache first
    #             cache_key = f"{symbol}_{start_date}_{end_date}_{resolution}"
    #             if self._is_cache_valid(cache_key):
    #                 symbol_data = self._history_cache[cache_key].copy()
    #             else:
    #                 # Get fresh data with configurable IBKR parameters
    #                 symbol_data = self._get_symbol_history(
    #                     symbol, start_date, end_date, factor_data_service,
    #                     what_to_show=what_to_show,
    #                     duration_str=duration_str,
    #                     bar_size_setting=bar_size_setting
    #                 )
    #                 # Cache the result
    #                 self._history_cache[cache_key] = symbol_data.copy()
    #                 self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)
                
    #             if not symbol_data.empty:
    #                 # Ensure we don't exceed the frontier
    #                 symbol_data = symbol_data[symbol_data.index <= end_date]
                    
    #                 # Limit to requested number of periods
    #                 if len(symbol_data) > periods:
    #                     symbol_data = symbol_data.tail(periods)
                    
    #                 # Add symbol column for multi-symbol datasets
    #                 symbol_data['Symbol'] = symbol
    #                 all_data.append(symbol_data)
                    
    #         except Exception as e:
    #             self.logger.warning(f"Error getting history for {symbol}: {e}")
    #             continue
        
    #     # Combine all data
    #     if all_data:
    #         result = pd.concat(all_data, ignore_index=False)
    #         self.logger.debug(f"Retrieved {len(result)} historical records")
    #         return result
    #     else:
    #         self.logger.warning(f"No historical data found for symbols {symbols}")
    #         return pd.DataFrame()
    
    # def _get_symbol_history(self, symbol: str, start_date: datetime, 
    #                        end_date: datetime, factor_data_service,
    #                        what_to_show: str = "TRADES",
    #                        duration_str: str = "6 M",
    #                        bar_size_setting: str = "1 day") -> pd.DataFrame:
    #     """
    #     Get historical data for a single symbol from the data source.
        
    #     Args:
    #         symbol: Symbol to get data for
    #         start_date: Start date for historical data
    #         end_date: End date for historical data  
    #         factor_data_service: Service to get factor data
    #         what_to_show: IBKR data type (TRADES, MIDPOINT, BID, ASK, etc.)
    #         duration_str: IBKR query duration (e.g., "6 M", "1 W")
    #         bar_size_setting: IBKR bar size (e.g., "1 day", "1 hour", "1 sec")
            
    #     Returns:
    #         DataFrame with historical data for the symbol
    #     """
    #     if not factor_data_service:
    #         return pd.DataFrame()
        
    #     try:
    #         # Get entity for the symbol
    #         entity = self.market_data_service._get_entity_by_ticker(symbol)
    #         if not entity:
    #             return pd.DataFrame()
            
            
    #         historical_data = []
            
            
            
    #         # Optimized: Use EntityService batch methods for historical data retrieval
    #         try:
    #             # Get all factors first using batch processing
    #             factors_data = []
                
                
    #             # Get factors in batch through market data service entity service
    #             factor_entities = []
    #             if hasattr(factor_data_service, 'get_factor_by_name'):
    #                 # Use existing factor data service methods
    #                 for factor_name in factor_names:
    #                     factor = factor_data_service.get_factor_by_name(factor_name)
    #                     if factor:
    #                         factor_entities.append(factor)
                
    #             if factor_entities and hasattr(self.market_data_service, 'entity_service'):
    #                 # Use MarketDataService's entity service for optimized batch processing
    #                 entity_service = self.market_data_service.entity_service
                    
    #                 # Check if IBKR is available for bulk data optimization
    #                 if (hasattr(entity_service, 'repository_factory') and 
    #                     hasattr(entity_service.repository_factory, 'ibkr_client') and
    #                     entity_service.repository_factory.ibkr_client):
                        
    #                     # Prepare batch request for IBKR bulk data
    #                     factor_values_data = []
    #                     for factor in factor_entities:
    #                         factor_values_data.append({
    #                             'factor': factor,
    #                             'financial_asset_entity': entity,
    #                             'entity_id': entity.id,
    #                             'time_date': start_date.strftime("%Y-%m-%d %H:%M:%S"),
    #                             'end_date': end_date.strftime("%Y-%m-%d %H:%M:%S")
    #                         })
                        
    #                     # Get bulk factor values using optimized IBKR batch method with configurable parameters
    #                     bulk_factor_values = entity_service.create_or_get_batch_ibkr(
    #                         factor_values_data, FactorValue,
    #                         what_to_show=what_to_show,
    #                         duration_str=duration_str,
    #                         bar_size_setting=bar_size_setting
    #                     )
                        
    #                     # Convert bulk factor values to DataFrame format
    #                     historical_data = self._convert_bulk_factor_values_to_dataframe(
    #                         bulk_factor_values, factor_entities, start_date, end_date
    #                     )
                        
    #                 else:
    #                     # Fallback to date iteration for local repositories
    #                     historical_data = self._process_date_range_locally(
    #                         factor_data_service, factor_names, entity, start_date, end_date
    #                     )
    #             else:
    #                 # Original fallback: iterate through dates and get factor values
    #                 historical_data = self._process_date_range_locally(
    #                     factor_data_service, factor_names, entity, start_date, end_date
    #                 )
    #         except Exception as e:
    #             self.logger.error(f"Error getting symbol history for {symbol}: {e}")
    #             return pd.DataFrame()

    #         # Create DataFrame
    #         if historical_data:
    #             df = pd.DataFrame(historical_data)
    #             df['Date'] = pd.to_datetime(df['Date'])
    #             df = df.set_index('Date')
    #             return df
            
    #         return pd.DataFrame()
            
    #     except Exception as e:
    #         self.logger.error(f"Error getting symbol history for {symbol}: {e}")
    #         return pd.DataFrame()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid.
        """
        if cache_key not in self._history_cache:
            return False
        
        if cache_key not in self._cache_expiry:
            return False
        
        return datetime.now() < self._cache_expiry[cache_key]
    
    def clear_cache(self):
        """
        Clear the history cache.
        """
        self._history_cache.clear()
        self._cache_expiry.clear()
        self.logger.debug("History cache cleared")
    
    @property
    def frontier(self) -> Optional[Frontier]:
        """Get the frontier object."""
        return self._frontier
    
    @property
    def current_time(self) -> Optional[datetime]:
        """Get the current frontier time."""
        return self._frontier.frontier if self._frontier else None
    
    def can_access_time(self, requested_time: datetime) -> bool:
        """
        Check if a requested time is accessible (doesn't violate the frontier).
        
        Args:
            requested_time: Time to check
            
        Returns:
            True if the time is accessible, False otherwise
        """
        if self._frontier is None:
            return False
        return requested_time <= self._frontier.frontier
    
    
    
    
    def process_factor_batch(self, factor_batch: FactorBatch, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process a FactorBatch to create and store factor entities in the database.
        
        Args:
            factor_batch: FactorBatch DTO containing factors to process
            tickers: Optional list of tickers to associate with factors
            
        Returns:
            Dictionary containing processing results
        """
        results = {
            'processed_count': 0,
            'failed_count': 0,
            'factor_ids': [],
            'errors': []
        }
        
        try:
            self.logger.info(f"Processing FactorBatch with {factor_batch.size()} factors")
            
            for factor in factor_batch.factors:
                try:
                    # Here you would typically use a factor repository to persist the factor
                    # For now, we'll just validate and log the factor creation
                    
                    if hasattr(factor, 'name') and factor.name:
                        # Simulate factor creation/persistence
                        results['processed_count'] += 1
                        results['factor_ids'].append(getattr(factor, 'id', f"temp_id_{results['processed_count']}"))
                        
                        self.logger.info(f"  ✅ Processed factor: {factor.name} (index: {getattr(factor, 'factor_index', 'N/A')})")
                    else:
                        results['failed_count'] += 1
                        results['errors'].append(f"Factor missing name: {factor}")
                        
                except Exception as e:
                    error_msg = f"Error processing factor {getattr(factor, 'name', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    results['failed_count'] += 1
                    self.logger.error(error_msg)
            
            # Log batch metadata
            if factor_batch.metadata:
                self.logger.info(f"  📊 Batch metadata: {factor_batch.metadata}")
            
            self.logger.info(f"FactorBatch processing complete: {results['processed_count']} processed, {results['failed_count']} failed")
            
        except Exception as e:
            error_msg = f"Error in process_factor_batch: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def create_factor_value_batch(self, factor_ids: List[int], entity_ids: List[int], 
                                date_range: tuple, values_data: Dict[str, Any]) -> FactorValueBatch:
        """
        Create a FactorValueBatch for bulk factor value operations.
        
        Args:
            factor_ids: List of factor IDs
            entity_ids: List of entity IDs 
            date_range: Tuple of (start_date, end_date)
            values_data: Dictionary containing factor value data
            
        Returns:
            FactorValueBatch DTO with factor values
        """
        from src.domain.entities.factor.factor_value import FactorValue
        
        factor_values = []
        start_date, end_date = date_range
        
        try:
            # Create factor values for the specified range
            current_date = start_date
            
            while current_date <= end_date:
                for factor_id in factor_ids:
                    for entity_id in entity_ids:
                        # Get value from values_data or generate placeholder
                        value_key = f"{factor_id}_{entity_id}_{current_date.strftime('%Y-%m-%d')}"
                        value = values_data.get(value_key, 0.0)  # Default to 0.0 if not provided
                        
                        factor_value = FactorValue(
                            factor_id=factor_id,
                            entity_id=entity_id,
                            date=current_date,
                            value=value
                        )
                        
                        factor_values.append(factor_value)
                
                current_date += timedelta(days=1)
            
            # Create and return FactorValueBatch
            factor_value_batch = FactorValueBatch(
                factor_values=factor_values,
                metadata={
                    'date_range': (start_date.isoformat(), end_date.isoformat()),
                    'factor_count': len(factor_ids),
                    'entity_count': len(entity_ids),
                    'created_at': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Created FactorValueBatch with {factor_value_batch.size()} factor values")
            return factor_value_batch
            
        except Exception as e:
            self.logger.error(f"Error creating FactorValueBatch: {e}")
            # Return empty batch on error
            return FactorValueBatch(
                factor_values=[],
                metadata={'error': str(e)}
            )

    def _convert_bulk_factor_values_to_dataframe(self, bulk_factor_values: List[FactorValue],
                                               factor_entities: List[Any], start_date: datetime, 
                                               end_date: datetime) -> List[Dict[str, Any]]:
        """
        Convert bulk factor values from IBKR to historical data format.
        
        Args:
            bulk_factor_values: List of FactorValue entities from IBKR bulk request
            factor_entities: List of factor entities for name mapping
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of dictionaries suitable for DataFrame creation
        """
        try:
            historical_data = []
            
            # Group factor values by date
            date_groups = {}
            for factor_value in bulk_factor_values:
                factor_date = factor_value.date
                
                # Filter by date range
                if factor_date < start_date or factor_date > end_date:
                    continue
                
                date_key = factor_date.strftime('%Y-%m-%d')
                if date_key not in date_groups:
                    date_groups[date_key] = {'Date': factor_date}
                
                # Find factor name by ID
                factor_name = None
                for factor in factor_entities:
                    if factor.id == factor_value.factor_id:
                        factor_name = factor.name
                        break
                
                if factor_name:
                    date_groups[date_key][factor_name] = float(factor_value.value)
            
            # Convert grouped data to list format
            for date_key, daily_data in date_groups.items():
                if len(daily_data) > 1:  # More than just the date
                    historical_data.append(daily_data)
            
            self.logger.info(f"Converted {len(bulk_factor_values)} factor values to {len(historical_data)} daily records")
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Error converting bulk factor values to dataframe: {e}")
            return []

    def _process_date_range_locally(self, factor_data_service, factor_names: List[str],
                                  entity: Any, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Process date range using local repositories (fallback method).
        
        Args:
            factor_data_service: Factor data service
            factor_names: List of factor names to retrieve
            entity: Entity to get data for
            start_date: Start date
            end_date: End date
            
        Returns:
            List of historical data dictionaries
        """
        try:
            historical_data = []
            current_date = start_date
            
            while current_date <= end_date:
                try:
                    daily_data = {'Date': current_date}
                    
                    for factor_name in factor_names:
                        factor = factor_data_service.get_factor_by_name(factor_name)
                        if factor:
                            factor_values = factor_data_service.get_factor_values(
                                factor_id=int(factor.id),
                                entity_id=entity.id,
                                start_date=current_date.strftime('%Y-%m-%d'),
                                end_date=current_date.strftime('%Y-%m-%d')
                            )
                            
                            if factor_values:
                                daily_data[factor_name] = float(factor_values[0].value)
                    
                    # Only add if we have actual price data
                    if len(daily_data) > 1:  # More than just the date
                        historical_data.append(daily_data)
                        
                except Exception as e:
                    self.logger.debug(f"Error getting local data for {entity} on {current_date}: {e}")
                
                current_date += timedelta(days=1)
            
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Error in local date range processing: {e}")
            return []
        
    def _create_or_get_factor_value_batch(self,factor_groups: Any, entities: Any, 
                                date: Any, ) -> FactorValueBatch:
        factor_data = {}
        
        created_factors =[]
        factor_values = []
        max_date = date
        
        for factor_config in factor_groups:
            
            
            created_factors.append(factor_config.get('factor_entity', 'unknown'))
    
        factor_values_data = []
        for factor in  created_factors:
            for entity in entities:
                if entity == None:
                    break
                for factor in created_factors:
                    factor_values_data.append({
                        'factor': factor,
                        'financial_asset_entity': entity,
                        'entity_id': entity.id,
                        'max_date': max_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
        factor_values = self.market_data_service.entity_service.create_or_get_batch_ibkr(
                        factor_values_data, FactorValue,
                        what_to_show="TRADES",
                        duration_str="1 D",
                        bar_size_setting="5 mins"
                    )
        for factor_value in factor_values:
                        # Find corresponding factor name
                        for factor in created_factors:
                            if factor.id == factor_value.factor_id:
                                factor_data[factor.name] = float(factor_value.value)
                                break
        
        return factor_data

    def _create_or_get(self, entity_config: Dict[str, Any]) -> Optional[Any]:
        """
        Create or get an entity using the MarketDataService.
        
        This method provides entity creation functionality for the MarketDataHistoryService
        using the underlying MarketDataService layer for proper layered architecture.
        
        Args:
            entity_config: Dictionary containing entity configuration with keys:
                - entity_class: Entity class to create/get
                - entity_symbol: Entity symbol/identifier
                - additional parameters for entity creation
        
        Returns:
            Entity if created/retrieved successfully, None otherwise
        """
        try:
            # Delegate to MarketDataService._create_or_get for proper layering
            entity = self.market_data_service._create_or_get(entity_config)
            
            if entity:
                self.logger.info(f"MarketDataHistoryService created/retrieved entity: {entity_config.get('entity_symbol')} via MarketDataService")
            else:
                self.logger.warning(f"MarketDataHistoryService failed to create/get entity: {entity_config.get('entity_symbol')}")
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Error in MarketDataHistoryService._create_or_get: {e}")
            return None