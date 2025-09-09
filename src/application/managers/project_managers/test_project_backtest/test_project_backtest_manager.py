import time
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_backtest import config
from application.services.misbuffet.algorithm.order import OrderEvent
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

# Import the actual backtesting framework components
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution, 
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm

# Import domain entities following DDD structure
from domain.entities.back_testing import (
    MockPortfolio, MockSecurity, MockMarketData, Symbol, SecurityType
)
from infrastructure.models.back_testing import (
    MockPortfolioModel, MockSecurityModel
)

# Import result handling
from application.services.misbuffet.results import (
    BacktestResultHandler, BacktestResult, PerformanceAnalyzer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Algorithm implementation using the misbuffet framework
import logging
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Import from the application services misbuffet package
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from application.services.misbuffet.common.interfaces import IAlgorithm
from application.services.misbuffet.common.enums import Resolution
from application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer

# Import config files
from .launch_config import MISBUFFET_LAUNCH_CONFIG
from .engine_config import MISBUFFET_ENGINE_CONFIG 

# ----------------------------------------------------------------------
# Example algorithm: Universe of stocks + weekly retraining + BL optimizer
# ----------------------------------------------------------------------
class MyAlgorithm(IAlgorithm):
    def initialize(self):
        # Define universe
        self.universe = ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
        for ticker in self.universe:
            self.add_equity(ticker, Resolution.DAILY)

        self.lookback_window = 20   # volatility window
        self.train_window = 252     # ~1 year
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Dict of models per ticker
        self.models = {}

        # Initial training
        self._train_models(self.time)

    # ---------------------------
    # Features
    # ---------------------------
    def _prepare_features(self, history: pd.DataFrame) -> pd.DataFrame:
        df = history.copy()
        df["return"] = df["close"].pct_change()
        df["return_lag1"] = df["return"].shift(1)
        df["return_lag2"] = df["return"].shift(2)
        df["volatility"] = df["return"].rolling(self.lookback_window).std()
        df["return_fwd1"] = df["return"].shift(-1)
        return df.dropna()

    # ---------------------------
    # Train one model
    # ---------------------------
    def _train_model_for_ticker(self, ticker: str, current_time: datetime):
        history = self.history(
            [ticker],
            self.train_window,
            Resolution.DAILY,
            end_time=current_time
        )

        df = self._prepare_features(history)
        if df.empty:
            return None

        X = df[["return_lag1", "return_lag2", "volatility"]]
        y = (df["return_fwd1"] > 0).astype(int)

        model = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )
        model.fit(X, y)
        return model

    # ---------------------------
    # Train all models
    # ---------------------------
    def _train_models(self, current_time: datetime):
        for ticker in self.universe:
            model = self._train_model_for_ticker(ticker, current_time)
            if model:
                self.models[ticker] = model

        self.last_train_time = current_time
        self.log(f"Models retrained at {current_time.date()}")

    # ---------------------------
    # On each new data point
    # ---------------------------
    def on_data(self, data):
        # Retrain weekly
        if (
            self.last_train_time is None
            or self.time - self.last_train_time >= self.retrain_interval
        ):
            self._train_models(self.time)

        if not self.models:
            return

        # Step 1: Collect signals
        signals = {}
        for ticker, model in self.models.items():
            if ticker not in data:
                continue

            history = self.history([ticker], self.lookback_window + 2, Resolution.DAILY)
            df = self._prepare_features(history)
            if df.empty:
                continue

            X_live = df[["return_lag1", "return_lag2", "volatility"]].iloc[-1:].values
            pred = model.predict(X_live)[0]  # 1 = long, 0 = short
            signals[ticker] = pred

        if not signals:
            return

        # Step 2: Build Black-Litterman optimizer
        # Convert signals into views: +5% for bullish, -5% for bearish
        views = {t: (0.05 if sig == 1 else -0.05) for t, sig in signals.items()}

        # Compute historical mean & covariance of returns
        hist = self.history(self.universe, self.train_window, Resolution.DAILY)
        
        # Handle both dictionary and DataFrame formats
        if isinstance(hist, dict):
            # Convert dictionary to DataFrame
            df_list = []
            for symbol, data in hist.items():
                if isinstance(data, pd.DataFrame):
                    data['symbol'] = symbol
                    df_list.append(data)
            if df_list:
                hist_df = pd.concat(df_list, ignore_index=True)
                pivoted = hist_df.pivot(index="time", columns="symbol", values="close")
            else:
                # Fallback: create simple returns data
                returns_data = {}
                for symbol in self.universe:
                    # Use mock data for demonstration
                    returns_data[symbol] = np.random.normal(0.001, 0.02, self.train_window)
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

        # Step 3: Execute trades based on BL weights
        total_portfolio_value = self.portfolio.total_portfolio_value
        for ticker, w in weights.items():
            target_value = w * total_portfolio_value
            current_value = self.portfolio[ticker].holdings_value
            diff_value = target_value - current_value
            price = data[ticker].close
            qty = int(diff_value / price)
            if qty != 0:
                self.market_order(ticker, qty)

    def on_order_event(self, order_event: OrderEvent) -> None:
        """Called when an order is filled or updated."""
        self.log(f"OrderEvent: {order_event.symbol} - Status: {order_event.status} - Qty: {order_event.quantity}")

    # ---------------------------
    # End of day
    # ---------------------------
    def on_end_of_day(self, symbol: Symbol) -> None:
        """Called at the end of each trading day."""
        self.log(f"End of day for {symbol.value}")

    # ---------------------------
    # End of algorithm
    # ---------------------------
    def on_end_of_algorithm(self) -> None:
        """Called when the algorithm finishes execution."""
        self.log("Algorithm execution completed.")
    
    # ---------------------------
    # Securities changes
    # ---------------------------
    def on_securities_changed(self, changes: Dict[str, List[Any]]) -> None:
        """Called when securities are added or removed."""
        added = changes.get("added", [])
        removed = changes.get("removed", [])
        if added:
            self.log(f"Securities added: {[s.value for s in added]}")
        if removed:
            self.log(f"Securities removed: {[s.value for s in removed]}")

    # ---------------------------
    # Margin call
    # ---------------------------
    def on_margin_call(self, requests: List[Dict[str, Any]]) -> None:
        """Called when a margin call occurs."""
        for req in requests:
            self.log(f"Margin call: {req}")

    # ---------------------------
    # Option assignment
    # ---------------------------
    def on_assignment(self, assignment_event: Dict[str, Any]) -> None:
        """Called when an option assignment occurs."""
        self.log(f"Option assignment: {assignment_event}")







class TestProjectBacktestManager(ProjectManager):
    """
    Enhanced Project Manager for backtesting operations.
    Implements a complete backtesting pipeline using actual classes instead of mocks.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_manager.session)
        
        # Backtesting components
        self.data_generator = None
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("misbuffet-main")

        logger.info("Launching Misbuffet...")

        try:
            # Step 1: Launch package
            misbuffet = Misbuffet.launch(config_file="launch_config.py")

            # Step 2: Configure engine with LauncherConfiguration
            config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="MyAlgorithm",  # String name as expected by LauncherConfiguration
                algorithm_location=__file__,
                data_folder=MISBUFFET_ENGINE_CONFIG.get("data_folder", "./downloads"),
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Override with engine config values
            config.custom_config = MISBUFFET_ENGINE_CONFIG
            
            # Add algorithm class to config for engine to use
            config.algorithm = MyAlgorithm  # Pass the class, not an instance

            logger.info("Starting engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")

            # Step 3: Run backtest
            result = engine.run(config)

            logger.info("Backtest finished.")
            logger.info(f"Result summary: {result.summary()}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise
    
    