"""
BaseProjectAlgorithm: Hybrid trading algorithm combining spatiotemporal ML models,
factor-based momentum strategies, and Black-Litterman portfolio optimization.

This algorithm integrates:
1. TFT/MLP ensemble models for price prediction
2. Factor-based momentum and technical indicators
3. Black-Litterman portfolio optimization
4. Risk management and performance tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

# Import Misbuffet framework components
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution,
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm
from application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer

# Import project-specific components
from ..data.factor_manager import FactorManager
from ..models.spatiotemporal_model import SpatiotemporalModel
from ..models.model_trainer import ModelTrainer
from ..strategy.momentum_strategy import MomentumStrategy
from ..strategy.signal_generator import MLSignalGenerator
from ..strategy.portfolio_optimizer import PortfolioOptimizer
from ..utils.performance_metrics import PerformanceMetrics

# Configure logging
logger = logging.getLogger(__name__)


class BaseProjectAlgorithm(QCAlgorithm):
    """
    Hybrid algorithm combining spatiotemporal ML models with factor-based strategies.
    """
    
    def initialize(self):
        """Initialize the hybrid algorithm with all required components."""
        # Call parent initialization
        super().initialize()
        
        # Algorithm configuration
        self.universe = ["AAPL", "MSFT", "AMZN", "GOOGL"]
        self.my_securities = {}
        
        # Initialize core components
        self._initialize_factor_system()
        self._initialize_ml_models()
        self._initialize_strategy_components()
        self._initialize_risk_management()
        
        # Trading configuration
        self.rebalance_frequency = timedelta(days=7)  # Weekly rebalancing
        self.last_rebalance_time = None
        self.retrain_frequency = timedelta(days=7)   # Weekly retraining
        self.last_retrain_time = None
        
        # Data tracking
        self._current_data = None
        self._factor_data_cache = {}
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        self.trade_log = []
        
        # Add securities to universe
        self._add_universe_securities()
        
        # Initial setup
        self._initial_factor_population()
        self._initial_model_training()
        
        self.log("BaseProject Algorithm initialized successfully")

    def _initialize_factor_system(self):
        """Initialize the factor management system."""
        try:
            self.factor_manager = FactorManager()
            self.log("Factor system initialized")
        except Exception as e:
            self.log(f"Error initializing factor system: {e}")
            self.factor_manager = None

    def _initialize_ml_models(self):
        """Initialize ML models and training components."""
        try:
            self.spatiotemporal_model = SpatiotemporalModel()
            self.model_trainer = ModelTrainer()
            self.ml_signal_generator = MLSignalGenerator()
            self.trained_models = {}  # Store trained models by ticker
            self.log("ML models initialized")
        except Exception as e:
            self.log(f"Error initializing ML models: {e}")
            self.spatiotemporal_model = None
            self.model_trainer = None
            self.ml_signal_generator = None

    def _initialize_strategy_components(self):
        """Initialize strategy and portfolio optimization components."""
        try:
            self.momentum_strategy = MomentumStrategy()
            self.portfolio_optimizer = PortfolioOptimizer()
            self.log("Strategy components initialized")
        except Exception as e:
            self.log(f"Error initializing strategy components: {e}")
            self.momentum_strategy = None
            self.portfolio_optimizer = None

    def _initialize_risk_management(self):
        """Initialize risk management parameters."""
        self.max_position_size = 0.25  # 25% max per position
        self.max_portfolio_leverage = 1.5
        self.volatility_scaling = True
        self.drawdown_limit = 0.15
        
        # Risk tracking
        self.position_sizes = {}
        self.portfolio_volatility = 0.0
        self.current_drawdown = 0.0
        
        self.log("Risk management initialized")

    def _add_universe_securities(self):
        """Add securities to the trading universe."""
        for ticker in self.universe:
            try:
                security = self.add_equity(ticker, Resolution.DAILY)
                if security is not None:
                    self.my_securities[ticker] = security
                    self.log(f"Added security: {ticker}")
                else:
                    self.log(f"Warning: Failed to add security {ticker}")
            except Exception as e:
                self.log(f"Error adding security {ticker}: {e}")

    def _initial_factor_population(self):
        """Populate initial factor data for all securities."""
        if self.factor_manager is None:
            return
            
        try:
            self.log("Starting initial factor population...")
            result = self.factor_manager.populate_momentum_factors(
                tickers=self.universe,
                overwrite=False
            )
            self.log(f"Factor population result: {result}")
        except Exception as e:
            self.log(f"Error in initial factor population: {e}")

    def _initial_model_training(self):
        """Perform initial training of ML models."""
        if self.model_trainer is None:
            return
            
        try:
            self.log("Starting initial model training...")
            
            # Get factor data for training
            training_data = self._prepare_training_data()
            
            if training_data is not None and not training_data.empty:
                # Train models for each ticker
                for ticker in self.universe:
                    ticker_data = training_data[training_data['ticker'] == ticker]
                    if not ticker_data.empty:
                        model = self.model_trainer.train_model(
                            data=ticker_data,
                            model_type='both',  # Train both TFT and MLP
                            ticker=ticker
                        )
                        if model is not None:
                            self.trained_models[ticker] = model
                            self.log(f"Model trained for {ticker}")
                
                self.last_retrain_time = self.time
                self.log(f"Initial training completed for {len(self.trained_models)} securities")
            else:
                self.log("No training data available")
                
        except Exception as e:
            self.log(f"Error in initial model training: {e}")

    def _prepare_training_data(self) -> Optional[pd.DataFrame]:
        """Prepare training data from factor system."""
        if self.factor_manager is None:
            return None
            
        try:
            # Get factor data for training
            training_data = self.factor_manager.get_factor_data_for_training(
                tickers=self.universe,
                start_date="2020-01-01",
                end_date=self.time.strftime("%Y-%m-%d"),
                factor_groups=['price', 'momentum', 'technical']
            )
            return training_data
        except Exception as e:
            self.log(f"Error preparing training data: {e}")
            return None

    def on_data(self, data):
        """Main trading logic executed on each data update."""
        try:
            # Store current data
            self._current_data = data
            
            # Check if it's time to retrain models
            if self._should_retrain():
                self._retrain_models()
            
            # Check if it's time to rebalance portfolio
            if self._should_rebalance():
                self._rebalance_portfolio()
                
        except Exception as e:
            self.log(f"Error in on_data: {e}")

    def _should_retrain(self) -> bool:
        """Check if models should be retrained."""
        if self.last_retrain_time is None:
            return True
        return self.time - self.last_retrain_time >= self.retrain_frequency

    def _should_rebalance(self) -> bool:
        """Check if portfolio should be rebalanced."""
        if self.last_rebalance_time is None:
            return True
        return self.time - self.last_rebalance_time >= self.rebalance_frequency

    def _retrain_models(self):
        """Retrain ML models with latest data."""
        try:
            self.log("Retraining models...")
            
            # Prepare fresh training data
            training_data = self._prepare_training_data()
            
            if training_data is not None and not training_data.empty:
                # Retrain models for each ticker
                for ticker in self.universe:
                    ticker_data = training_data[training_data['ticker'] == ticker]
                    if not ticker_data.empty:
                        model = self.model_trainer.train_model(
                            data=ticker_data,
                            model_type='both',
                            ticker=ticker
                        )
                        if model is not None:
                            self.trained_models[ticker] = model
                
                self.last_retrain_time = self.time
                self.log("Models retrained successfully")
            
        except Exception as e:
            self.log(f"Error retraining models: {e}")

    def _rebalance_portfolio(self):
        """Execute portfolio rebalancing based on signals."""
        try:
            self.log("Executing portfolio rebalancing...")
            
            # Generate signals from different sources
            signals = self._generate_combined_signals()
            
            if not signals:
                self.log("No signals generated, skipping rebalancing")
                return
            
            # Optimize portfolio weights
            weights = self._optimize_portfolio_weights(signals)
            
            if weights:
                # Execute trades based on optimized weights
                self._execute_rebalancing_trades(weights)
                self.last_rebalance_time = self.time
                self.log("Portfolio rebalanced successfully")
            
        except Exception as e:
            self.log(f"Error rebalancing portfolio: {e}")

    def _generate_combined_signals(self) -> Dict[str, float]:
        """Generate combined signals from ML models and momentum strategy."""
        signals = {}
        
        try:
            # Generate ML-based signals
            ml_signals = self._generate_ml_signals()
            
            # Generate momentum-based signals
            momentum_signals = self._generate_momentum_signals()
            
            # Combine signals with weights
            ml_weight = 0.6
            momentum_weight = 0.4
            
            for ticker in self.universe:
                ml_signal = ml_signals.get(ticker, 0.0)
                momentum_signal = momentum_signals.get(ticker, 0.0)
                
                combined_signal = (ml_weight * ml_signal + 
                                 momentum_weight * momentum_signal)
                signals[ticker] = combined_signal
            
            self.log(f"Generated signals: {signals}")
            
        except Exception as e:
            self.log(f"Error generating combined signals: {e}")
            
        return signals

    def _generate_ml_signals(self) -> Dict[str, float]:
        """Generate signals using trained ML models."""
        ml_signals = {}
        
        if self.ml_signal_generator is None:
            return ml_signals
            
        try:
            for ticker in self.universe:
                if ticker in self.trained_models:
                    # Get recent data for prediction
                    recent_data = self._get_recent_factor_data(ticker)
                    
                    if recent_data is not None:
                        signal = self.ml_signal_generator.generate_signal(
                            model=self.trained_models[ticker],
                            data=recent_data,
                            ticker=ticker
                        )
                        ml_signals[ticker] = signal
                        
        except Exception as e:
            self.log(f"Error generating ML signals: {e}")
            
        return ml_signals

    def _generate_momentum_signals(self) -> Dict[str, float]:
        """Generate signals using momentum strategy."""
        momentum_signals = {}
        
        if self.momentum_strategy is None:
            return momentum_signals
            
        try:
            for ticker in self.universe:
                # Get historical price data
                history = self.history([ticker], 60, Resolution.DAILY)
                
                if not history.empty:
                    signal = self.momentum_strategy.generate_signal(history, ticker)
                    momentum_signals[ticker] = signal
                    
        except Exception as e:
            self.log(f"Error generating momentum signals: {e}")
            
        return momentum_signals

    def _get_recent_factor_data(self, ticker: str, lookback: int = 60) -> Optional[pd.DataFrame]:
        """Get recent factor data for a specific ticker."""
        if self.factor_manager is None:
            return None
            
        try:
            end_date = self.time.strftime("%Y-%m-%d")
            start_date = (self.time - timedelta(days=lookback)).strftime("%Y-%m-%d")
            
            factor_data = self.factor_manager.get_factor_data_for_training(
                tickers=[ticker],
                start_date=start_date,
                end_date=end_date,
                factor_groups=['price', 'momentum', 'technical']
            )
            
            return factor_data
            
        except Exception as e:
            self.log(f"Error getting recent factor data for {ticker}: {e}")
            return None

    def _optimize_portfolio_weights(self, signals: Dict[str, float]) -> Dict[str, float]:
        """Optimize portfolio weights using Black-Litterman or other methods."""
        if self.portfolio_optimizer is None:
            # Simple proportional allocation fallback
            total_signal = sum(abs(s) for s in signals.values())
            if total_signal == 0:
                return {}
            
            return {ticker: signal/total_signal for ticker, signal in signals.items()}
        
        try:
            weights = self.portfolio_optimizer.optimize_weights(
                signals=signals,
                universe=self.universe,
                risk_model=self._get_risk_model()
            )
            return weights
            
        except Exception as e:
            self.log(f"Error optimizing portfolio weights: {e}")
            return {}

    def _get_risk_model(self) -> Dict[str, Any]:
        """Get risk model parameters for portfolio optimization."""
        try:
            # Get historical returns for covariance estimation
            history = self.history(self.universe, 252, Resolution.DAILY)
            
            if isinstance(history, dict):
                # Convert to returns matrix
                returns_data = {}
                for symbol, data in history.items():
                    if isinstance(data, pd.DataFrame) and 'close' in data.columns:
                        returns_data[symbol] = data['close'].pct_change().dropna()
                
                returns_df = pd.DataFrame(returns_data)
                
                return {
                    'mean_returns': returns_df.mean(),
                    'covariance_matrix': returns_df.cov(),
                    'risk_free_rate': 0.02
                }
            
        except Exception as e:
            self.log(f"Error building risk model: {e}")
            
        # Return default risk model
        return {
            'mean_returns': pd.Series([0.001] * len(self.universe), index=self.universe),
            'covariance_matrix': pd.DataFrame(np.eye(len(self.universe)) * 0.0004, 
                                            index=self.universe, columns=self.universe),
            'risk_free_rate': 0.02
        }

    def _execute_rebalancing_trades(self, weights: Dict[str, float]):
        """Execute trades to rebalance portfolio according to target weights."""
        try:
            total_portfolio_value = float(self.portfolio.total_portfolio_value)
            cash_balance = float(self.portfolio.cash_balance)
            
            # Use total value for position sizing
            portfolio_value = max(total_portfolio_value, cash_balance)
            
            self.log(f"Executing rebalancing with portfolio value: ${portfolio_value:.2f}")
            
            for ticker, weight in weights.items():
                if ticker not in self.my_securities or self.my_securities[ticker] is None:
                    continue
                    
                security = self.my_securities[ticker]
                target_value = weight * portfolio_value
                
                # Apply position size limits
                max_position_value = self.max_position_size * portfolio_value
                target_value = max(-max_position_value, min(max_position_value, target_value))
                
                # Get current position value
                current_value = self._get_current_holdings_value(ticker, security.symbol)
                
                # Calculate trade size
                diff_value = target_value - current_value
                price = self._get_current_price(ticker, security.symbol)
                
                if price is not None and abs(diff_value) > 100:  # Minimum trade size
                    qty = int(diff_value / price)
                    
                    if qty != 0:
                        self.log(f"Trading {ticker}: target=${target_value:.2f}, "
                               f"current=${current_value:.2f}, qty={qty}")
                        
                        # Execute the trade
                        self.market_order(security.symbol, qty)
                        
                        # Log trade
                        self.trade_log.append({
                            'timestamp': self.time,
                            'ticker': ticker,
                            'quantity': qty,
                            'price': price,
                            'value': qty * price,
                            'signal_weight': weight
                        })
                        
        except Exception as e:
            self.log(f"Error executing rebalancing trades: {e}")

    def _get_current_holdings_value(self, ticker: str, symbol) -> float:
        """Get current holdings value for a ticker."""
        try:
            if hasattr(self.portfolio, 'holdings') and symbol in self.portfolio.holdings:
                holding = self.portfolio.holdings[symbol]
                return float(getattr(holding, 'market_value', 0.0))
            return 0.0
        except Exception:
            return 0.0

    def _get_current_price(self, ticker: str, symbol) -> Optional[float]:
        """Get current price for a ticker."""
        try:
            # Try to get price from current data
            if self._current_data is not None:
                if hasattr(self._current_data, 'bars') and symbol in self._current_data.bars:
                    return float(self._current_data.bars[symbol].close)
                elif hasattr(self._current_data, 'columns') and ticker in self._current_data.columns:
                    return float(self._current_data[ticker].iloc[-1])
            
            # Fallback to securities data
            if symbol in self.securities and hasattr(self.securities[symbol], 'price'):
                return float(self.securities[symbol].price)
                
            return None
        except Exception:
            return None

    def _has_price_data(self, ticker: str, symbol) -> bool:
        """Check if price data is available for a ticker."""
        try:
            price = self._get_current_price(ticker, symbol)
            return price is not None and price > 0
        except Exception:
            return False

    def on_order_event(self, order_event):
        """Handle order events for tracking and logging."""
        try:
            self.log(f"Order event: {order_event.symbol} - {order_event.status}")
        except Exception as e:
            self.log(f"Error handling order event: {e}")

    def on_end_of_day(self):
        """End of day processing and performance tracking."""
        try:
            # Update performance metrics
            portfolio_value = float(self.portfolio.total_portfolio_value)
            self.performance_metrics.update_daily_performance(
                date=self.time.date(),
                portfolio_value=portfolio_value
            )
            
            # Log daily performance
            daily_return = self.performance_metrics.get_daily_return()
            if daily_return is not None:
                self.log(f"Daily return: {daily_return:.4f}, "
                        f"Portfolio value: ${portfolio_value:.2f}")
                        
        except Exception as e:
            self.log(f"Error in end of day processing: {e}")

    def on_algorithm_termination(self):
        """Final processing when algorithm terminates."""
        try:
            # Generate final performance report
            final_performance = self.performance_metrics.get_performance_summary()
            self.log(f"Final performance summary: {final_performance}")
            
            # Log trade summary
            total_trades = len(self.trade_log)
            self.log(f"Total trades executed: {total_trades}")
            
        except Exception as e:
            self.log(f"Error in algorithm termination: {e}")