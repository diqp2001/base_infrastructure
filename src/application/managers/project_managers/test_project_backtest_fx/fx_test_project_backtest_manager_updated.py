import time
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

# Import LightGBM for ML functionality with fallback hierarchy
try:
    import lightgbm as lgb
except ImportError:
    try:
        import xgboost as xgb
        lgb = None
    except ImportError:
        from sklearn.ensemble import RandomForestClassifier
        lgb = None
        xgb = None

from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_backtest import config

# Import currency-related entities and repositories
from domain.entities.finance.financial_assets.currency import Currency as CurrencyEntity
from domain.entities.country import Country as CountryEntity
from infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository

# Import the actual backtesting framework components
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution, 
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm

# Import from the application services misbuffet package
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from application.services.misbuffet.common.interfaces import IAlgorithm
from application.services.misbuffet.common.enums import Resolution

# Import config files
from .launch_config import MISBUFFET_LAUNCH_CONFIG
from .engine_config import MISBUFFET_ENGINE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# FX LightGBM + Mean Reversion Algorithm (Enhanced with proper data management)
# ----------------------------------------------------------------------
class FX_LGBM_MeanReversion_Algorithm(QCAlgorithm):
    def initialize(self):
        super().initialize()
        
        # --- User-configurable settings ---
        self.currencies = ["EUR", "GBP", "AUD", "USD", "MXN", "JPY", "CAD"]
        self.currency_pair_for = {
            "EUR": "EURUSD", "GBP": "GBPUSD", "AUD": "AUDUSD",
            "USD": None,  # handled implicitly by other pairs
            "MXN": "USDMXN", "JPY": "USDJPY", "CAD": "USDCAD",
        }

        # Only include currencies that have a mapped pair
        self.tradable_currencies = [c for c in self.currencies if self.currency_pair_for.get(c)]
        self.universe = [self.currency_pair_for[c] for c in self.tradable_currencies]

        # Feature / training settings
        self.lookback_window = 60
        self.train_window = 252
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Model container
        self.models: Dict[str, Any] = {}

        # Positioning
        self.n_long = 2
        self.n_short = 2
        self.target_leverage_per_side = 0.4

        # Add FX securities to the algorithm
        self.my_securities = {}
        for pair in self.universe:
            try:
                sec = self.add_forex(pair, Resolution.DAILY)
                self.my_securities[pair] = sec
                self.log(f"Added FX pair {pair}")
            except Exception as e:
                self.log(f"Failed to add {pair}: {e}")
                self.my_securities[pair] = None

        # Initial training
        self._train_models(self.time)

    def _get_history_df(self, symbol: str, lookback_days: int, end_time: datetime) -> pd.DataFrame:
        """Request historical daily bars and return DataFrame."""
        try:
            hist = self.history([symbol], lookback_days, Resolution.DAILY, end_time=end_time)
            if isinstance(hist, dict):
                df = hist.get(symbol, pd.DataFrame())
                return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
            elif isinstance(hist, pd.DataFrame):
                return hist.copy()
            return pd.DataFrame()
        except Exception as e:
            self.log(f"history call failed for {symbol}: {e}")
            return pd.DataFrame()

    def _prepare_features_df(self, hist: pd.DataFrame) -> pd.DataFrame:
        """Compute features and next-day return label."""
        df = hist.copy()
        if "close" not in df.columns:
            return pd.DataFrame()
        df = df.sort_index()
        df["return"] = df["close"].pct_change()
        df["ma_short"] = df["close"].rolling(5).mean()
        df["ma_long"] = df["close"].rolling(20).mean()
        df["ma_gap"] = (df["close"] - df["ma_long"]) / df["ma_long"]
        df["volatility"] = df["return"].rolling(self.lookback_window).std()
        df["rsi"] = self._rsi(df["close"], 14)
        df["return_fwd1"] = df["return"].shift(-1)
        return df.dropna()

    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -1 * delta.clip(upper=0.0)
        ma_up = up.rolling(period).mean()
        ma_down = down.rolling(period).mean()
        rs = ma_up / (ma_down + 1e-12)
        return 100 - (100 / (1 + rs))

    def _train_model_for_currency(self, currency: str, current_time: datetime):
        """Train ML model for a specific currency."""
        pair = self.currency_pair_for.get(currency)
        if not pair:
            return None

        hist = self._get_history_df(pair, self.train_window + 5, current_time)
        df = self._prepare_features_df(hist)
        if df.empty:
            self.log(f"No training data for {pair}")
            return None

        # Features & label
        X = df[["return", "ma_gap", "volatility", "rsi"]].fillna(0)
        y = (df["return_fwd1"] > 0).astype(int)

        # Try LightGBM -> XGBoost -> Random Forest hierarchy
        try:
            if lgb:
                model = lgb.LGBMClassifier(n_estimators=200, random_state=42)
                model.fit(X, y)
                self.log(f"Trained LightGBM model for {currency} ({pair}) on {len(X)} samples")
                return model
            elif xgb:
                model = xgb.XGBClassifier(n_estimators=200, random_state=42)
                model.fit(X, y)
                self.log(f"Trained XGBoost model for {currency} ({pair}) on {len(X)} samples")
                return model
            else:
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X, y)
                self.log(f"Trained RandomForest model for {currency} ({pair}) on {len(X)} samples")
                return model
        except Exception as e:
            self.log(f"Model training failed for {pair}: {e}")
            return None

    def _train_models(self, current_time: datetime):
        """Train all currency models."""
        for c in self.tradable_currencies:
            model = self._train_model_for_currency(c, current_time)
            if model is not None:
                self.models[c] = model
        self.last_train_time = current_time
        self.log(f"Models retrained at {current_time.date()}")

    def _zscore(self, series: pd.Series, window: int):
        """Calculate z-score for mean reversion."""
        ma = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - ma) / (std + 1e-12)

    def on_data(self, data):
        """Main algorithm logic combining ML + mean reversion."""
        # Retrain periodically
        if (self.last_train_time is None or 
            (self.time - self.last_train_time) >= self.retrain_interval):
            self._train_models(self.time)

        if not self.models:
            return

        # Step 1: Collect signals
        currency_scores = {}
        for cur in self.tradable_currencies:
            pair = self.currency_pair_for[cur]
            if pair not in self.my_securities or self.my_securities[pair] is None:
                continue

            # Get history and prepare features
            hist = self._get_history_df(pair, self.lookback_window + 5, self.time)
            if hist.empty or "close" not in hist.columns or len(hist) < (self.lookback_window + 2):
                continue
            
            df = self._prepare_features_df(hist)
            if df.empty:
                continue

            # ML prediction
            X_live = df[["return", "ma_gap", "volatility", "rsi"]].iloc[-1:].fillna(0.0)
            model = self.models.get(cur)
            if model is None:
                continue

            try:
                if hasattr(model, 'predict_proba'):
                    prob_pos = float(model.predict_proba(X_live)[0][1])
                else:
                    prob_pos = float(model.predict(X_live)[0])
            except Exception as e:
                self.log(f"Model prediction failed for {cur}: {e}")
                continue

            # Mean-reversion z-score
            z = self._zscore(hist["close"], self.lookback_window).iloc[-1]
            reversion_expectation = -float(z)

            # Combine signals (60% ML, 40% mean reversion)
            ml_signal = (prob_pos - 0.5) * 2.0
            combined_score = 0.6 * ml_signal + 0.4 * reversion_expectation

            currency_scores[cur] = {
                "pair": pair,
                "prob_pos": prob_pos,
                "z": z,
                "combined_score": combined_score
            }

        if not currency_scores:
            return

        # Step 2: Rank and select currencies
        sorted_items = sorted(currency_scores.items(), 
                            key=lambda kv: kv[1]["combined_score"], reverse=True)

        longs = [c for c, _ in sorted_items[:self.n_long]]
        shorts = [c for c, _ in sorted_items[-self.n_short:]]

        self.log(f"Long candidates: {longs}, Short candidates: {shorts}")

        # Step 3: Execute trades with proper position sizing
        long_weight_each = self.target_leverage_per_side / max(1, len(longs))
        short_weight_each = self.target_leverage_per_side / max(1, len(shorts))

        for cur in self.tradable_currencies:
            pair = self.currency_pair_for[cur]
            if pair is None or pair not in self.my_securities:
                continue
            
            target_pct = 0.0
            if cur in longs:
                # Long the currency
                target_pct = long_weight_each if pair.endswith("USD") else -long_weight_each
            elif cur in shorts:
                # Short the currency
                target_pct = -short_weight_each if pair.endswith("USD") else short_weight_each

            try:
                self.set_holdings(pair, target_pct)
                self.log(f"Set holdings for {pair}: {target_pct:.3f}")
            except Exception as e:
                self.log(f"Order failed for {pair}: {e}")

    def log(self, msg: str):
        """Logging wrapper."""
        logger.info(msg)


class FXTestProjectBacktestManager(ProjectManager):
    """
    Enhanced FX Project Manager with proper data management patterns.
    Loads FX data from CSV, creates currency entities, and executes FX backtesting.
    """
    
    def __init__(self):
        super().__init__()
        # Initialize database manager
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        
        # Initialize currency repository
        self.currency_repository = CurrencyRepository(self.database_manager.session)
        
        # Backtesting components
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Web interface manager
        from application.services.misbuffet.web_interface import WebInterfaceManager
        self.web_interface = WebInterfaceManager()

    def run(self):
        """Main run method that loads FX data and executes backtest."""
        # Start web interface
        self.web_interface.start_interface_and_open_browser()
        
        # Load FX data and run backtest
        return self._run_fx_backtest()

    def _run_fx_backtest(self):
        """Execute the FX backtest with proper data management."""
        # Step 1: Load and store FX currency data
        self.create_fx_currencies_with_data()
        
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("fx-misbuffet-main")

        # Send initial progress message
        self.web_interface.progress_queue.put({
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': 'Starting FX TestProjectBacktestManager...'
        })

        logger.info("Launching FX Misbuffet...")

        try:
            # Launch package
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Loading FX Misbuffet framework...'
            })
            
            misbuffet = Misbuffet.launch(config_file="launch_config.py")

            # Configure engine
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Configuring FX backtest engine...'
            })
            
            config_obj = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="FX_LGBM_MeanReversion_Algorithm",
                algorithm_location=__file__,
                data_folder=MISBUFFET_ENGINE_CONFIG.get("data_folder", "./downloads"),
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Override with engine config values
            config_obj.custom_config = MISBUFFET_ENGINE_CONFIG
            config_obj.algorithm = FX_LGBM_MeanReversion_Algorithm
            config_obj.database_manager = self.database_manager
            
            logger.info("FX Configuration setup with database access for real FX data")

            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Starting FX backtest engine...'
            })
            
            logger.info("Starting FX engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")

            # Run backtest
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Executing FX backtest algorithm...'
            })
            
            result = engine.run(config_obj)

            logger.info("FX Backtest finished.")
            logger.info(f"FX Result summary: {result.summary()}")
            
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'SUCCESS',
                'message': f'FX Backtest completed successfully! Result: {result.summary()}'
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error running FX backtest: {e}")
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'ERROR',
                'message': f'FX Backtest failed: {str(e)}'
            })
            raise

    def create_fx_currencies_with_data(self) -> List[CurrencyEntity]:
        """
        Load FX data from CSV and create currency entities with historical rates.
        Follows patterns from create_five_tech_companies_with_data.
        """
        logger.info("Creating FX currencies with historical data...")
        
        # Path to FX data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # Navigate up to find project root
        while not os.path.exists(os.path.join(project_root, 'data', 'fx_data')) and project_root != os.path.dirname(project_root):
            project_root = os.path.dirname(project_root)
        
        fx_data_path = os.path.join(project_root, "data", "fx_data", "currency_exchange_rates_02-01-1995_-_02-05-2018.csv")
        
        if not os.path.exists(fx_data_path):
            logger.error(f"FX data file not found: {fx_data_path}")
            return []

        # Load FX data
        logger.info(f"Loading FX data from: {fx_data_path}")
        fx_df = pd.read_csv(fx_data_path)
        fx_df['Date'] = pd.to_datetime(fx_df['Date'])
        fx_df = fx_df.sort_values('Date')
        
        logger.info(f"Loaded {len(fx_df)} FX data points from {fx_df['Date'].min().date()} to {fx_df['Date'].max().date()}")

        # Currency name mapping (subset for backtesting)
        currency_mapping = {
            'Australian Dollar': 'AUD',
            'Canadian Dollar': 'CAD', 
            'Euro': 'EUR',
            'Japanese Yen': 'JPY',
            'U.K. Pound Sterling': 'GBP',
            'Mexican Peso': 'MXN',
            'U.S. Dollar': 'USD'
        }

        # Initialize database
        self.database_manager.db.initialize_database_and_create_all_tables()

        created_currencies = []
        
        for currency_name, iso_code in currency_mapping.items():
            if currency_name not in fx_df.columns and iso_code != 'USD':
                logger.warning(f"Currency {currency_name} not found in FX data")
                continue

            try:
                # Create currency entity
                currency_id = len(created_currencies) + 1
                currency = CurrencyEntity(
                    asset_id=currency_id,
                    name=currency_name,
                    iso_code=iso_code,
                    country_id=None  # Could be mapped to countries if needed
                )

                # Add historical rates for non-USD currencies
                if iso_code != 'USD' and currency_name in fx_df.columns:
                    # Filter out invalid/missing rates
                    currency_data = fx_df[['Date', currency_name]].dropna()
                    currency_data = currency_data[currency_data[currency_name] > 0]
                    
                    # Convert to rate format expected by domain entity
                    rates_data = []
                    for _, row in currency_data.iterrows():
                        rates_data.append({
                            'date': row['Date'],
                            'rate': row[currency_name],
                            'target_currency': 'USD'
                        })
                    
                    # Add historical rates to domain entity
                    currency.add_historical_rates(rates_data)
                    
                    logger.info(f"Added {len(rates_data)} historical rates for {iso_code}")
                else:
                    # USD has rate = 1.0 by definition
                    currency.update_exchange_rate(Decimal('1.0'), datetime.now())

                # Save to database
                saved_currency = self.currency_repository.add(currency)
                created_currencies.append(saved_currency)

                # Save time series data to database table for backtesting engine
                if iso_code != 'USD' and currency_name in fx_df.columns:
                    # Create OHLC data from exchange rates for backtesting
                    ohlc_data = currency_data.copy()
                    ohlc_data['open'] = ohlc_data[currency_name]
                    ohlc_data['high'] = ohlc_data[currency_name] 
                    ohlc_data['low'] = ohlc_data[currency_name]
                    ohlc_data['close'] = ohlc_data[currency_name]
                    ohlc_data['volume'] = 1000000  # Mock volume
                    
                    # Save to database table for backtesting engine
                    table_name = f"fx_price_data_{iso_code.lower()}_usd"
                    ohlc_data_clean = ohlc_data[['Date', 'open', 'high', 'low', 'close', 'volume']].rename(columns={'Date': 'date'})
                    
                    self.database_manager.dataframe_replace_table(ohlc_data_clean, table_name)
                    logger.info(f"Saved {len(ohlc_data_clean)} OHLC records for {iso_code} to table '{table_name}'")

                # Print currency metrics
                metrics = currency.get_currency_metrics()
                logger.info(f"Created {iso_code}: Rate=${metrics['current_rate_usd']}, "
                          f"Major={metrics['is_major']}, Data Points={metrics['historical_data_points']}")

            except Exception as e:
                logger.error(f"Error creating currency {iso_code}: {e}")
                continue

        logger.info(f"Successfully created {len(created_currencies)} FX currencies")
        return created_currencies

    def get_currency_summary(self) -> Dict[str, Any]:
        """Get summary of loaded currencies."""
        try:
            currencies = self.currency_repository.get_all()
            major_currencies = self.currency_repository.get_major_currencies()
            tradeable_currencies = self.currency_repository.get_tradeable_currencies()
            
            return {
                'total_currencies': len(currencies),
                'major_currencies': len(major_currencies),
                'tradeable_currencies': len(tradeable_currencies),
                'currency_list': [c.iso_code for c in currencies]
            }
        except Exception as e:
            logger.error(f"Error getting currency summary: {e}")
            return {}