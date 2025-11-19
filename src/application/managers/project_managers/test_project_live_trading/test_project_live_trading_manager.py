import time
import logging
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from application.services.database_service import DatabaseService
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_live_trading import config
from application.services.misbuffet.algorithm.order import OrderEvent
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import  Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

# Import the misbuffet framework components for live trading
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution, 
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm

# Import domain entities following DDD structure
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import  Dividend
from domain.entities.finance.financial_assets.security import MarketData, Symbol

# Import misbuffet components
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from application.services.misbuffet.common.enums import Resolution
from application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer

# Import config files
from .launch_config import MISBUFFET_LAUNCH_CONFIG
from .engine_config import MISBUFFET_ENGINE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveTradingAlgorithm(QCAlgorithm):
    """
    Live Trading Algorithm using ML signals and Black-Litterman optimization.
    
    This algorithm is adapted for live trading with Interactive Brokers,
    featuring real-time data processing, risk management, and position monitoring.
    """
    
    def initialize(self):
        # Define universe - same as backtest but with live data
        self.universe = ["AAPL", "MSFT", "AMZN", "GOOGL"]
        for ticker in self.universe:
            # Subscribe to live market data
            self.add_equity(ticker, Resolution.MINUTE)  # Higher resolution for live trading
        
        # ML and optimization parameters
        self.lookback_window = 20
        self.train_window = 252
        self.retrain_interval = timedelta(hours=1)  # Retrain every hour in live mode
        self.last_train_time = None
        
        # Model storage
        self.models = {}
        
        # Live trading specific settings
        self.trading_hours_start = "09:30"
        self.trading_hours_end = "16:00"
        
        # Risk management
        self.max_position_size = 0.20  # 20% max per position
        self.daily_loss_limit = 5000   # USD
        self.position_check_interval = timedelta(minutes=5)
        self.last_position_check = None
        
        # Performance tracking
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.start_of_day_value = float(self.portfolio.total_portfolio_value)
        
        # Schedule periodic tasks
        self.schedule.schedule(
            self.on_market_open, 
            name="market_open",
            date_rule=self.date_rules.every_day(),
            time_rule=self.time_rules.at(9, 29)
        )
        
        self.schedule.schedule(
            self.on_market_close,
            name="market_close", 
            date_rule=self.date_rules.every_day(),
            time_rule=self.time_rules.at(16, 1)
        )
        
        # Initial model training
        self.log("Initializing Live Trading Algorithm...")
        self._train_models(self.time)
    
    def on_market_open(self):
        """Called at market open to reset daily tracking."""
        self.log("Market opened - resetting daily tracking")
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.start_of_day_value = float(self.portfolio.total_portfolio_value)
        
        # Force retrain models at market open
        self._train_models(self.time)
    
    def on_market_close(self):
        """Called at market close to log daily performance."""
        current_value = self.portfolio.total_portfolio_value
        self.daily_pnl = float(current_value - self.start_of_day_value)
        
        self.log(f"Market closed - Daily P&L: ${self.daily_pnl:.2f}, Trades: {self.trades_today}")
        
        # Log performance metrics
        self.runtime_statistic("Daily P&L", f"${self.daily_pnl:.2f}")
        self.runtime_statistic("Trades Today", str(self.trades_today))
        self.runtime_statistic("Portfolio Value", f"${current_value:.2f}")
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within trading hours."""
        current_time = self.time.time()
        market_open = datetime.strptime(self.trading_hours_start, "%H:%M").time()
        market_close = datetime.strptime(self.trading_hours_end, "%H:%M").time()
        
        return market_open <= current_time <= market_close
    
    def _prepare_features(self, history: pd.DataFrame) -> pd.DataFrame:
        """Prepare ML features from historical data."""
        df = history.copy()
        df["return"] = df["close"].pct_change()
        df["return_lag1"] = df["return"].shift(1)
        df["return_lag2"] = df["return"].shift(2)
        df["volatility"] = df["return"].rolling(self.lookback_window).std()
        df["volume_ma"] = df["volume"].rolling(self.lookback_window).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"]
        df["return_fwd1"] = df["return"].shift(-1)
        return df.dropna()
    
    def _train_model_for_ticker(self, ticker: str, current_time: datetime):
        """Train ML model for a specific ticker."""
        try:
            # Get more recent history for live trading
            history = self.history(
                [ticker],
                self.train_window,
                Resolution.DAILY,  # Use daily data for training
                end_time=current_time
            )
            
            df = self._prepare_features(history)
            if df.empty or len(df) < 50:  # Minimum data requirement
                return None
            
            # Enhanced features for live trading
            X = df[["return_lag1", "return_lag2", "volatility", "volume_ratio"]]
            y = (df["return_fwd1"] > 0).astype(int)
            
            # Use a more sophisticated model for live trading
            model = RandomForestClassifier(
                n_estimators=200,  # More trees for better accuracy
                max_depth=10,
                random_state=42,
                min_samples_split=5,
                min_samples_leaf=2
            )
            
            model.fit(X, y)
            
            # Calculate model confidence/accuracy on recent data
            recent_data = df.tail(50)
            if len(recent_data) > 10:
                X_recent = recent_data[["return_lag1", "return_lag2", "volatility", "volume_ratio"]]
                y_recent = (recent_data["return_fwd1"] > 0).astype(int)
                accuracy = model.score(X_recent, y_recent)
                self.log(f"Model accuracy for {ticker}: {accuracy:.3f}")
            
            return model
            
        except Exception as e:
            self.log(f"Error training model for {ticker}: {str(e)}")
            return None
    
    def _train_models(self, current_time: datetime):
        """Train models for all tickers."""
        self.log("Starting model retraining...")
        trained_count = 0
        
        for ticker in self.universe:
            model = self._train_model_for_ticker(ticker, current_time)
            if model:
                self.models[ticker] = model
                trained_count += 1
        
        self.last_train_time = current_time
        self.log(f"Model retraining completed: {trained_count}/{len(self.universe)} models updated")
    
    def _check_risk_limits(self) -> bool:
        """Check if risk limits are breached."""
        # Check daily loss limit
        current_pnl = float(self.portfolio.total_portfolio_value) - self.start_of_day_value
        if current_pnl < -self.daily_loss_limit:
            self.log(f"Daily loss limit breached: ${current_pnl:.2f}")
            return False
        
        # Check position sizes
        total_value = float(self.portfolio.total_portfolio_value)
        for symbol, holding in self.portfolio.items():
            if abs(holding.holdings_value / total_value) > self.max_position_size:
                self.log(f"Position size limit exceeded for {symbol}")
                return False
        
        return True
    
    def on_data(self, data):
        """Main trading logic called on each data point."""
        # Only trade during market hours
        if not self._is_market_hours():
            return
        
        # Check risk limits
        if not self._check_risk_limits():
            self.log("Risk limits breached - halting trading")
            return
        
        # Periodic position checks
        if (self.last_position_check is None or 
            self.time - self.last_position_check >= self.position_check_interval):
            self._log_portfolio_status()
            self.last_position_check = self.time
        
        # Retrain models periodically
        if (self.last_train_time is None or 
            self.time - self.last_train_time >= self.retrain_interval):
            self._train_models(self.time)
        
        if not self.models:
            return
        
        # Generate trading signals
        signals = {}
        for ticker, model in self.models.items():
            if ticker not in data:
                continue
            
            try:
                # Get recent history for feature calculation
                history = self.history([ticker], self.lookback_window + 5, Resolution.MINUTE)
                df = self._prepare_features(history)
                if df.empty:
                    continue
                
                # Generate prediction
                X_live = df[["return_lag1", "return_lag2", "volatility", "volume_ratio"]].iloc[-1:]
                pred_proba = model.predict_proba(X_live)[0]
                confidence = max(pred_proba)
                prediction = 1 if pred_proba[1] > pred_proba[0] else 0
                
                # Only trade if confidence is high enough
                if confidence > 0.6:  # Minimum confidence threshold
                    signals[ticker] = prediction
                    
            except Exception as e:
                self.log(f"Error generating signal for {ticker}: {str(e)}")
                continue
        
        if not signals:
            return
        
        # Convert signals to Black-Litterman views
        views = {}
        for ticker, signal in signals.items():
            view_strength = 0.03 if signal == 1 else -0.03  # 3% expected return
            views[ticker] = view_strength
        
        # Portfolio optimization with Black-Litterman
        try:
            hist = self.history(self.universe, 60, Resolution.DAILY)  # 2 months of data
            
            # Process historical data for optimization
            if isinstance(hist, dict):
                df_list = []
                for symbol, data in hist.items():
                    if isinstance(data, pd.DataFrame):
                        data['symbol'] = symbol
                        df_list.append(data)
                if df_list:
                    hist_df = pd.concat(df_list, ignore_index=True)
                    pivoted = hist_df.pivot(index="time", columns="symbol", values="close")
                else:
                    # Fallback for optimization
                    return
            else:
                pivoted = hist.pivot(index="time", columns="symbol", values="close")
            
            returns = pivoted.pct_change().dropna()
            mu = returns.mean()
            cov = returns.cov()
            
            # Black-Litterman optimization
            bl = BlackLittermanOptimizer(mu, cov)
            bl.add_views(views)
            weights = bl.solve()
            
            # Execute trades based on optimized weights
            self._execute_portfolio_trades(weights, data)
            
        except Exception as e:
            self.log(f"Error in portfolio optimization: {str(e)}")
    
    def _execute_portfolio_trades(self, weights: Dict[str, float], data):
        """Execute trades to achieve target portfolio weights."""
        total_value = float(self.portfolio.total_portfolio_value)
        
        for ticker, target_weight in weights.items():
            if ticker not in data:
                continue
            
            try:
                current_holding = self.portfolio[ticker]
                current_value = current_holding.holdings_value
                target_value = target_weight * total_value
                
                # Calculate required trade
                difference = target_value - current_value
                price = data[ticker].close
                required_shares = int(difference / price)
                
                # Apply minimum trade size filter
                min_trade_value = 100  # Minimum $100 trade
                if abs(required_shares * price) < min_trade_value:
                    continue
                
                # Execute trade
                if required_shares != 0:
                    ticket = self.market_order(ticker, required_shares)
                    self.trades_today += 1
                    self.log(f"Trade executed: {ticker} {required_shares} shares @ ${price:.2f}")
                    
            except Exception as e:
                self.log(f"Error executing trade for {ticker}: {str(e)}")
    
    def _log_portfolio_status(self):
        """Log current portfolio status."""
        total_value = float(self.portfolio.total_portfolio_value)
        self.log(f"Portfolio value: ${total_value:.2f}")
        
        for symbol, holding in self.portfolio.items():
            if holding.quantity != 0:
                weight = holding.holdings_value / total_value
                self.log(f"{symbol}: {holding.quantity} shares, ${holding.holdings_value:.2f} ({weight:.1%})")
    
    def on_order_event(self, order_event: OrderEvent) -> None:
        """Handle order events with enhanced logging."""
        status_msg = f"Order {order_event.order_id}: {order_event.symbol} - {order_event.status}"
        if order_event.status == "Filled":
            status_msg += f" - {order_event.quantity} @ ${order_event.fill_price:.2f}"
        self.log(status_msg)
        
        # Update daily P&L tracking
        if order_event.status == "Filled":
            current_value = float(self.portfolio.total_portfolio_value)
            self.daily_pnl = current_value - self.start_of_day_value
    
    def on_end_of_day(self, symbol: Symbol) -> None:
        """Called at end of trading day."""
        pass  # Handled by scheduled market close event
    
    def on_end_of_algorithm(self) -> None:
        """Called when algorithm finishes."""
        self.log("Live trading algorithm stopped")
        final_value = self.portfolio.total_portfolio_value
        self.log(f"Final portfolio value: ${final_value:.2f}")


class TestProjectLiveTradingManager(ProjectManager):
    """
    Project Manager for live trading operations with Interactive Brokers.
    
    This manager orchestrates live trading execution, monitoring, and risk management
    while maintaining integration with the existing DDD architecture.
    """
    
    def __init__(self):
        super().__init__()
        # Initialize database manager
        self.setup_database_manager(DatabaseService(config.CONFIG_LIVE_TRADING['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_service.session)
        
        # Live trading components
        self.algorithm = None
        self.trading_thread = None
        self.is_running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Risk management
        self.emergency_stop = False
        self.max_daily_loss = config.CONFIG_LIVE_TRADING.get('MAX_DAILY_LOSS', 5000)
    
    def run(self):
        """Main entry point for live trading execution."""
        self.logger.info("Starting Live Trading Manager...")
        
        try:
            # Pre-flight checks
            if not self._pre_flight_checks():
                self.logger.error("Pre-flight checks failed")
                return False
            
            # Initialize data
            self._setup_trading_data()
            
            # Configure and launch live trading
            result = self._launch_live_trading()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in live trading execution: {e}")
            return False
    
    def _pre_flight_checks(self) -> bool:
        """Perform pre-flight safety checks."""
        self.logger.info("Performing pre-flight checks...")
        
        # Check database connectivity
        try:
            self.database_service.db.initialize_database_and_create_all_tables()
            self.logger.info("✅ Database connectivity verified")
        except Exception as e:
            self.logger.error(f"❌ Database check failed: {e}")
            return False
        
        # Check configuration
        required_configs = ['IB_HOST', 'IB_PORT', 'IB_CLIENT_ID']
        for key in required_configs:
            if key not in config.CONFIG_LIVE_TRADING:
                self.logger.error(f"❌ Missing required configuration: {key}")
                return False
        
        self.logger.info("✅ Configuration validated")
        
        # Verify trading hours (if market is open)
        if self._is_market_hours():
            self.logger.info("✅ Market is currently open")
        else:
            self.logger.warning("⚠️ Market is currently closed - algorithm will wait for market open")
        
        self.logger.info("✅ Pre-flight checks completed successfully")
        return True
    
    def _is_market_hours(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now()
        # Simple check for weekdays between 9:30 AM and 4:00 PM ET
        if now.weekday() >= 5:  # Weekend
            return False
        
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def _setup_trading_data(self):
        """Setup required data for trading."""
        self.logger.info("Setting up trading data...")
        
        # Create company entities if they don't exist
        self.create_trading_universe()
        
        self.logger.info("✅ Trading data setup completed")
    
    def _launch_live_trading(self):
        """Launch the live trading system."""
        self.logger.info("Launching live trading system...")
        
        try:
            # Initialize Misbuffet for live trading
            misbuffet = Misbuffet.launch(config_file="launch_config.py")
            
            # Configure for live trading
            config_obj = LauncherConfiguration(
                mode=LauncherMode.LIVE_TRADING,  # Key difference from backtest
                algorithm_type_name="LiveTradingAlgorithm",
                algorithm_location=__file__,
                data_folder=MISBUFFET_ENGINE_CONFIG.get("data_folder", "./live_data"),
                environment="live_trading",
                live_mode=True,  # Enable live mode
                debugging=True
            )
            
            # Override with engine config
            config_obj.custom_config = MISBUFFET_ENGINE_CONFIG
            config_obj.algorithm = LiveTradingAlgorithm
            config_obj.database_manager = self.database_service
            
            self.logger.info("✅ Configuration setup for live trading")
            
            # Start engine
            self.logger.info("Starting live trading engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")
            
            # Run live trading
            self.is_running = True
            result = engine.run(config_obj)
            
            self.logger.info("Live trading session completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in live trading launch: {e}")
            self.emergency_stop = True
            raise
    
    def create_trading_universe(self) -> List[CompanyShareEntity]:
        """Create the trading universe (same stocks as backtest)."""
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL"]
        companies_data = []
        
        for i, ticker in enumerate(tickers, start=1):
            companies_data.append({
                'id': i,
                'ticker': ticker,
                'exchange_id': 1,
                'company_id': i,
                'start_date': datetime(2020, 1, 1),
                'company_name': f"{ticker} Inc." if ticker != "GOOGL" else "Alphabet Inc.",
                'sector': 'Technology'
            })
        
        # Create companies
        created_companies = self.create_multiple_companies(companies_data)
        
        
        
        return created_companies
    
    def create_multiple_companies(self, companies_data: List[Dict]) -> List[CompanyShareEntity]:
        """Create multiple companies - same as backtest version."""
        if not companies_data:
            return []
        
        try:
            self.database_service.db.initialize_database_and_create_all_tables()
            
            domain_shares = []
            for data in companies_data:
                domain_share = CompanyShareEntity(
                    id=data['id'],
                    ticker=data['ticker'],
                    exchange_id=data['exchange_id'],
                    company_id=data['company_id'],
                    start_date=data['start_date'],
                    end_date=data.get('end_date')
                )
                
                if 'company_name' in data:
                    domain_share.set_company_name(data['company_name'])
                
                
                
                domain_shares.append(domain_share)
            
            created_entities = self.company_share_repository_local.add_bulk(domain_shares)
            self.logger.info(f"✅ Created {len(created_entities)} companies for live trading")
            
            return created_entities
            
        except Exception as e:
            self.logger.error(f"Error creating companies: {e}")
            raise
    
    def stop(self):
        """Stop live trading gracefully."""
        self.logger.info("Stopping live trading...")
        self.is_running = False
        self.emergency_stop = True
        
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=10)
        
        self.logger.info("Live trading stopped")