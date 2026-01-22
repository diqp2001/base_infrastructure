"""
QuantConnect-style Data Management Layer for Misbuffet Service

This module provides QuantConnect-compatible data feed subscriptions, history data slice creation,
and frontier time management, reusing existing misbuffet handlers and managers while integrating
with the current repository and data services.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import pandas as pd

from ..common.symbol import Symbol
from ..common.enums import Resolution, SecurityType, MarketDataType
from ..common.data_types import (
    Slice, TradeBar, QuoteBar, Tick, BaseData, 
    SubscriptionDataConfig, TradeBars, QuoteBars, Ticks
)
from .subscription_manager import SubscriptionManager, SubscriptionRequest
from .data_feed import DataFeed, FileSystemDataFeed, LiveTradingDataFeed
from .history_provider import IHistoryProvider

# Import existing services for database integration
from src.application.services.data.entities.entity_service import EntityService
from src.application.services.data.entities.factor.factor_service import FactorService
from src.domain.entities.finance.financial_assets.company_share import CompanyShare


class QuantConnectDataManager:
    """
    QuantConnect-style data management layer that bridges QC patterns with misbuffet infrastructure.
    
    This class provides:
    - Data feed subscription management using existing SubscriptionManager
    - History data access using existing data services and repositories  
    - Frontier time management for backtesting
    - Data slice creation compatible with QC OnData() patterns
    """
    
    def __init__(self, data_feed: Optional[DataFeed] = None, 
                 entity_service: Optional[EntityService] = None,
                 factor_service: Optional[FactorService] = None):
        """
        Initialize the QuantConnect data manager.
        
        Args:
            data_feed: Existing DataFeed instance (FileSystemDataFeed, LiveTradingDataFeed, etc.)
            entity_service: Service for entity data access
            factor_service: Service for factor/historical data access
        """
        self._logger = logging.getLogger("misbuffet.qc_data_manager")
        
        # Core components - reuse existing misbuffet infrastructure
        self._data_feed = data_feed or FileSystemDataFeed("./data")
        self._subscription_manager = SubscriptionManager()
        self._entity_service = entity_service
        self._factor_service = factor_service
        
        # Frontier time management
        self._frontier_time: Optional[datetime] = None
        self._universe: List[str] = []
        
        # Data caching for performance
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
        
        # History provider integration
        self._history_provider: Optional[IHistoryProvider] = None
        
        self._logger.info("QuantConnect data manager initialized")
    
    def initialize(self) -> bool:
        """Initialize the data manager and underlying data feed."""
        try:
            success = self._data_feed.initialize()
            if success:
                self._logger.info("QuantConnect data manager initialization completed")
            else:
                self._logger.error("Data feed initialization failed")
            return success
        except Exception as e:
            self._logger.error(f"Error initializing QuantConnect data manager: {e}")
            return False
    
    def add_equity(self, ticker: str, resolution: Resolution = Resolution.DAILY, 
                   market: str = "USA") -> Symbol:
        """
        QuantConnect AddEquity() equivalent - creates subscription and ensures entity exists.
        
        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            resolution: Data resolution (Daily, Minute, etc.)
            market: Market identifier
            
        Returns:
            Symbol object for the equity
        """
        try:
            # Create symbol
            symbol = Symbol.create_equity(ticker, market)
            
            # Create subscription request
            request = SubscriptionRequest(
                symbol=symbol,
                resolution=resolution,
                data_type=TradeBar,
                fill_forward=True,
                extended_market_hours=False
            )
            
            # Convert to config and add subscription
            config = request.to_config()
            success = self._subscription_manager.add_subscription(config)
            
            if success:
                # Create data feed subscription using existing infrastructure
                feed_config = self._data_feed.create_subscription(symbol, resolution)
                
                # Ensure entity exists in database using existing entity service
                if self._entity_service:
                    self._ensure_entity_exists(ticker)
                
                # Add to universe
                if ticker not in self._universe:
                    self._universe.append(ticker)
                
                self._logger.info(f"✅ Added equity subscription: {ticker} at {resolution.value} resolution")
            else:
                self._logger.warning(f"⚠️ Subscription already exists for {ticker}")
            
            return symbol
            
        except Exception as e:
            self._logger.error(f"Error adding equity {ticker}: {e}")
            raise
    
    def add_forex(self, pair: str, resolution: Resolution = Resolution.DAILY) -> Symbol:
        """Add forex pair subscription."""
        try:
            symbol = Symbol.create_forex(pair)
            
            request = SubscriptionRequest(
                symbol=symbol,
                resolution=resolution,
                data_type=QuoteBar,
                fill_forward=True
            )
            
            config = request.to_config()
            self._subscription_manager.add_subscription(config)
            self._data_feed.create_subscription(symbol, resolution)
            
            if pair not in self._universe:
                self._universe.append(pair)
            
            self._logger.info(f"✅ Added forex subscription: {pair}")
            return symbol
            
        except Exception as e:
            self._logger.error(f"Error adding forex {pair}: {e}")
            raise
    
    def add_crypto(self, pair: str, resolution: Resolution = Resolution.DAILY) -> Symbol:
        """Add cryptocurrency pair subscription."""
        try:
            symbol = Symbol.create_crypto(pair)
            
            request = SubscriptionRequest(
                symbol=symbol,
                resolution=resolution,
                data_type=TradeBar,
                fill_forward=True
            )
            
            config = request.to_config()
            self._subscription_manager.add_subscription(config)
            self._data_feed.create_subscription(symbol, resolution)
            
            if pair not in self._universe:
                self._universe.append(pair)
            
            self._logger.info(f"✅ Added crypto subscription: {pair}")
            return symbol
            
        except Exception as e:
            self._logger.error(f"Error adding crypto {pair}: {e}")
            raise
    
    def history(self, symbols: Union[str, List[str], Symbol, List[Symbol]], 
                periods: int, resolution: Resolution = Resolution.DAILY,
                end_time: Optional[datetime] = None) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        QuantConnect History() equivalent using existing data services.
        
        Args:
            symbols: Symbol(s) to get history for
            periods: Number of periods to retrieve
            resolution: Data resolution
            end_time: End time for historical data (default: now)
            
        Returns:
            DataFrame or dictionary of DataFrames with historical data
        """
        try:
            # Normalize symbols input
            if isinstance(symbols, (str, Symbol)):
                symbols = [symbols]
            
            # Convert Symbol objects to strings
            ticker_symbols = []
            for symbol in symbols:
                if isinstance(symbol, Symbol):
                    ticker_symbols.append(symbol.value)
                else:
                    ticker_symbols.append(str(symbol))
            
            # Use existing factor service for historical data
            if self._factor_service and len(ticker_symbols) == 1:
                return self._get_historical_data_from_service(
                    ticker_symbols[0], periods, end_time
                )
            elif self._factor_service and len(ticker_symbols) > 1:
                result = {}
                for ticker in ticker_symbols:
                    result[ticker] = self._get_historical_data_from_service(
                        ticker, periods, end_time
                    )
                return result
            else:
                # Fallback to data feed
                self._logger.warning("No factor service available, using data feed fallback")
                return self._get_historical_data_from_feed(ticker_symbols, periods, end_time)
                
        except Exception as e:
            self._logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame() if len(ticker_symbols) == 1 else {}
    
    def create_data_slice(self, current_time: datetime, 
                         universe: Optional[List[str]] = None) -> Slice:
        """
        Create QuantConnect-style data slice using existing data infrastructure.
        
        Args:
            current_time: Current frontier time
            universe: List of symbols to include (default: current universe)
            
        Returns:
            Slice object containing all market data for the time point
        """
        try:
            universe = universe or self._universe
            self._frontier_time = current_time
            
            # Get next data ticks from existing data feed
            data_points = self._data_feed.get_next_ticks()
            
            # Create slice containers
            bars = TradeBars()
            quote_bars = QuoteBars()
            ticks = Ticks()
            
            # Process data points
            for data_point in data_points:
                if hasattr(data_point, 'symbol') and data_point.symbol:
                    symbol = data_point.symbol
                    
                    # Route data based on type
                    if isinstance(data_point, TradeBar):
                        bars[symbol] = data_point
                    elif isinstance(data_point, QuoteBar):
                        quote_bars[symbol] = data_point
                    elif isinstance(data_point, Tick):
                        if symbol not in ticks:
                            ticks[symbol] = []
                        ticks[symbol].append(data_point)
                    else:
                        # Convert BaseData to TradeBar if possible
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
            
            # Create slice
            slice_obj = Slice(
                time=current_time,
                bars=bars,
                quote_bars=quote_bars,
                ticks=ticks
            )
            
            self._logger.debug(f"Created data slice at {current_time} with {len(bars)} bars, "
                             f"{len(quote_bars)} quote bars, {len(ticks)} tick series")
            
            return slice_obj
            
        except Exception as e:
            self._logger.error(f"Error creating data slice: {e}")
            # Return empty slice
            return Slice(time=current_time)
    
    def get_frontier_time(self) -> Optional[datetime]:
        """Get current algorithm frontier time (QuantConnect concept)."""
        return self._frontier_time
    
    def set_frontier_time(self, time: datetime) -> None:
        """Set current algorithm frontier time."""
        self._frontier_time = time
    
    def get_universe(self) -> List[str]:
        """Get current universe of subscribed symbols."""
        return self._universe.copy()
    
    def set_universe(self, universe: List[str], 
                    resolution: Resolution = Resolution.DAILY) -> None:
        """
        Set universe and create subscriptions for all symbols.
        
        Args:
            universe: List of ticker symbols
            resolution: Data resolution for all symbols
        """
        try:
            # Clear existing universe
            self._universe.clear()
            
            # Add subscriptions for new universe
            for ticker in universe:
                self.add_equity(ticker, resolution)
            
            self._logger.info(f"Universe updated with {len(universe)} symbols")
            
        except Exception as e:
            self._logger.error(f"Error setting universe: {e}")
    
    def get_subscriptions(self) -> List[SubscriptionDataConfig]:
        """Get all active subscriptions."""
        return self._subscription_manager.get_subscriptions()
    
    def get_subscription_statistics(self) -> Dict[str, Any]:
        """Get subscription statistics."""
        return self._subscription_manager.get_subscription_statistics()
    
    def remove_subscription(self, symbol: Union[Symbol, str]) -> bool:
        """Remove subscription for a symbol."""
        try:
            if isinstance(symbol, str):
                symbol = Symbol.create_equity(symbol)
            
            success = self._subscription_manager.remove_symbol(symbol)
            
            if success:
                # Remove from universe
                symbol_str = symbol.value
                if symbol_str in self._universe:
                    self._universe.remove(symbol_str)
                
                self._logger.info(f"Removed subscription for {symbol_str}")
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error removing subscription: {e}")
            return False
    
    def is_subscribed(self, symbol: Union[Symbol, str], 
                     resolution: Optional[Resolution] = None) -> bool:
        """Check if a symbol is subscribed."""
        try:
            if isinstance(symbol, str):
                symbol = Symbol.create_equity(symbol)
            
            return self._subscription_manager.is_subscribed(symbol, resolution)
            
        except Exception as e:
            self._logger.error(f"Error checking subscription: {e}")
            return False
    
    def set_data_normalization(self, symbol: Union[Symbol, str], 
                              normalization: str) -> bool:
        """Set data normalization mode for a symbol."""
        # This would integrate with existing data normalization in misbuffet
        try:
            self._logger.info(f"Data normalization set to {normalization} for {symbol}")
            return True
        except Exception as e:
            self._logger.error(f"Error setting data normalization: {e}")
            return False
    
    def dispose(self) -> None:
        """Clean up resources."""
        try:
            self._subscription_manager.clear()
            self._data_cache.clear()
            self._cache_expiry.clear()
            
            if self._data_feed:
                self._data_feed.dispose()
            
            self._logger.info("QuantConnect data manager disposed")
            
        except Exception as e:
            self._logger.error(f"Error disposing data manager: {e}")
    
    # Private helper methods
    
    def _ensure_entity_exists(self, ticker: str) -> bool:
        """Ensure entity exists in database using existing entity service."""
        try:
            if not self._entity_service:
                return False
            
            # Try to get existing entity
            entity = self._entity_service.get_by_symbol(CompanyShare, ticker)
            
            if not entity:
                # Try to create from external data source (IBKR, etc.)
                entity = self._entity_service._create_or_get_ibkr(CompanyShare, ticker)
                if entity:
                    self._logger.info(f"✅ Created entity for {ticker} from external data")
                    return True
                
                # Create basic entity
                entity = self._entity_service._create_or_get(CompanyShare, ticker)
                if entity:
                    self._logger.info(f"✅ Created basic entity for {ticker}")
                    return True
                else:
                    self._logger.warning(f"⚠️ Could not create entity for {ticker}")
                    return False
            else:
                self._logger.debug(f"Entity already exists for {ticker}")
                return True
                
        except Exception as e:
            self._logger.error(f"Error ensuring entity exists for {ticker}: {e}")
            return False
    
    def _get_historical_data_from_service(self, ticker: str, periods: int, 
                                        end_time: Optional[datetime] = None) -> pd.DataFrame:
        """Get historical data using existing factor service."""
        try:
            # Check cache first
            cache_key = f"{ticker}_{periods}_{end_time}"
            if (cache_key in self._data_cache and 
                cache_key in self._cache_expiry and 
                self._cache_expiry[cache_key] > datetime.now()):
                return self._data_cache[cache_key].copy()
            
            # Get entity
            entity = self._entity_service.get_by_symbol(CompanyShare, ticker) if self._entity_service else None
            if not entity:
                self._logger.warning(f"No entity found for {ticker}")
                return pd.DataFrame()
            
            # Calculate date range
            end_date = end_time or datetime.now()
            start_date = end_date - timedelta(days=periods * 2)  # Buffer for weekends/holidays
            
            # Get factor data for common OHLCV factors
            factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            data_dict = {'Date': []}
            
            for factor_name in factor_names:
                factor = self._factor_service.get_factor_by_name(factor_name)
                if factor:
                    factor_values = self._factor_service.get_factor_values(
                        factor_id=int(factor.id),
                        entity_id=entity.id,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                    
                    # Convert to dictionary format
                    dates = []
                    values = []
                    for fv in factor_values:
                        dates.append(fv.date)
                        values.append(float(fv.value))
                    
                    if dates and values:
                        data_dict[factor_name] = values
                        if not data_dict['Date']:
                            data_dict['Date'] = dates
            
            # Create DataFrame
            if data_dict['Date']:
                df = pd.DataFrame(data_dict)
                df = df.sort_values('Date').tail(periods)  # Get requested number of periods
                
                # Cache the result
                self._data_cache[cache_key] = df.copy()
                self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
                
                self._logger.debug(f"Retrieved {len(df)} historical records for {ticker}")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self._logger.error(f"Error getting historical data from service for {ticker}: {e}")
            return pd.DataFrame()
    
    def _get_historical_data_from_feed(self, tickers: List[str], periods: int,
                                     end_time: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        """Fallback method to get historical data from data feed."""
        try:
            result = {}
            for ticker in tickers:
                # This would use the existing data feed infrastructure
                # For now, return empty DataFrame as placeholder
                result[ticker] = pd.DataFrame()
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error getting historical data from feed: {e}")
            return {ticker: pd.DataFrame() for ticker in tickers}


class QuantConnectCompatibilityLayer:
    """
    Provides additional QuantConnect-style convenience methods and aliases.
    """
    
    def __init__(self, data_manager: QuantConnectDataManager):
        self.data_manager = data_manager
    
    # QuantConnect method aliases
    def AddEquity(self, ticker: str, resolution: Resolution = Resolution.DAILY) -> Symbol:
        """QuantConnect-style method name (PascalCase)."""
        return self.data_manager.add_equity(ticker, resolution)
    
    def AddForex(self, pair: str, resolution: Resolution = Resolution.DAILY) -> Symbol:
        """QuantConnect-style method name (PascalCase)."""
        return self.data_manager.add_forex(pair, resolution)
    
    def AddCrypto(self, pair: str, resolution: Resolution = Resolution.DAILY) -> Symbol:
        """QuantConnect-style method name (PascalCase).""" 
        return self.data_manager.add_crypto(pair, resolution)
    
    def History(self, symbols: Union[str, List[str]], periods: int, 
               resolution: Resolution = Resolution.DAILY) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """QuantConnect-style method name (PascalCase)."""
        return self.data_manager.history(symbols, periods, resolution)
    
    def SetUniverse(self, universe: List[str], resolution: Resolution = Resolution.DAILY) -> None:
        """QuantConnect-style method name (PascalCase)."""
        self.data_manager.set_universe(universe, resolution)
    
    @property
    def Time(self) -> Optional[datetime]:
        """QuantConnect-style property name (PascalCase)."""
        return self.data_manager.get_frontier_time()