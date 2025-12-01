"""
BaseProjectAlgorithm - Simple 200-day moving average trading algorithm.

Implements a straightforward 200-day moving average strategy:
- Long position when current price > 200-day average
- Short position when current price < 200-day average

Factor creation remains the same, backtesting uses Misbuffet framework.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sklearn.ensemble import RandomForestClassifier

# Misbuffet framework imports
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution, 
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm
from application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer

# Test base project imports
from ..data.data_loader import SpatiotemporalDataLoader
from ..data.feature_engineer import SpatiotemporalFeatureEngineer
from ..data.factor_manager import FactorEnginedDataManager
from ..models.spatiotemporal_model import HybridSpatiotemporalModel
from ..models.model_trainer import SpatiotemporalModelTrainer
from ..strategy.momentum_strategy import SpatiotemporalMomentumStrategy
from ..strategy.portfolio_optimizer import HybridPortfolioOptimizer
from ..config import get_config


class BaseProjectAlgorithm(QCAlgorithm):
    """
    Simple 200-day moving average trading algorithm:
    - Compare current price to 200-day moving average
    - Long when price > 200-day average
    - Short when price < 200-day average
    
    Uses factor creation system for data storage and
    Misbuffet framework for backtesting.
    """
    
    def initialize(self):
        """Initialize the algorithm following MyAlgorithm pattern."""
        # Call parent initialization first
        super().initialize()
        
        # Load configuration
        self.config = get_config('test')
        
        # Define universe and store Security objects
        self.universe = self.config['DATA']['DEFAULT_UNIVERSE']
        self.my_securities = {}  # Dictionary to store Security objects by ticker for easy lookup
        
        for ticker in self.universe:
            try:
                security = self.add_equity(ticker, Resolution.DAILY)
                if security is not None:
                    # Store in our custom dictionary for easy ticker-based lookup
                    self.my_securities[ticker] = security
                    self.log(f"Successfully added security: {ticker} -> {security.symbol}")
                else:
                    self.log(f"Warning: Failed to add security {ticker} - got None")
            except Exception as e:
                self.log(f"Error adding security {ticker}: {str(e)}")

        # Algorithm parameters
        self.moving_average_window = 200  # 200-day moving average
        self.lookback_window = 20         # volatility window (kept for compatibility)
        self.train_window = 252           # data history window
        self.retrain_interval = timedelta(days=1)  # Daily signal updates
        self.last_train_time = None

        # Signal storage - simple 200-day average signals
        self.moving_averages = {}  # 200-day moving averages per ticker
        self.signals = {}          # Binary signals: 1 (long) or -1 (short)
        self.last_prices = {}      # Store last prices for comparison
        
        # Data tracking for flexible data format handling
        self._current_data_frame = None
        self._current_data_slice = None

        
        # Defer initial training until dependencies are injected
        # This will be triggered by the first on_data() call or explicit training call
        self._initial_training_completed = False

    

    # ---------------------------
    # Features (Enhanced with factor system)
    # ---------------------------


   
    def _setup_factor_data_for_ticker(self, ticker: str, current_time: datetime) -> pd.DataFrame:
        """
        Set up factor-based data for a specific ticker, similar to setup_factor_system.
        
        This replaces _prepare_features() and uses the comprehensive factor system
        instead of basic technical analysis.
        """
        try:
            self.log(f"Setting up factor data for {ticker}...")
            
            # If we have a factor manager, use the comprehensive factor system
            if hasattr(self, 'factor_manager') and self.factor_manager:
                self.log(f"Using factor manager for {ticker} data...")
                
                # Ensure entity exists for this ticker
                try:
                    self.factor_manager._ensure_entities_exist([ticker])
                except Exception as e:
                    self.log(f"Warning: Could not ensure entities for {ticker}: {e}")
                
                # Get factor data for the training window
                try:
                    # Get comprehensive factor data including price, momentum, and technical factors
                    factor_data = self.factor_manager.get_factor_data_for_training(
                        tickers=[ticker],
                        factor_groups=['price', 'momentum', 'technical'],
                        lookback_days=self.train_window,
                        end_date=current_time
                    )
                    
                    if factor_data is not None and not factor_data.empty:
                        self.log(f"Retrieved {len(factor_data)} factor data points for {ticker}")
                        
                        # Convert factor data to the format expected by the model
                        df = self._convert_factor_data_to_training_format(factor_data, ticker)
                        if not df.empty:
                            return df
                    else:
                        self.log(f"No factor data available for {ticker}, falling back to basic features")
                except Exception as e:
                    self.log(f"Error getting factor data for {ticker}: {e}")
                
            
            
        except Exception as e:
            self.log(f"Error setting up factor data for {ticker}: {str(e)}")
            # Return empty DataFrame to trigger fallback logic
            return pd.DataFrame()
    
    def _convert_factor_data_to_training_format(self, factor_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Convert factor system data to the format expected by the training algorithm.
        
        This ensures compatibility with existing model training code that expects
        specific column names like return_lag1, return_lag2, volatility, etc.
        """
        try:
            df = factor_data.copy()
            
            # Map factor system columns to expected training columns
            column_mapping = {}
            
            # Price-based features - handle different price column names including ticker-prefixed
            price_column = None
            # First try exact matches
            for col in ['Close', 'close', 'Adj Close', 'price']:
                if col in df.columns:
                    price_column = col
                    break
            
            # If no exact match, look for ticker-prefixed columns
            if not price_column:
                for col in df.columns:
                    col_lower = col.lower()
                    if any(price_suffix in col_lower for price_suffix in ['_close', '_adj close', '_price']):
                        price_column = col
                        break
            
            if price_column:
                df['close'] = df[price_column]
                df["return"] = df["close"].pct_change()
                df["return_lag1"] = df["return"].shift(1)
                df["return_lag2"] = df["return"].shift(2)
                df["return_fwd1"] = df["return"].shift(-1)  # Target variable
                column_mapping[price_column] = 'close'
            else:
                error_msg = f"ERROR: No price column found for {ticker}. Available columns: {list(df.columns)}"
                self.log(error_msg)
                raise ValueError(error_msg)
            
            # Volatility from factor system or calculate it
            volatility_column = None
            # First try exact matches
            for col in ['realized_vol', 'daily_vol', 'volatility', 'vol_of_vol']:
                if col in df.columns:
                    volatility_column = col
                    break
            
            # If no exact match, look for ticker-prefixed volatility columns
            if not volatility_column:
                for col in df.columns:
                    col_lower = col.lower()
                    if any(vol_suffix in col_lower for vol_suffix in ['_realized_vol', '_daily_vol', '_volatility', '_vol_of_vol']):
                        volatility_column = col
                        break
            
            if volatility_column:
                df['volatility'] = df[volatility_column]
                column_mapping[volatility_column] = 'volatility'
            elif 'close' in df.columns or price_column:
                # Calculate volatility if not available in factor system
                df["volatility"] = df["return"].rolling(self.lookback_window).std()
                self.log(f"Calculated volatility for {ticker} using rolling window")
            else:
                error_msg = f"ERROR: No volatility data available for {ticker} and cannot calculate from price data"
                self.log(error_msg)
                raise ValueError(error_msg)
            
            # Use momentum factors from the factor system
            momentum_factors = ['deep_momentum_1d', 'deep_momentum_5d', 'deep_momentum_21d', 'deep_momentum_63d']
            for factor in momentum_factors:
                if factor in df.columns:
                    # Keep momentum factors as they are - they're already properly calculated
                    continue
            
            # Use technical indicators from factor system
            technical_factors = ['rsi_14', 'macd', 'bollinger_upper', 'bollinger_lower']
            for factor in technical_factors:
                if factor in df.columns:
                    # Keep technical factors as they are
                    continue
            
            self.log(f"Converted factor data for {ticker}: {len(df)} rows, columns: {list(df.columns)}")
            return df.dropna()
            
        except Exception as e:
            self.log(f"Error converting factor data for {ticker}: {str(e)}")
            return pd.DataFrame()

    # ---------------------------
    # Calculate 200-day moving averages
    # ---------------------------
    def _calculate_moving_average_for_ticker(self, ticker: str, current_time: datetime):
        """
        Calculate 200-day moving average for a specific ticker.
        
        Simple price-based moving average calculation.
        """
        try:
            history = self.history(
                [ticker],
                self.moving_average_window + 20,  # Extra buffer for data
                Resolution.DAILY,
                end_time=current_time
            )

            df = self._setup_factor_data_for_ticker(ticker, current_time)
            if df.empty or len(df) < self.moving_average_window:
                self.log(f"Insufficient data for {ticker}: need {self.moving_average_window} days, got {len(df)}")
                return None

            # Calculate 200-day simple moving average
            if 'close' in df.columns:
                moving_avg = df['close'].rolling(window=self.moving_average_window).mean().iloc[-1]
                current_price = df['close'].iloc[-1]
                
                self.log(f"{ticker}: Current price ${current_price:.2f}, 200-day MA ${moving_avg:.2f}")
                return {
                    'moving_average': moving_avg,
                    'current_price': current_price,
                    'signal': 1 if current_price > moving_avg else -1
                }
            else:
                self.log(f"No price data available for {ticker}")
                return None
            
        except Exception as e:
            self.log(f"Error calculating moving average for {ticker}: {str(e)}")
            return None

    # ---------------------------
    # Calculate moving averages for all tickers
    # ---------------------------
    def _calculate_signals(self, current_time: datetime):
        """
        Calculate 200-day moving average signals for all tickers.
        
        Simple binary signal generation based on price vs moving average.
        """
        self.log(f"Calculating 200-day moving average signals at {current_time.date()}")
        
        for ticker in self.universe:
            ma_data = self._calculate_moving_average_for_ticker(ticker, current_time)
            if ma_data:
                self.moving_averages[ticker] = ma_data['moving_average']
                self.last_prices[ticker] = ma_data['current_price']
                self.signals[ticker] = ma_data['signal']
                
                signal_text = "LONG" if ma_data['signal'] == 1 else "SHORT"
                self.log(f"{ticker} Signal: {signal_text} (Price: ${ma_data['current_price']:.2f}, MA: ${ma_data['moving_average']:.2f})")

        self.last_train_time = current_time
        self.log(f"Signals updated at {current_time.date()}")

    # ---------------------------
    # On each new data point (Enhanced with ML signals)
    # ---------------------------
    def on_data(self, data):
        """
        Process new data point with hybrid ML + traditional signals.
        
        Exactly matches MyAlgorithm structure but integrates ML signals.
        """
        # DEBUG: Log every on_data call to ensure it's being called
        self.log(f"🔔 on_data called at {self.time} - data type: {type(data)}")
        
        # Check if dependencies were properly injected
        if not self.factor_manager:
            self.log(f"⚠️ on_data called but dependencies not fully injected - factor_manager: {self.factor_manager is not None}")
        if not self.spatiotemporal_trainer:
            self.log(f"⚠️ on_data called but dependencies not fully injected - trainer: {self.spatiotemporal_trainer is not None}")
        if not self.momentum_strategy:
            self.log(f"⚠️ on_data called but dependencies not fully injected -  strategy: {self.momentum_strategy is not None}")
        
        # Comprehensive data type handling - accept both Slice and DataFrame objects
        if hasattr(data, 'columns') and hasattr(data, 'index'):
            # This is a DataFrame - convert it to a format we can work with
            self.log(f"INFO: on_data received DataFrame object, converting to internal format: {type(data)}")
            # Store the DataFrame for price lookup instead of expecting Slice format
            self._current_data_frame = data
            self._current_data_slice = None
        elif hasattr(data, 'bars'):
            # This is a proper Slice object
            self.log(f"INFO: on_data received Slice object with bars")
            self._current_data_frame = None
            self._current_data_slice = data
        else:
            # Unknown data type - log and skip
            self.log(f"ERROR: on_data received unknown data type: {type(data)}")
            return
            
        # Update signals daily
        if (
            self.last_train_time is None
            or self.time - self.last_train_time >= self.retrain_interval
        ):
            self._calculate_signals(self.time)

        if not self.signals:
            return

        # Step 1: Use simple 200-day moving average signals
        trading_signals = {}
        
        for ticker in self.universe:
            # Check if ticker exists in securities and has valid signal
            if ticker not in self.my_securities:
                self.log(f"Warning: {ticker} not found in my_securities dictionary")
                continue
            elif self.my_securities[ticker] is None:
                self.log(f"Warning: {ticker} security object is None")
                continue
            elif not self._has_price_data(ticker, self.my_securities[ticker].symbol):
                self.log(f"Warning: {ticker} price data not available in current data")
                continue
            elif ticker not in self.signals:
                self.log(f"Warning: {ticker} signal not available")
                continue

            # Use the calculated 200-day MA signal
            signal = self.signals[ticker]  # 1 = long, -1 = short
            trading_signals[ticker] = 1 if signal == 1 else 0  # Convert to 1/0 format for compatibility

        if not trading_signals:
            return

        # Step 2: Simple position sizing (equal weight or binary)
        # Convert signals into views: +3% for bullish, -3% for bearish (more conservative)
        views = {t: (0.03 if sig == 1 else -0.03) for t, sig in trading_signals.items()}
        
        self.log(f"Generated views for {len(views)} tickers: {views}")

        # Compute historical mean & covariance of returns
        hist = self.history(self.universe, self.train_window, Resolution.DAILY)
        
        # Handle both dictionary and DataFrame formats (matching MyAlgorithm exactly)
        if isinstance(hist, dict):
            # Convert dictionary to DataFrame
            df_list = []
            for symbol, data in hist.items():
                if isinstance(data, pd.DataFrame):
                    data['symbol'] = symbol
                    df_list.append(data)
            if df_list:
                hist_df = pd.concat(df_list)
                pivoted = hist_df.pivot(columns="symbol", values="close")
            else:
                # Fallback: create simple returns data
                returns_data = {}
                for symbol in self.universe:
                    # Use factor-based historical data if available, otherwise mock
                    if hasattr(self, 'factor_manager') and self.factor_manager:
                        factor_data = self._get_factor_historical_data(symbol)
                        if factor_data is not None:
                            returns_data[symbol] = factor_data
                        
                pivoted = pd.DataFrame(returns_data)
        else:
            # Assume it's already a DataFrame
            pivoted = hist.pivot(index="time", columns="symbol", values="close")
        
        returns = pivoted.pct_change().dropna()
        mu = returns.mean()
        cov = returns.cov()

        bl = BlackLittermanOptimizer(mu, cov)
        bl.add_views(views)
        try:
            weights = bl.solve()
            self.log(f"Black-Litterman optimization successful, weights: {weights}")
        except Exception as e:
            self.log(f"Black-Litterman optimization failed: {str(e)}")
            # Fall back to simple equal weighting
            num_signals = len([s for s in trading_signals.values() if s == 1])
            if num_signals > 0:
                equal_weight = 1.0 / len(self.universe)
                weights = {t: equal_weight if trading_signals.get(t, 0) == 1 else 0.0 for t in self.universe}
                self.log(f"Using equal weighting fallback: {weights}")
            else:
                self.log("No bullish signals, skipping trades")
                return

        # Step 3: Execute trades based on BL weights (matching MyAlgorithm exactly)
        # Use cash balance when portfolio holdings are empty (initial state)
        portfolio_holdings_value = float(self.portfolio.total_portfolio_value)
        cash_balance = float(self.portfolio.cash_balance)
        
        if portfolio_holdings_value == 0.0:
            # No holdings yet, use available cash for position sizing
            total_portfolio_value = cash_balance
            self.log(f"Using cash balance for position sizing: ${total_portfolio_value:.2f}")
        else:
            # Has holdings, use total portfolio value (holdings + cash)
            total_portfolio_value = portfolio_holdings_value + cash_balance
            self.log(f"Using total portfolio value: ${total_portfolio_value:.2f} (holdings: ${portfolio_holdings_value:.2f} + cash: ${cash_balance:.2f})")
        
        for ticker, w in weights.items():
            if ticker not in self.my_securities or self.my_securities[ticker] is None:
                self.log(f"Warning: Cannot execute trade for {ticker} - security not available")
                continue
            security = self.my_securities[ticker]
            target_value = w * total_portfolio_value
            
            # Get current holdings value - use portfolio.holdings for direct access
            current_value = self._get_current_holdings_value(ticker, security.symbol)
            if current_value == 0.0:
                self.log(f"No existing holding for {ticker}, starting from zero")
            
            diff_value = target_value - current_value
            # Get price data using the current data format
            price = self._get_current_price(ticker, security.symbol)
            if price is None:
                self.log(f"Warning: Cannot find price data for {ticker}")
                continue
            qty = int(diff_value / price)
            if qty != 0:
                self.log(f"Executing order for {ticker}: target=${target_value:.2f}, current=${current_value:.2f}, qty={qty}")
                self.set_holding(security.symbol, qty, price)
                self.market_order(security.symbol, qty)

    # ---------------------------
    # Helper methods (inherited from QCAlgorithm base class)
    # ---------------------------
    # Note: _has_price_data(), _get_current_price(), and _get_current_holdings_value() 
    # are inherited from QCAlgorithm base class with proper implementations

    def _get_factor_historical_data(self, ticker: str) -> Optional[np.ndarray]:
        """Get historical returns from factor system if available."""
        try:
            if hasattr(self, 'factor_manager') and self.factor_manager:
                # Get factor data for returns
                factor_data = self.factor_manager.get_factor_data_for_training(
                    tickers=[ticker],
                    factor_groups=['price'],
                    lookback_days=self.train_window
                )
                if factor_data is not None and not factor_data.empty and 'price' in factor_data.columns:
                    prices = factor_data['price'].values
                    returns = np.diff(prices) / prices[:-1]
                    return returns
            return None
        except Exception as e:
            self.log(f"Error getting factor historical data for {ticker}: {str(e)}")
            return None

    # Event handlers are inherited from QCAlgorithm base class
    
    def set_factor_manager(self, factor_manager):
        """Inject factor manager from the BacktestRunner."""
        self.factor_manager = factor_manager
        self.log("✅ Factor manager injected successfully")
        
    
    def set_spatiotemporal_trainer(self, trainer):
        """Inject spatiotemporal trainer from the BacktestRunner."""
        self.spatiotemporal_trainer = trainer
        self.log("✅ Spatiotemporal trainer injected successfully")
    
    def set_momentum_strategy(self, strategy):
        """Inject momentum strategy from the BacktestRunner."""
        self.momentum_strategy = strategy
        self.log("✅ Momentum strategy injected successfully")
    
