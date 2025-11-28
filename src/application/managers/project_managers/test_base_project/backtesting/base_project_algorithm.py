"""
BaseProjectAlgorithm - Main trading algorithm for test_base_project.

This algorithm matches the exact structure of MyAlgorithm from test_project_backtest
but integrates with the spatiotemporal momentum system, factor creation, and ML models.
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
    Hybrid trading algorithm combining:
    - Spatiotemporal momentum modeling (TFT/MLP ensemble)
    - Factor-based data system
    - Black-Litterman portfolio optimization
    - Traditional technical indicators
    
    This follows the exact structure of MyAlgorithm but integrates
    with the complete test_base_project ecosystem.
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
        self.lookback_window = 20   # volatility window
        self.train_window = 252     # ~1 year
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Model storage - both ML models and traditional models
        self.models = {}  # Traditional RandomForest models per ticker
        self.spatiotemporal_model = None  # Our TFT/MLP ensemble model
        self.ml_signal_generator = None
        
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
                    
                    if not factor_data.empty:
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
            
            # Price-based features
            if 'Close' in df.columns:
                df['close'] = df['Close']
                df["return"] = df["close"].pct_change()
                df["return_lag1"] = df["return"].shift(1)
                df["return_lag2"] = df["return"].shift(2)
                df["return_fwd1"] = df["return"].shift(-1)  # Target variable
                column_mapping['Close'] = 'close'
            
            # Volatility from factor system or calculate it
            if 'realized_vol' in df.columns:
                df['volatility'] = df['realized_vol']
                column_mapping['realized_vol'] = 'volatility'
            elif 'daily_vol' in df.columns:
                df['volatility'] = df['daily_vol']
                column_mapping['daily_vol'] = 'volatility'
            elif 'close' in df.columns:
                # Calculate volatility if not available in factor system
                df["volatility"] = df["return"].rolling(self.lookback_window).std()
            
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
    # Train one model (Enhanced with ML integration)
    # ---------------------------
    def _train_model_for_ticker(self, ticker: str, current_time: datetime):
        """
        Train model for a specific ticker.
        
        Matches MyAlgorithm pattern but integrates with spatiotemporal training.
        """
        try:
            history = self.history(
                [ticker],
                self.train_window,
                Resolution.DAILY,
                end_time=current_time
            )

            df = self._setup_factor_data_for_ticker(ticker, current_time)
            if df.empty:
                return None

            # Traditional model training (matching MyAlgorithm)
            X = df[["return_lag1", "return_lag2", "volatility"]]
            y = (df["return_fwd1"] > 0).astype(int)

            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42
            )
            model.fit(X, y)
            
            return model
            
        except Exception as e:
            self.log(f"Error training model for {ticker}: {str(e)}")
            return None

    # ---------------------------
    # Train all models (Enhanced with spatiotemporal training)
    # ---------------------------
    def _train_models(self, current_time: datetime):
        """
        Train all models including traditional and spatiotemporal models.
        
        Matches MyAlgorithm structure but adds our ML ensemble.
        """
        # Train traditional models per ticker (matching MyAlgorithm)
        for ticker in self.universe:
            model = self._train_model_for_ticker(ticker, current_time)
            if model:
                self.models[ticker] = model

        # Train spatiotemporal ensemble model
        try:
            if hasattr(self, 'spatiotemporal_trainer') and self.spatiotemporal_trainer:
                self.log("Training spatiotemporal ensemble model...")
                
                # Train the TFT/MLP ensemble
                training_results = self.spatiotemporal_trainer.train_complete_pipeline(
                    tickers=self.universe,
                    model_type='both',  # Train both TFT and MLP
                    seeds=[42, 123]  # Ensemble with multiple seeds
                )
                
                if training_results and not training_results.get('error'):
                    self.spatiotemporal_model = self.spatiotemporal_trainer.get_trained_model()
                    self.log("Spatiotemporal model training completed successfully")
                else:
                    self.log(f"Spatiotemporal model training failed: {training_results.get('error', 'Unknown error')}")
        except Exception as e:
            self.log(f"Error training spatiotemporal models: {str(e)}")

        self.last_train_time = current_time
        self.log(f"Models retrained at {current_time.date()}")

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
            
        # Retrain weekly
        if (
            self.last_train_time is None
            or self.time - self.last_train_time >= self.retrain_interval
        ):
            self._train_models(self.time)

        if not self.models:
            return

        # Step 1: Collect signals (Enhanced with ML)
        signals = {}
        ml_signals = {}
        
        for ticker, model in self.models.items():
            # Check if ticker exists in securities and the security object is not None
            if ticker not in self.my_securities:
                self.log(f"Warning: {ticker} not found in my_securities dictionary")
                continue
            elif self.my_securities[ticker] is None:
                self.log(f"Warning: {ticker} security object is None")
                continue
            elif not self._has_price_data(ticker, self.my_securities[ticker].symbol):
                self.log(f"Warning: {ticker} price data not available in current data")
                continue

            # Get traditional signals using factor system
            df = self._setup_factor_data_for_ticker(ticker, self.time)
            if df.empty:
                continue

            # Traditional RandomForest signal (matching MyAlgorithm)
            X_live = df[["return_lag1", "return_lag2", "volatility"]].iloc[-1:]
            pred = model.predict(X_live)[0]  # 1 = long, 0 = short
            signals[ticker] = pred

            # Enhanced ML signals from spatiotemporal model
            try:
                if self.spatiotemporal_model and hasattr(self, 'momentum_strategy') and self.momentum_strategy:
                    # Get ML signal from our ensemble model
                    ml_signal = self.momentum_strategy.generate_strategy_signals(
                        df, df, self.time
                    ).get(ticker, 0.0)
                    ml_signals[ticker] = ml_signal
                    
                    # Combine traditional and ML signals (weighted average)
                    combined_signal = 0.6 * pred + 0.4 * (1 if ml_signal > 0 else 0)
                    signals[ticker] = int(combined_signal > 0.5)
                    
            except Exception as e:
                self.log(f"Error getting ML signal for {ticker}: {str(e)}")
                # Fall back to traditional signal only
                pass

        if not signals:
            return

        # Step 2: Build Black-Litterman optimizer (matching MyAlgorithm exactly)
        # Convert signals into views: +5% for bullish, -5% for bearish
        views = {t: (0.05 if sig == 1 else -0.05) for t, sig in signals.items()}
        
        # Enhance views with ML confidence if available
        if ml_signals:
            for ticker, ml_signal in ml_signals.items():
                if ticker in views:
                    # Adjust view strength based on ML signal confidence
                    ml_confidence = abs(ml_signal)
                    if ml_confidence > 0.1:  # High confidence
                        views[ticker] *= (1 + ml_confidence)

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
        weights = bl.solve()

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
                if not factor_data.empty and 'price' in factor_data.columns:
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
    
