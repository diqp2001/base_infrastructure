"""
QuantConnect-style History Provider for Misbuffet Service

Provides comprehensive historical data access with QuantConnect-compatible interfaces
while leveraging existing misbuffet data services and repositories.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Iterator
import pandas as pd

from ..common.symbol import Symbol
from ..common.enums import Resolution, SecurityType
from ..common.data_types import BaseData, TradeBar, QuoteBar, Slice
from .history_provider import IHistoryProvider

# Import existing services
from src.application.services.data.entities.entity_service import EntityService
from src.application.services.data.entities.factor.factor_service import FactorService
from src.domain.entities.finance.financial_assets.company_share import CompanyShare


class QuantConnectHistoryProvider(IHistoryProvider):
    """
    QuantConnect-compatible history provider that integrates with existing 
    misbuffet data services and provides comprehensive historical data access.
    """
    
    def __init__(self, entity_service: Optional[EntityService] = None,
                 factor_service: Optional[FactorService] = None):
        """
        Initialize the history provider.
        
        Args:
            entity_service: Service for entity data access
            factor_service: Service for factor/historical data access
        """
        self._logger = logging.getLogger("misbuffet.qc_history_provider")
        self._entity_service = entity_service
        self._factor_service = factor_service
        
        # Performance caching
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=10)
        
        # Supported data types
        self._supported_securities = {
            SecurityType.EQUITY: CompanyShare,
            # Can be extended for other security types
        }
        
        self._logger.info("QuantConnect history provider initialized")
    
    def get_history(self, requests: List['HistoryRequest']) -> Dict[str, pd.DataFrame]:
        """
        Get historical data for multiple requests.
        
        Args:
            requests: List of history requests
            
        Returns:
            Dictionary mapping request keys to historical DataFrames
        """
        try:
            results = {}
            
            for request in requests:
                try:
                    key = self._generate_request_key(request)
                    data = self._get_single_history(request)
                    results[key] = data
                    
                except Exception as e:
                    self._logger.error(f"Error processing history request {request}: {e}")
                    results[key] = pd.DataFrame()
            
            return results
            
        except Exception as e:
            self._logger.error(f"Error in get_history: {e}")
            return {}
    
    def get_history_single(self, symbol: Symbol, start: datetime, end: datetime,
                          resolution: Resolution, data_type: type = TradeBar) -> pd.DataFrame:
        """
        Get historical data for a single symbol.
        
        Args:
            symbol: Symbol to get data for
            start: Start date
            end: End date  
            resolution: Data resolution
            data_type: Type of data (TradeBar, QuoteBar, etc.)
            
        Returns:
            DataFrame with historical data
        """
        try:
            # Create history request
            request = HistoryRequest(
                symbol=symbol,
                start_time=start,
                end_time=end,
                resolution=resolution,
                data_type=data_type
            )
            
            return self._get_single_history(request)
            
        except Exception as e:
            self._logger.error(f"Error getting single history for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_history_periods(self, symbol: Symbol, periods: int, 
                           resolution: Resolution, end_time: Optional[datetime] = None,
                           data_type: type = TradeBar) -> pd.DataFrame:
        """
        Get historical data for a specified number of periods.
        
        Args:
            symbol: Symbol to get data for
            periods: Number of periods to retrieve
            resolution: Data resolution
            end_time: End time (default: now)
            data_type: Type of data
            
        Returns:
            DataFrame with historical data
        """
        try:
            end_time = end_time or datetime.now()
            
            # Calculate start time based on resolution and periods
            start_time = self._calculate_start_time(end_time, resolution, periods)
            
            return self.get_history_single(symbol, start_time, end_time, resolution, data_type)
            
        except Exception as e:
            self._logger.error(f"Error getting history periods for {symbol}: {e}")
            return pd.DataFrame()
    
    def create_historical_slices(self, symbols: List[Symbol], start: datetime, 
                               end: datetime, resolution: Resolution) -> Iterator[Slice]:
        """
        Create historical data slices for backtesting.
        
        Args:
            symbols: List of symbols
            start: Start date
            end: End date
            resolution: Data resolution
            
        Yields:
            Slice objects for each time point
        """
        try:
            # Get all historical data
            all_data = {}
            for symbol in symbols:
                data = self.get_history_single(symbol, start, end, resolution)
                if not data.empty:
                    all_data[symbol] = data
            
            if not all_data:
                return
            
            # Find all unique timestamps
            all_timestamps = set()
            for data in all_data.values():
                if 'Date' in data.columns:
                    timestamps = pd.to_datetime(data['Date']).tolist()
                    all_timestamps.update(timestamps)
                elif data.index.name == 'Date':
                    timestamps = pd.to_datetime(data.index).tolist()
                    all_timestamps.update(timestamps)
            
            # Sort timestamps
            sorted_timestamps = sorted(all_timestamps)
            
            # Generate slices
            for timestamp in sorted_timestamps:
                slice_obj = self._create_slice_for_timestamp(timestamp, symbols, all_data)
                if slice_obj.has_data:
                    yield slice_obj
                    
        except Exception as e:
            self._logger.error(f"Error creating historical slices: {e}")
    
    def is_valid_trading_day(self, date: datetime) -> bool:
        """Check if a date is a valid trading day."""
        try:
            # Simple implementation - can be enhanced with market calendars
            if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Check for major holidays (simplified)
            major_holidays = {
                (1, 1),    # New Year's Day
                (7, 4),    # Independence Day  
                (12, 25),  # Christmas
            }
            
            if (date.month, date.day) in major_holidays:
                return False
            
            return True
            
        except Exception:
            return False
    
    # Private methods
    
    def _get_single_history(self, request: 'HistoryRequest') -> pd.DataFrame:
        """Get historical data for a single request."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if self._is_cached(cache_key):
                return self._cache[cache_key].copy()
            
            # Get data based on security type
            if request.symbol.security_type == SecurityType.EQUITY:
                data = self._get_equity_history(request)
            elif request.symbol.security_type == SecurityType.FOREX:
                data = self._get_forex_history(request)
            elif request.symbol.security_type == SecurityType.CRYPTO:
                data = self._get_crypto_history(request)
            else:
                self._logger.warning(f"Unsupported security type: {request.symbol.security_type}")
                data = pd.DataFrame()
            
            # Cache the result
            if not data.empty:
                self._cache[cache_key] = data.copy()
                self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
            
            return data
            
        except Exception as e:
            self._logger.error(f"Error getting single history: {e}")
            return pd.DataFrame()
    
    def _get_equity_history(self, request: 'HistoryRequest') -> pd.DataFrame:
        """Get historical data for equity symbols."""
        try:
            if not self._entity_service or not self._factor_service:
                self._logger.warning("Entity or factor service not available")
                return pd.DataFrame()
            
            # Get entity
            ticker = request.symbol.value
            entity = self._entity_service.get_by_symbol(CompanyShare, ticker)
            
            if not entity:
                # Try to create entity
                entity = self._entity_service._create_or_get_ibkr(CompanyShare, ticker)
                if not entity:
                    entity = self._entity_service._create_or_get(CompanyShare, ticker)
                
                if not entity:
                    self._logger.warning(f"Could not find or create entity for {ticker}")
                    return pd.DataFrame()
            
            # Get factor data
            factor_names = self._get_equity_factor_names(request.data_type)
            data_dict = {}
            
            for factor_name in factor_names:
                factor = self._factor_service.get_factor_by_name(factor_name)
                if factor:
                    factor_values = self._factor_service.get_factor_values(
                        factor_id=int(factor.id),
                        entity_id=entity.id,
                        start_date=request.start_time.strftime('%Y-%m-%d'),
                        end_date=request.end_time.strftime('%Y-%m-%d')
                    )
                    
                    # Process factor values
                    dates = []
                    values = []
                    for fv in factor_values:
                        dates.append(fv.date)
                        values.append(float(fv.value))
                    
                    if dates and values:
                        data_dict[factor_name] = dict(zip(dates, values))
            
            # Convert to DataFrame
            if data_dict:
                # Find all dates
                all_dates = set()
                for factor_data in data_dict.values():
                    all_dates.update(factor_data.keys())
                
                all_dates = sorted(all_dates)
                
                # Build DataFrame
                df_data = {'Date': all_dates}
                for factor_name, factor_data in data_dict.items():
                    df_data[factor_name] = [factor_data.get(date, None) for date in all_dates]
                
                df = pd.DataFrame(df_data)
                df = df.dropna()  # Remove rows with missing data
                
                self._logger.debug(f"Retrieved {len(df)} equity history records for {ticker}")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            self._logger.error(f"Error getting equity history: {e}")
            return pd.DataFrame()
    
    def _get_forex_history(self, request: 'HistoryRequest') -> pd.DataFrame:
        """Get historical data for forex pairs (placeholder)."""
        try:
            # This would be implemented based on available forex data sources
            self._logger.warning(f"Forex history not yet implemented for {request.symbol.value}")
            return pd.DataFrame()
            
        except Exception as e:
            self._logger.error(f"Error getting forex history: {e}")
            return pd.DataFrame()
    
    def _get_crypto_history(self, request: 'HistoryRequest') -> pd.DataFrame:
        """Get historical data for crypto pairs (placeholder)."""
        try:
            # This would be implemented based on available crypto data sources
            self._logger.warning(f"Crypto history not yet implemented for {request.symbol.value}")
            return pd.DataFrame()
            
        except Exception as e:
            self._logger.error(f"Error getting crypto history: {e}")
            return pd.DataFrame()
    
    def _get_equity_factor_names(self, data_type: type) -> List[str]:
        """Get relevant factor names for equity data type."""
        if data_type == TradeBar:
            return ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        elif data_type == QuoteBar:
            return ['Bid', 'Ask', 'BidSize', 'AskSize']
        else:
            return ['Close', 'Volume']
    
    def _calculate_start_time(self, end_time: datetime, resolution: Resolution, 
                            periods: int) -> datetime:
        """Calculate start time based on resolution and periods."""
        try:
            if resolution == Resolution.TICK:
                return end_time - timedelta(hours=periods)
            elif resolution == Resolution.SECOND:
                return end_time - timedelta(seconds=periods)
            elif resolution == Resolution.MINUTE:
                return end_time - timedelta(minutes=periods)
            elif resolution == Resolution.HOUR:
                return end_time - timedelta(hours=periods)
            elif resolution == Resolution.DAILY:
                # Account for weekends and holidays
                return end_time - timedelta(days=periods * 1.5)
            elif resolution == Resolution.WEEKLY:
                return end_time - timedelta(weeks=periods)
            elif resolution == Resolution.MONTHLY:
                return end_time - timedelta(days=periods * 32)  # ~1 month
            else:
                return end_time - timedelta(days=periods)
                
        except Exception:
            return end_time - timedelta(days=periods)
    
    def _create_slice_for_timestamp(self, timestamp: datetime, symbols: List[Symbol], 
                                  all_data: Dict[Symbol, pd.DataFrame]) -> Slice:
        """Create a data slice for a specific timestamp."""
        try:
            from ..common.data_types import TradeBars, QuoteBars, Ticks
            
            bars = TradeBars()
            quote_bars = QuoteBars()
            ticks = Ticks()
            
            for symbol in symbols:
                if symbol not in all_data:
                    continue
                
                data = all_data[symbol]
                
                # Find data for this timestamp
                if 'Date' in data.columns:
                    mask = pd.to_datetime(data['Date']) == timestamp
                    row_data = data[mask]
                elif data.index.name == 'Date':
                    row_data = data[data.index == timestamp]
                else:
                    continue
                
                if not row_data.empty:
                    row = row_data.iloc[0]
                    
                    # Create TradeBar if OHLCV data available
                    if all(col in row_data.columns for col in ['Open', 'High', 'Low', 'Close']):
                        trade_bar = TradeBar(
                            symbol=symbol,
                            time=timestamp,
                            end_time=timestamp,
                            open=float(row.get('Open', 0)),
                            high=float(row.get('High', 0)), 
                            low=float(row.get('Low', 0)),
                            close=float(row.get('Close', 0)),
                            volume=int(row.get('Volume', 0))
                        )
                        bars[symbol] = trade_bar
                    
                    # Create QuoteBar if bid/ask data available
                    elif all(col in row_data.columns for col in ['Bid', 'Ask']):
                        quote_bar = QuoteBar(
                            symbol=symbol,
                            time=timestamp,
                            end_time=timestamp,
                            bid_close=float(row.get('Bid', 0)),
                            ask_close=float(row.get('Ask', 0)),
                            bid_size=int(row.get('BidSize', 0)),
                            ask_size=int(row.get('AskSize', 0))
                        )
                        quote_bars[symbol] = quote_bar
            
            return Slice(
                time=timestamp,
                bars=bars,
                quote_bars=quote_bars,
                ticks=ticks
            )
            
        except Exception as e:
            self._logger.error(f"Error creating slice for timestamp {timestamp}: {e}")
            return Slice(time=timestamp)
    
    def _generate_request_key(self, request: 'HistoryRequest') -> str:
        """Generate a unique key for a history request."""
        return f"{request.symbol.value}_{request.resolution.value}_{request.data_type.__name__}"
    
    def _generate_cache_key(self, request: 'HistoryRequest') -> str:
        """Generate a cache key for a history request."""
        return (f"{request.symbol.value}_{request.start_time.strftime('%Y%m%d')}_"
                f"{request.end_time.strftime('%Y%m%d')}_{request.resolution.value}")
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is available in cache and not expired."""
        return (cache_key in self._cache and 
                cache_key in self._cache_expiry and
                self._cache_expiry[cache_key] > datetime.now())
    
    def initialize(self, **kwargs) -> bool:
        """Initialize the history provider."""
        try:
            self._logger.info("QuantConnect history provider initialized")
            return True
        except Exception as e:
            self._logger.error(f"Error initializing history provider: {e}")
            return False


@dataclass  
class HistoryRequest:
    """Request for historical data."""
    symbol: Symbol
    start_time: datetime
    end_time: datetime
    resolution: Resolution
    data_type: type = TradeBar
    fill_forward: bool = True
    extended_market_hours: bool = False
    
    def __str__(self) -> str:
        return (f"HistoryRequest({self.symbol.value}, {self.start_time.date()}, "
                f"{self.end_time.date()}, {self.resolution.value})")


class QuantConnectSliceBuilder:
    """
    Builder for creating QuantConnect-compatible data slices with enhanced functionality.
    """
    
    def __init__(self, history_provider: Optional[QuantConnectHistoryProvider] = None):
        """Initialize the slice builder."""
        self._logger = logging.getLogger("misbuffet.qc_slice_builder")
        self._history_provider = history_provider
    
    def build_slice_from_data(self, timestamp: datetime, 
                            data_points: List[BaseData]) -> Slice:
        """
        Build a data slice from a list of data points.
        
        Args:
            timestamp: Slice timestamp
            data_points: List of BaseData objects
            
        Returns:
            Constructed Slice object
        """
        try:
            from ..common.data_types import TradeBars, QuoteBars, Ticks
            
            bars = TradeBars()
            quote_bars = QuoteBars()
            ticks = Ticks()
            
            for data_point in data_points:
                if not hasattr(data_point, 'symbol') or not data_point.symbol:
                    continue
                
                symbol = data_point.symbol
                
                if isinstance(data_point, TradeBar):
                    bars[symbol] = data_point
                elif isinstance(data_point, QuoteBar):
                    quote_bars[symbol] = data_point
                elif hasattr(data_point, 'tick_type'):  # Tick
                    if symbol not in ticks:
                        ticks[symbol] = []
                    ticks[symbol].append(data_point)
                else:
                    # Convert generic BaseData to TradeBar
                    if hasattr(data_point, 'value') and data_point.value > 0:
                        trade_bar = TradeBar(
                            symbol=symbol,
                            time=data_point.time,
                            end_time=data_point.end_time,
                            open=data_point.value,
                            high=data_point.value,
                            low=data_point.value, 
                            close=data_point.value,
                            volume=0
                        )
                        bars[symbol] = trade_bar
            
            slice_obj = Slice(
                time=timestamp,
                bars=bars,
                quote_bars=quote_bars,
                ticks=ticks
            )
            
            self._logger.debug(f"Built slice at {timestamp} with {len(bars)} bars, "
                             f"{len(quote_bars)} quote bars, {len(ticks)} tick series")
            
            return slice_obj
            
        except Exception as e:
            self._logger.error(f"Error building slice from data: {e}")
            return Slice(time=timestamp)
    
    def build_slice_from_history(self, timestamp: datetime, symbols: List[Symbol]) -> Slice:
        """
        Build a data slice by fetching historical data for a specific timestamp.
        
        Args:
            timestamp: Target timestamp
            symbols: List of symbols to include
            
        Returns:
            Constructed Slice object
        """
        try:
            if not self._history_provider:
                return Slice(time=timestamp)
            
            from ..common.data_types import TradeBars, QuoteBars, Ticks
            
            bars = TradeBars()
            quote_bars = QuoteBars()
            ticks = Ticks()
            
            # Get data for each symbol
            for symbol in symbols:
                try:
                    # Get single day data around the timestamp
                    start_time = timestamp - timedelta(days=1)
                    end_time = timestamp + timedelta(days=1)
                    
                    data = self._history_provider.get_history_single(
                        symbol, start_time, end_time, Resolution.DAILY
                    )
                    
                    if not data.empty:
                        # Find closest data point to timestamp
                        if 'Date' in data.columns:
                            data['Date'] = pd.to_datetime(data['Date'])
                            closest_idx = (data['Date'] - timestamp).abs().idxmin()
                            row = data.iloc[closest_idx]
                            
                            # Create TradeBar
                            trade_bar = TradeBar(
                                symbol=symbol,
                                time=timestamp,
                                end_time=timestamp,
                                open=float(row.get('Open', 0)),
                                high=float(row.get('High', 0)),
                                low=float(row.get('Low', 0)),
                                close=float(row.get('Close', 0)),
                                volume=int(row.get('Volume', 0))
                            )
                            bars[symbol] = trade_bar
                        
                except Exception as e:
                    self._logger.warning(f"Error getting history for {symbol}: {e}")
                    continue
            
            return Slice(
                time=timestamp,
                bars=bars,
                quote_bars=quote_bars,
                ticks=ticks
            )
            
        except Exception as e:
            self._logger.error(f"Error building slice from history: {e}")
            return Slice(time=timestamp)