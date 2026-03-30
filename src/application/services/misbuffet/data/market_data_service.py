from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
import pandas as pd
import logging
from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING
from src.application.services.misbuffet.common.data_types import Slice, TradeBar, Symbol
from src.application.services.data.entities.entity_service import EntityService
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_value import FactorValue


class MarketDataService:
    """
    Main market data service that provides data slices to the trading engine.
    Handles slice creation for both real-time and backtest scenarios.
    """

    def __init__(self, entity_service: EntityService):
        self.entity_service = entity_service
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cache for performance
        self._last_time = None
        self._data_cache = {}
        
        # Event callbacks
        self.on_data_slice: Optional[Callable[[Slice], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
    def create_data_slice(self, current_date: datetime, universe: List[str],bar_size_setting,duration_str) -> Slice:
        """
        Create a data slice for the given date and universe.
        This is the main method called by the engine's _create_data_slice.
        
        Args:
            current_date: The date/time for this slice
            universe: List of tickers/symbols to include
            factor_data_service: Service to get factor data (passed from engine)
            
        Returns:
            Slice containing market data for the specified time
        """
        # Validate if current_date is a trading day
        if  self._is_valid_trading_day(current_date):
            
            
        
            # Create the slice for this time point
            slice_data = Slice(time=current_date)
            
            # Get data for each symbol in the universe
            for entity_class, entities in universe.items():
                
                for entity in entities:
                    try:
                        point_in_time_data = self._get_point_in_time_data(
                            entity,entity_class, current_date,bar_size_setting,duration_str
                        )

                        
                        if point_in_time_data is not None and not point_in_time_data.empty:
                            # Create Symbol object
                            symbol = Symbol.create_equity(entity)
                            
                            # Use the most recent data point
                            latest_data = point_in_time_data.iloc[-1]
                            
                            # Create TradeBar with actual market data
                            trade_bar = TradeBar(
                                symbol=symbol,
                                time=current_date,
                                end_time=current_date,
                                open=float(latest_data.get('Open', latest_data.get('open', 0.0))),
                                high=float(latest_data.get('High', latest_data.get('high', 0.0))),
                                low=float(latest_data.get('Low', latest_data.get('low', 0.0))),
                                close=float(latest_data.get('Close', latest_data.get('close', 0.0))),
                                volume=int(latest_data.get('Volume', latest_data.get('volume', 0)))
                            )
                            
                            # Add to slice
                            slice_data.bars[symbol] = trade_bar
                            
                            # Also add to data dictionary for has_data() compatibility
                            if symbol not in slice_data._data:
                                slice_data._data[symbol] = []
                            slice_data._data[symbol].append(trade_bar)
                            
                    except Exception as e:
                        self.logger.debug(f"Error creating data slice for {symbol} on {current_date}: {e}")
                        if self.on_error:
                            self.on_error(f"Error getting data for {symbol}: {str(e)}")
                        continue
        
            self.logger.debug(f"Created data slice for {current_date} with {len(slice_data.bars)} symbols")
        else:
            self.logger.debug(f"Skipping non-trading day: {current_date}")
        # Trigger callback if set
        if self.on_data_slice:
            self.on_data_slice(slice_data)
        slice_data.bar_size_setting = bar_size_setting
        slice_data.duration_str = duration_str
        return slice_data
    
    def _get_point_in_time_data(self, ticker: str, entity_class: object, point_in_time: datetime, bar_size_setting,duration_str) -> Optional[pd.DataFrame]:
        """
        Get point-in-time data for a specific ticker and date.
        Uses the factor data service to retrieve historical data.
        """
        
        try:
            # Get entity using entity service
            entity = self._get_entity_by_ticker(ticker,entity_class)
            if not entity:
                self.logger.debug(f"No entity found for ticker {ticker}")
                return None
            
            # Get price factor data for this date using optimized batch processing
            factor_names = ['high', 'open', 'low', 'close', 'volume']
            factor_data = {}
            
            if self.entity_service.repository_factory.ibkr_client.ib_connection.connected_flag:
                # Create factors first
                entity_factor_class_input = ENTITY_FACTOR_MAPPING[entity.__class__][0]
                factors = []
                
                # Get or create all factors in batch
                factors_data = []
                for factor_name in factor_names:
                    factors_data.append({
                        'entity_symbol': factor_name,
                        'group': 'price',
                        'entity_cls': entity_factor_class_input
                    })
                
                # Use batch method to get/create factors with seconds bar_size for point-in-time data
                created_factors = self.entity_service.create_or_get_batch_ibkr(
                    factors_data, entity_factor_class_input,
                    what_to_show="TRADES",
                    duration_str="1 D", 
                    bar_size_setting=bar_size_setting
                )
                
                if created_factors:
                    # Prepare batch data for factor values with metadata for bulk IBKR processing
                    factor_values_data = []
                    for factor in created_factors:
                        factor_values_data.append({
                            'factor': factor,
                            'financial_asset_entity': entity,
                            'entity_id': entity.id,
                            'time_date': point_in_time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    # Use optimized batch method to get factor values from IBKR bulk data with seconds bar_size
                    factor_values = self.entity_service.create_or_get_batch_ibkr(
                        factor_values_data, FactorValue,
                        what_to_show="TRADES",
                        duration_str=duration_str,#"1 D", 
                        bar_size_setting=bar_size_setting#"1 day"
                    )
                    
                    # Build factor_data dictionary
                    for factor_value in factor_values:
                        # Find corresponding factor name
                        for factor in created_factors:
                            if factor.id == factor_value.factor_id:
                                factor_data[factor.name] = float(factor_value.value)
                                break
                else:
                    # Local batch processing for non-IBKR
                    entity_factor_class_input = ENTITY_FACTOR_MAPPING[entity.__class__][0]
                    
                    # Get or create all factors in batch
                    factors_data = []
                    for factor_name in factor_names:
                        factors_data.append({
                            'entity_symbol': factor_name,
                            'group': 'price'
                        })
                    
                    # Use batch method to get/create factors locally
                    created_factors = self.entity_service.create_or_get_batch_local(factors_data, entity_factor_class_input)
                    
                    if created_factors:
                        # Prepare batch data for factor values
                        factor_values_data = []
                        for factor in created_factors:
                            date_str = point_in_time.strftime('%Y-%m-%d')
                            composite_key = f"{factor.id}_{entity.id}_{date_str}"
                            factor_values_data.append({
                                'entity_symbol': composite_key,
                                'factor': factor,
                                'entity': entity,
                                'date': point_in_time.date()
                            })
                        
                        # Use local batch method for factor values
                        factor_values = self.entity_service.create_or_get_batch_local(factor_values_data, FactorValue)
                        
                        # Build factor_data dictionary
                        for factor_value in factor_values:
                            # Find corresponding factor name
                            for factor in created_factors:
                                if factor.id == factor_value.factor_id:
                                    factor_data[factor.name] = float(factor_value.value)
                                    break
            # Create DataFrame if we have data
            if factor_data:
                factor_data['Date'] = point_in_time
                df = pd.DataFrame([factor_data])
                return df
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting point-in-time data for {ticker} on {point_in_time}: {e}")
            return None
    
    def _get_entity_by_ticker(self, ticker: str, entity_class= None):
        """
        Get entity by ticker using the entity service.
        """
        try:
            
            
            # Check if IBKR client is available in entity service
            if hasattr(self.entity_service, 'repository_factory') and \
               hasattr(self.entity_service.repository_factory, 'ibkr_client') and \
               self.entity_service.repository_factory.ibkr_client:
                # Use IBKR method if client is available
                entity = self.entity_service._create_or_get_ibkr(
                    entity_cls = entity_class, 
                    entity_symbol = ticker
                )
            else:
                # Use local method
                entity = self.entity_service._create_or_get(
                    entity_class, 
                    ticker
                )
            return entity
        except Exception as e:
            self.logger.debug(f"Error getting entity for ticker {ticker}: {e}")
            return None
    
    def _is_valid_trading_day(self, date: datetime) -> bool:
        """
        Check if a given date is a valid trading day.
        Basic implementation - can be enhanced with market calendar.
        """
        # Skip weekends
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Basic US holidays check (can be expanded)
        month, day = date.month, date.day
        
        # New Year's Day
        if month == 1 and day == 1:
            return False
        
        # Independence Day
        if month == 7 and day == 4:
            return False
            
        # Christmas
        if month == 12 and day == 25:
            return False
            
        return True
    
    def set_time(self, current_time: datetime):
        """
        Set the current time for the data service.
        Used for time progression validation.
        """
        if self._last_time and current_time < self._last_time:
            raise ValueError(f"Cannot go backwards in time: {current_time} < {self._last_time}")
        self._last_time = current_time
    
    def get_current_time(self) -> Optional[datetime]:
        """
        Get the current time.
        """
        return self._last_time
    
    def _create_or_get(self, entity_config: Dict[str, Any]) -> Optional[Any]:
        """
        Create or get an entity using the entity_service.
        
        This method provides entity creation functionality for the MarketDataService
        using the underlying entity_service layer for proper layered architecture.
        
        Args:
            entity_config: Dictionary containing entity configuration with keys:
                - entity_class: Entity class to create/get
                - entity_symbol: Entity symbol/identifier
                - additional parameters for entity creation (strike_price, expiry, option_type for options)
        
        Returns:
            Entity if created/retrieved successfully, None otherwise
        """
        try:
            entity_class = entity_config.get('entity_class')
            entity_symbol = entity_config.get('entity_symbol')
            
            if not entity_class or not entity_symbol:
                self.logger.warning("entity_class and entity_symbol are required")
                return None
            
            # Special handling for IndexFutureOption - requires option parameters
            if entity_class.__name__ == 'IndexFutureOption':
                strike_price = entity_config.get('strike_price')
                expiry = entity_config.get('expiry')
                option_type = entity_config.get('option_type')
                
                if not strike_price or not expiry or not option_type:
                    self.logger.warning(f"IndexFutureOption requires strike_price, expiry, and option_type. Got: {entity_config}")
                    return None
                
                # Use IBKR repository if available for options
                if hasattr(self.entity_service, 'repository_factory'):
                    try:
                        # Get the IBKR repository for IndexFutureOption
                        ibkr_repo = getattr(self.entity_service.repository_factory, 'index_future_option_ibkr_repo', None)
                        if ibkr_repo:
                            entity = ibkr_repo._create_or_get(
                                symbol=entity_symbol,
                                strike_price=float(strike_price),
                                expiry=expiry,
                                option_type=option_type
                            )
                            if entity:
                                self.logger.info(f"Created/retrieved IndexFutureOption via IBKR: {entity_symbol} strike={strike_price} expiry={expiry} type={option_type}")
                                return entity
                        
                        # Fallback to local repository
                        local_repo = getattr(self.entity_service.repository_factory, 'index_future_option_local_repo', None)
                        if local_repo:
                            entity = local_repo._create_or_get(
                                symbol=entity_symbol,
                                strike_price=float(strike_price),
                                expiry=expiry,
                                option_type=option_type
                            )
                            if entity:
                                self.logger.info(f"Created/retrieved IndexFutureOption via local: {entity_symbol} strike={strike_price} expiry={expiry} type={option_type}")
                                return entity
                    
                    except Exception as e:
                        self.logger.warning(f"Error creating IndexFutureOption with specific parameters: {e}")
                        
                # Final fallback - log the issue but don't create incomplete entity
                self.logger.warning(f"Failed to create IndexFutureOption {entity_symbol} with required parameters")
                return None
            
            # Standard entity creation for non-option entities
            # Remove entity_class from kwargs to avoid passing it twice
            kwargs = {k: v for k, v in entity_config.items() if k not in ['entity_class', 'entity_symbol']}
            
            # Use entity_service _create_or_get method
            entity = self.entity_service._create_or_get(
                entity_cls = entity_class, 
                #name = entity_symbol,
                **kwargs
            )
            
            if entity:
                self.logger.info(f"Created/retrieved entity: {entity_symbol} (class: {entity_class.__name__})")
            else:
                self.logger.warning(f"Failed to create/get entity: {entity_symbol}")
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Error in MarketDataService._create_or_get: {e}")
            return None
    
    def create_entity_from_ticker_item(self, ticker_item: Union[str, Dict[str, Any]], entity_class: type) -> Optional[Any]:
        """
        Create or get an entity from ticker item, handling both dictionary and string formats.
        
        This method consolidates the logic for handling entity creation from configuration
        that was previously in model_trainer.py.
        
        Args:
            ticker_item: Either a string ticker (legacy format) or dictionary with entity parameters
            entity_class: The entity class to create/get
            
        Returns:
            Entity if created/retrieved successfully, None otherwise
        """
        try:
            if isinstance(ticker_item, dict):
                # New format: {"symbol": "EW", "strike_price": 2250.0, "expiry": "20260320", "option_type": "C"}
                # For IndexFutureOption, we need to create entity with specific parameters
                if entity_class.__name__ == 'IndexFutureOption':
                    # Use the entity creation service with option parameters
                    entity_config = {
                        'entity_class': entity_class,
                        'entity_symbol': ticker_item['symbol'],
                        'strike_price': ticker_item.get('strike_price'),
                        'expiry': ticker_item.get('expiry'),  
                        'option_type': ticker_item.get('option_type'),
                        'source': 'config'
                    }
                    entity = self._create_or_get(entity_config)
                else:
                    # For other entity types with dict format, use symbol field
                    ticker = ticker_item.get('symbol', ticker_item.get('name', str(ticker_item)))
                    entity = self._get_entity_by_ticker(ticker, entity_class)
            else:
                # Legacy string format: "EW" or "SPX"
                ticker = ticker_item
                entity = self._get_entity_by_ticker(ticker, entity_class)
            
            if not entity:
                self.logger.warning(f"Failed to create/get entity for {ticker_item} (class: {entity_class.__name__})")
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Error in create_entity_from_ticker_item: {e}")
            return None
