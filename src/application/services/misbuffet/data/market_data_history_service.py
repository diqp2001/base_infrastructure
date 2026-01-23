
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import logging
from src.application.services.misbuffet.data.frontier import Frontier
from src.application.services.misbuffet.data.market_data_service import MarketDataService


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
    
    def get_history(self, symbols: Union[str, List[str]], periods: int, 
                   resolution: str = '1d', factor_data_service=None) -> pd.DataFrame:
        """
        Get historical data for symbols, respecting the frontier.
        
        Args:
            symbols: Symbol or list of symbols to get data for
            periods: Number of periods to retrieve
            resolution: Data resolution (e.g., '1d', '1h', '1m')
            factor_data_service: Service to get factor data (passed from algorithm)
            
        Returns:
            DataFrame with historical data up to the frontier time
        """
        if self._frontier is None:
            raise ValueError("Frontier must be set before accessing historical data")
        
        # Normalize symbols to list
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # Calculate start date based on periods
        end_date = self._frontier.frontier
        
        if resolution == '1d':
            start_date = end_date - timedelta(days=periods + 10)  # Add buffer for weekends/holidays
        elif resolution == '1h':
            start_date = end_date - timedelta(hours=periods)
        elif resolution == '1m':
            start_date = end_date - timedelta(minutes=periods)
        else:
            raise ValueError(f"Unsupported resolution: {resolution}")
        
        self.logger.debug(f"Getting history for {symbols} from {start_date} to {end_date} ({periods} periods)")
        
        # Get data for all symbols
        all_data = []
        
        for symbol in symbols:
            try:
                # Check cache first
                cache_key = f"{symbol}_{start_date}_{end_date}_{resolution}"
                if self._is_cache_valid(cache_key):
                    symbol_data = self._history_cache[cache_key].copy()
                else:
                    # Get fresh data
                    symbol_data = self._get_symbol_history(
                        symbol, start_date, end_date, factor_data_service
                    )
                    # Cache the result
                    self._history_cache[cache_key] = symbol_data.copy()
                    self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)
                
                if not symbol_data.empty:
                    # Ensure we don't exceed the frontier
                    symbol_data = symbol_data[symbol_data.index <= end_date]
                    
                    # Limit to requested number of periods
                    if len(symbol_data) > periods:
                        symbol_data = symbol_data.tail(periods)
                    
                    # Add symbol column for multi-symbol datasets
                    symbol_data['Symbol'] = symbol
                    all_data.append(symbol_data)
                    
            except Exception as e:
                self.logger.warning(f"Error getting history for {symbol}: {e}")
                continue
        
        # Combine all data
        if all_data:
            result = pd.concat(all_data, ignore_index=False)
            self.logger.debug(f"Retrieved {len(result)} historical records")
            return result
        else:
            self.logger.warning(f"No historical data found for symbols {symbols}")
            return pd.DataFrame()
    
    def _get_symbol_history(self, symbol: str, start_date: datetime, 
                           end_date: datetime, factor_data_service) -> pd.DataFrame:
        """
        Get historical data for a single symbol from the data source.
        """
        if not factor_data_service:
            return pd.DataFrame()
        
        try:
            # Get entity for the symbol
            entity = self.market_data_service._get_entity_by_ticker(symbol)
            if not entity:
                return pd.DataFrame()
            
            # Get historical factor data
            factor_names = ['Open', 'High', 'Low', 'Close', 'Volume']
            historical_data = []
            
            # Query factor data service for the date range
            # Note: This assumes factor_data_service has a method to get data ranges
            try:
                # Try to get ticker factor data if available
                if hasattr(factor_data_service, 'get_ticker_factor_data'):
                    df = factor_data_service.get_ticker_factor_data(
                        ticker=symbol,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d'),
                        factor_groups=['price']
                    )
                    if df is not None and not df.empty:
                        # Ensure the index is datetime for proper filtering
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df = df.set_index('date')
                        return df
            except Exception as e:
                self.logger.debug(f"Error using get_ticker_factor_data: {e}")
            
            # Fallback: iterate through dates and get factor values
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
                    self.logger.debug(f"Error getting data for {symbol} on {current_date}: {e}")
                
                current_date += timedelta(days=1)
            
            # Create DataFrame
            if historical_data:
                df = pd.DataFrame(historical_data)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error getting symbol history for {symbol}: {e}")
            return pd.DataFrame()
    
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