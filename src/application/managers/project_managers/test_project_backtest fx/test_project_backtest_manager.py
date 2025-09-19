import time
import logging
import random
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

# Import LightGBM for ML functionality
try:
    import lightgbm as lgb
except ImportError:
    # Fallback to XGBoost if LightGBM not available
    try:
        import xgboost as xgb
        lgb = None
    except ImportError:
        # Final fallback to sklearn
        from sklearn.ensemble import RandomForestClassifier
        lgb = None
        xgb = None

from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_backtest import config
from application.services.misbuffet.algorithm.order import OrderEvent
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData, Symbol

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.back_testing import StockDataRepository

# Import the actual backtesting framework components
from application.services.misbuffet.common import (
    IAlgorithm, BaseData, TradeBar, Slice, Resolution, 
    OrderType, OrderDirection, Securities, OrderTicket, TradeBars
)
from application.services.misbuffet.algorithm.base import QCAlgorithm

# Import result handling
from application.services.misbuffet.results import (
    BacktestResultHandler, BacktestResult, PerformanceAnalyzer
)

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
# FX LightGBM + Mean Reversion Algorithm
# Combines machine learning predictions with mean reversion signals for FX trading
# ----------------------------------------------------------------------
class FX_LGBM_MeanReversion_Algorithm(QCAlgorithm):
    def initialize(self):
        super().initialize()
        
        # --- User-configurable settings ---
        self.currencies = ["EUR", "GBP", "AUD", "USD", "MXN", "JPY", "CAD"]
        # Map currency -> tradable FX symbol in your framework
        # NOTE: adjust symbol strings to match your backtester (e.g. 'EURUSD' or 'EUR/USD')
        self.currency_pair_for = {
            "EUR": "EURUSD",
            "GBP": "GBPUSD",
            "AUD": "AUDUSD",
            # USD is special (we'll treat USD direction via inversions across pairs)
            "USD": None,      # handled implicitly by other pairs
            "MXN": "USDMXN",
            "JPY": "USDJPY",
            "CAD": "USDCAD",
        }

        # Only include currencies that have a mapped pair
        self.tradable_currencies = [c for c in self.currencies if self.currency_pair_for.get(c)]
        self.universe = [self.currency_pair_for[c] for c in self.tradable_currencies]

        # Feature / training settings
        self.lookback_window = 60      # rolling window for features & zscore
        self.train_window = 252        # training history (days)
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Model container
        self.models: Dict[str, Any] = {}

        # Positioning
        self.n_long = 2
        self.n_short = 2
        self.target_leverage_per_side = 0.4  # max fraction of portfolio for longs (and for shorts)
                                              # each long will get target_leverage_per_side / n_long

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

        # Initial training (if data exists)
        self._train_models(self.time)

    # ---------------------------
    # Helpers: history & prices
    # ---------------------------
    def _get_history_df(self, symbol: str, lookback_days: int, end_time: datetime) -> pd.DataFrame:
        """Request historical daily bars and return a DataFrame with index=time and columns: open, high, low, close, volume (if available)."""
        try:
            hist = self.history([symbol], lookback_days, Resolution.DAILY, end_time=end_time)
        except Exception as e:
            self.log(f"history call failed for {symbol}: {e}")
            return pd.DataFrame()

        if isinstance(hist, dict):
            # some frameworks return dict of DataFrames keyed by symbol
            df = hist.get(symbol, pd.DataFrame())
            if isinstance(df, pd.DataFrame):
                return df.copy()
            return pd.DataFrame()
        elif isinstance(hist, pd.DataFrame):
            return hist.copy()
        else:
            return pd.DataFrame()

    def _current_price(self, symbol: str):
        # Prefer current slice if available
        try:
            # many frameworks support self.Securities[symbol].Price or self.Securities[symbol].close
            if symbol in self.securities:
                return float(self.securities[symbol].price)
        except Exception:
            pass

        # fallback to history last close
        df = self._get_history_df(symbol, 2, self.time)
        if df.empty:
            return None
        if "close" in df.columns:
            return float(df["close"].iloc[-1])
        # attempt to find typical price column
        for col in ["price", "last"]:
            if col in df.columns:
                return float(df[col].iloc[-1])
        return None

    # ---------------------------
    # Feature engineering
    # ---------------------------
    def _prepare_features_df(self, hist: pd.DataFrame) -> pd.DataFrame:
        """Given a historical DataFrame with 'close', compute features and next-day return label."""
        df = hist.copy()
        if "close" not in df.columns:
            return pd.DataFrame()
        df = df.sort_index()
        df["return"] = df["close"].pct_change()
        df["ma_short"] = df["close"].rolling(5).mean()
        df["ma_long"] = df["close"].rolling(20).mean()
        df["ma_gap"] = (df["close"] - df["ma_long"]) / df["ma_long"]  # relative deviation
        df["volatility"] = df["return"].rolling(self.lookback_window).std()
        df["rsi"] = self._rsi(df["close"], 14)
        # forward return (next day's return)
        df["return_fwd1"] = df["return"].shift(-1)
        df = df.dropna()
        return df

    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -1 * delta.clip(upper=0.0)
        ma_up = up.rolling(period).mean()
        ma_down = down.rolling(period).mean()
        rs = ma_up / (ma_down + 1e-12)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    # ---------------------------
    # Train per-currency model
    # ---------------------------
    def _train_model_for_currency(self, currency: str, current_time: datetime):
        pair = self.currency_pair_for.get(currency)
        if not pair:
            return None

        hist = self._get_history_df(pair, self.train_window + 5, current_time)
        df = self._prepare_features_df(hist)
        if df.empty:
            self.log(f"No training data for {pair}")
            return None

        # features & label
        X = df[["return", "ma_gap", "volatility", "rsi"]]
        # label: 1 if next-day return > 0 (we let ML predict direction)
        y = (df["return_fwd1"] > 0).astype(int)

        # Try LightGBM first, then fallbacks
        try:
            if lgb is not None:
                model = lgb.LGBMClassifier(n_estimators=200, random_state=42)
            elif xgb is not None:
                model = xgb.XGBClassifier(n_estimators=200, random_state=42)
            else:
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=200, random_state=42)
            
            model.fit(X, y)
            self.log(f"Trained model for {currency} ({pair}) on {len(X)} samples")
            return model
        except Exception as e:
            self.log(f"Model train failed for {pair}: {e}")
            return None

    def _train_models(self, current_time: datetime):
        for c in self.tradable_currencies:
            model = self._train_model_for_currency(c, current_time)
            if model is not None:
                self.models[c] = model
        self.last_train_time = current_time
        self.log(f"Models retrained at {current_time.date()}")

    # ---------------------------
    # Mean reversion z-score
    # ---------------------------
    def _zscore(self, series: pd.Series, window: int):
        ma = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (series - ma) / (std + 1e-12)

    # ---------------------------
    # OnData / decision logic
    # ---------------------------
    def on_data(self, data):
        # Retrain periodicly
        if self.last_train_time is None or (self.time - self.last_train_time) >= self.retrain_interval:
            self._train_models(self.time)

        if not self.models:
            return

        currency_scores = {}

        for cur in self.tradable_currencies:
            pair = self.currency_pair_for[cur]
            if pair not in self.my_securities or self.my_securities[pair] is None:
                continue

            # Prepare last lookback_window+1 history for features and zscore
            hist = self._get_history_df(pair, self.lookback_window + 5, self.time)
            if hist.empty or "close" not in hist.columns or len(hist) < (self.lookback_window + 2):
                continue
            df = self._prepare_features_df(hist)
            if df.empty:
                continue

            X_live = df[["return", "ma_gap", "volatility", "rsi"]].iloc[-1:].fillna(0.0)
            model = self.models.get(cur)
            if model is None:
                continue

            # Get ML prediction probability
            try:
                if hasattr(model, 'predict_proba'):
                    prob_pos = float(model.predict_proba(X_live)[0][1])  # probability of next-day positive return
                else:
                    # Fallback for models without predict_proba
                    pred = model.predict(X_live)[0]
                    prob_pos = 0.7 if pred == 1 else 0.3
            except Exception as e:
                self.log(f"Error getting prediction for {cur}: {e}")
                continue

            # mean-reversion zscore: positive z -> price above mean -> expect down (revert)
            z = self._zscore(hist["close"], self.lookback_window).iloc[-1]
            # reversion expectation for next-day return ~ -z (if z>0 expect negative)
            reversion_expectation = -float(z)

            # Combine signals:
            # - If prob_pos high AND reversion_expectation positive => strong long
            # - If prob_pos low AND reversion_expectation negative => strong short
            # Combine with a simple weighted sum (weights tunable)
            ml_w = 0.6
            mr_w = 0.4
            # Normalize prob_pos to [-1,1] where 0=neutral
            ml_signal = (prob_pos - 0.5) * 2.0
            combined_score = ml_w * ml_signal + mr_w * reversion_expectation

            currency_scores[cur] = {
                "pair": pair,
                "prob_pos": prob_pos,
                "z": z,
                "combined_score": combined_score
            }

        if not currency_scores:
            return

        # Rank currencies by combined score
        sorted_items = sorted(currency_scores.items(), key=lambda kv: kv[1]["combined_score"], reverse=True)

        longs = [c for c, _ in sorted_items[: self.n_long]]
        shorts = [c for c, _ in sorted_items[-self.n_short:]]

        self.log(f"Long candidates: {longs}, Short candidates: {shorts}")

        # Convert currency picks to pair-level orders, adjusting sign for pairs where USD is base
        # Position sizing: equal-weight across longs and equal-weight across shorts
        long_weight_each = self.target_leverage_per_side / max(1, len(longs))
        short_weight_each = self.target_leverage_per_side / max(1, len(shorts))

        # First clear positions not in new target set
        target_pairs = set(self.currency_pair_for[c] for c in longs + shorts if self.currency_pair_for.get(c))
        # Set holdings for each tradable pair
        for cur in self.tradable_currencies:
            pair = self.currency_pair_for[cur]
            if pair is None:
                continue
            target_pct = 0.0
            if cur in longs:
                # Long the currency:
                # If the pair is XUSD (currency as base) -> buy pair -> positive target_pct
                # If pair is USDX (USD base, e.g. USDJPY) -> to long foreign currency we need to SHORT the pair (inverse)
                if pair.endswith("USD"):
                    target_pct = long_weight_each
                elif pair.startswith("USD"):
                    target_pct = -long_weight_each  # inverse
            elif cur in shorts:
                # Short the currency:
                if pair.endswith("USD"):
                    target_pct = -short_weight_each
                elif pair.startswith("USD"):
                    target_pct = short_weight_each

            # Place the order (using percent target to keep it simple)
            try:
                if pair in self.securities:
                    self.set_holdings(pair, target_pct)
                    self.log(f"Set holdings for {pair}: target_pct={target_pct:.3f}")
                else:
                    self.log(f"Pair {pair} not in securities (skip)")
            except Exception as e:
                self.log(f"Order failed for {pair}: {e}")

    # ---------------------------
    # Utility: logging wrapper
    # ---------------------------
    def log(self, msg: str):
        logger.info(msg)


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
        
        # Web interface manager
        from application.services.misbuffet.web_interface import WebInterfaceManager
        self.web_interface = WebInterfaceManager()

    def run(self):
        """Main run method that launches web interface and executes backtest"""
        # Start web interface and open browser
        self.web_interface.start_interface_and_open_browser()
        
        # Start the actual backtest
        return self._run_backtest()
    # Web interface functionality moved to application.services.misbuffet.web_interface
    
    def _run_backtest(self):
        """Execute the actual backtest with progress logging"""
        self.create_fx_currency_data()
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("misbuffet-main")

        # Send initial progress message
        self.web_interface.progress_queue.put({
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': 'Starting TestProjectBacktestManager...'
        })

        logger.info("Launching Misbuffet...")

        try:
            # Step 1: Launch package
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Loading Misbuffet framework...'
            })
            
            misbuffet = Misbuffet.launch(config_file="launch_config.py")

            # Step 2: Configure engine with LauncherConfiguration
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Configuring backtest engine...'
            })
            
            config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="FX_LGBM_MeanReversion_Algorithm",  # String name as expected by LauncherConfiguration
                algorithm_location=__file__,
                data_folder=MISBUFFET_ENGINE_CONFIG.get("data_folder", "./downloads"),
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Override with engine config values
            config.custom_config = MISBUFFET_ENGINE_CONFIG
            
            # Add algorithm class to config for engine to use
            config.algorithm = FX_LGBM_MeanReversion_Algorithm  # Pass the class, not an instance
            
            # Add database manager for real data access
            config.database_manager = self.database_manager
            
            logger.info("Configuration setup with database access for real stock data")

            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Starting backtest engine...'
            })
            
            logger.info("Starting engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")

            # Step 3: Run backtest
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Executing backtest algorithm...'
            })
            
            result = engine.run(config)

            logger.info("Backtest finished.")
            logger.info(f"Result summary: {result.summary()}")
            
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'SUCCESS',
                'message': f'Backtest completed successfully! Result: {result.summary()}'
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'ERROR',
                'message': f'Backtest failed: {str(e)}'
            })
            raise

    def create_multiple_companies(self, companies_data: List[Dict]) -> List[CompanyShareEntity]:
        """
        Create multiple CompanyShare entities in a single atomic transaction.
        
        Args:
            companies_data: List of dicts containing company share data
            
        Returns:
            List[CompanyShareEntity]: Successfully created company share entities
        """
        if not companies_data:
            print("No data provided for bulk company creation")
            return []
        
        print(f"Creating {len(companies_data)} companies in bulk operation...")
        start_time = time.time()
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Validate and create domain entities
            domain_shares = []
            for i, data in enumerate(companies_data):
                try:
                    domain_share = CompanyShareEntity(
                        id=data['id'],
                        ticker=data['ticker'],
                        exchange_id=data['exchange_id'],
                        company_id=data['company_id'],
                        start_date=data['start_date'],
                        end_date=data.get('end_date')
                    )
                    
                    # Set company name if provided
                    if 'company_name' in data:
                        domain_share.set_company_name(data['company_name'])
                    
                    # Set sector information if provided  
                    if 'sector' in data:
                        fundamentals = FundamentalData(sector=data['sector'])
                        domain_share.update_company_fundamentals(fundamentals)
                    
                    domain_shares.append(domain_share)
                    
                except Exception as e:
                    print(f"Error creating domain entity {i}: {str(e)}")
                    raise
            
            # Use bulk repository operation (no more key mappings needed)
            created_entities = self.company_share_repository_local.add_bulk(domain_shares)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_entities)} companies in {elapsed:.3f} seconds")
            print(f"⚡ Performance: {len(created_entities)/elapsed:.1f} companies/second")
            
            return created_entities
            
        except Exception as e:
            print(f"❌ Error in bulk company creation: {str(e)}")
            raise

    def create_fx_currency_data(self) -> List[CompanyShareEntity]:
        """
        Load FX currency exchange rate data from CSV and prepare it for backtesting.
        Creates entities for major currency pairs used by the FX algorithm.
        """
        currencies = ["EUR", "GBP", "AUD", "JPY", "CAD", "MXN"]
        currency_data = []

        # Path to FX data directory - find project root and build absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # Navigate up to find the project root (where data/ folder is located)
        while not os.path.exists(os.path.join(project_root, 'data', 'fx_data')) and project_root != os.path.dirname(project_root):
            project_root = os.path.dirname(project_root)
        
        fx_data_path = os.path.join(project_root, "data", "fx_data")
        print(f"📁 Loading FX data from: {fx_data_path}")
        
        # Verify the path exists before proceeding
        if not os.path.exists(fx_data_path):
            print(f"❌ FX data directory not found at: {fx_data_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"File location: {current_dir}")
            print("Available directories in project root:")
            if os.path.exists(project_root):
                for item in os.listdir(project_root):
                    if os.path.isdir(os.path.join(project_root, item)):
                        print(f"  - {item}/")
        else:
            print(f"✅ FX data directory found with {len(os.listdir(fx_data_path))} files")

        # Load actual FX data from CSV file
        csv_path = os.path.join(fx_data_path, "currency_exchange_rates_02-01-1995_-_02-05-2018.csv")
        fx_data_cache = {}
        
        try:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date')
                
                # Extract data for our target currencies
                currency_column_mapping = {
                    "EUR": "Euro",
                    "GBP": "U.K. Pound Sterling", 
                    "AUD": "Australian Dollar",
                    "JPY": "Japanese Yen",
                    "CAD": "Canadian Dollar",
                    "MXN": "Mexican Peso"
                }
                
                for currency, column_name in currency_column_mapping.items():
                    if column_name in df.columns:
                        currency_df = df[['Date', column_name]].copy()
                        currency_df.columns = ['Date', 'Rate']
                        currency_df = currency_df.dropna()
                        
                        # Convert to price format (1/rate for proper FX representation)
                        currency_df['Close'] = 1.0 / currency_df['Rate']
                        currency_df['Open'] = currency_df['Close'].shift(1).fillna(currency_df['Close'])
                        currency_df['High'] = currency_df[['Open', 'Close']].max(axis=1) * 1.001
                        currency_df['Low'] = currency_df[['Open', 'Close']].min(axis=1) * 0.999
                        currency_df['Volume'] = 1000000  # Mock volume for FX
                        
                        fx_data_cache[currency] = currency_df
                        print(f"✅ Loaded {len(currency_df)} data points for {currency} from {currency_df['Date'].min().date()} to {currency_df['Date'].max().date()}")
                    else:
                        print(f"⚠️  Column not found for {currency}: {column_name}")
                        fx_data_cache[currency] = None
            else:
                print(f"⚠️  CSV file not found: {csv_path}")
        except Exception as e:
            print(f"❌ Error loading FX data: {str(e)}")

        # Create currency entities (treating them as special securities)
        start_id = 1
        for i, currency in enumerate(currencies, start=start_id):
            currency_data.append({
                'id': i,
                'ticker': f"USD{currency}" if currency in ["JPY", "CAD", "MXN"] else f"{currency}USD",
                'exchange_id': 1,  # FX exchange
                'company_id': i + 100,  # Offset to avoid conflicts
                'start_date': datetime(1995, 1, 2),
                'company_name': f"{currency} Currency",
                'sector': 'Currency'
            })

        # Step 1: Create currency entities in bulk
        created_currencies = self.create_multiple_companies(currency_data)
        if not created_currencies:
            print("❌ No currencies were created")
            return []

        # Step 2: Save FX data to database and enhance with market data
        for i, currency_entity in enumerate(created_currencies):
            currency = currencies[i]
            ticker = currency_entity.ticker
            
            try:
                # Get FX data for this currency
                fx_df = fx_data_cache.get(currency)
                
                if fx_df is not None and not fx_df.empty:
                    # Save FX data to database for backtesting engine to use
                    table_name = f"fx_price_data_{currency.lower()}"
                    print(f"💾 Saving {len(fx_df)} FX records for {currency} to database table '{table_name}'")
                    self.database_manager.dataframe_replace_table(fx_df, table_name)
                    
                    # Use the most recent data point for current market data
                    latest_data = fx_df.iloc[-1]
                    latest_price = Decimal(str(latest_data['Close']))
                    latest_date = latest_data['Date']
                    
                    print(f"💱 Using real data for {currency}: Latest Rate=${latest_price:.4f}")
                else:
                    # Fallback to mock data if FX data not available
                    latest_price = Decimal('1.0')
                    latest_date = datetime.now()
                    print(f"⚠️  Using fallback data for {currency}")

                # Market data for FX (no volume, just price)
                market_data = MarketData(
                    timestamp=latest_date if isinstance(latest_date, datetime) else datetime.now(),
                    price=latest_price,
                    volume=Decimal('0')  # FX doesn't have traditional volume
                )
                currency_entity.update_market_data(market_data)

                # Basic fundamental data for currencies
                fundamentals = FundamentalData(
                    pe_ratio=Decimal('0'),  # Not applicable for currencies
                    dividend_yield=Decimal('0'),  # Not applicable for currencies
                    market_cap=Decimal('0'),  # Not applicable for currencies
                    shares_outstanding=Decimal('0'),  # Not applicable for currencies
                    sector='Currency',
                    industry=f'{currency} Foreign Exchange'
                )
                currency_entity.update_company_fundamentals(fundamentals)

                # Print metrics for confirmation
                print(f"💱 {currency_entity.ticker}: Rate=${latest_price:.4f}, Sector=Currency")

            except Exception as e:
                print(f"❌ Error enhancing currency {currency_entity.ticker}: {str(e)}")
                continue

        return created_currencies

    
    