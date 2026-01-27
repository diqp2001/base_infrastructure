from datetime import datetime
from typing import Callable, List, Optional, Union
import pandas as pd
import logging
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
        
    def create_data_slice(self, current_date: datetime, universe: List[str]) -> Slice:
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
                            entity,entity_class, current_date
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
            
        return slice_data
    
    def _get_point_in_time_data(self, ticker: str, entity_class: object, point_in_time: datetime) -> Optional[pd.DataFrame]:
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
            
            # Get price factor data for this date
            factor_names = ['Open', 'High', 'Low', 'Close', 'Volume']
            factor_data = {}
            
            for factor_name in factor_names:
                # Use entity service to get or create factor
                entity_factor_class_input = ENTITY_FACTOR_MAPPING[entity.__class__][0]
                factor = self.entity_service._create_or_get(
                    entity_cls = entity_factor_class_input, 
                    name = factor_name
                )
                if factor:
                    # Create composite key for factor value lookup
                    date_str = point_in_time.strftime('%Y-%m-%d')
                    composite_key = f"{factor.id}_{entity.id}_{date_str}"
                    
                    # Use entity service to get factor value
                    factor_value = self.entity_service._create_or_get(
                        FactorValue,
                        composite_key,
                        factor_id=factor.id,
                        entity_id=entity.id,
                        date=point_in_time.date(),
                        value="0.0"  # Default value if not found
                    )
                    
                    if factor_value:
                        factor_data[factor_name] = float(factor_value.value)
            
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
                    entity_class, 
                    ticker
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
