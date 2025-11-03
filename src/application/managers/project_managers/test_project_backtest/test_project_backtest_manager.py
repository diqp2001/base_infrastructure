import time
import logging
import random
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_backtest import config
from application.services.misbuffet.algorithm.order import OrderEvent
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import  Dividend
from domain.entities.finance.financial_assets.security import MarketData, Symbol

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.back_testing import StockDataRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper

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
class MyAlgorithm(QCAlgorithm):
    def initialize(self):
        # Call parent initialization first
        super().initialize()
        
        # Define universe and store Security objects
        self.universe = ["AAPL", "MSFT", "AMZN", "GOOGL"]
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

        self.lookback_window = 20   # volatility window
        self.train_window = 252     # ~1 year
        self.retrain_interval = timedelta(days=7)
        self.last_train_time = None

        # Dict of models per ticker
        self.models = {}
        
        # Data tracking for flexible data format handling
        self._current_data_frame = None
        self._current_data_slice = None

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
        # Comprehensive data type handling - accept both Slice and DataFrame objects
        if hasattr(data, 'columns') and hasattr(data, 'index'):
            # This is a DataFrame - convert it to a format we can work with
            self.log(f"INFO: on_data received DataFrame object, converting to internal format: {type(data)}")
            # Store the DataFrame for price lookup instead of expecting Slice format
            self._current_data_frame = data
            self._current_data_slice = None
        elif hasattr(data, 'bars'):
            # This is a proper Slice object
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

        # Step 1: Collect signals
        signals = {}
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

            history = self.history([ticker], self.lookback_window + 2, Resolution.DAILY)
            df = self._prepare_features(history)
            if df.empty:
                continue

            X_live = df[["return_lag1", "return_lag2", "volatility"]].iloc[-1:]
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
                hist_df = pd.concat(df_list)
                pivoted = hist_df.pivot( columns="symbol", values="close")
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
                

    # Event handlers are now in QCAlgorithm base class


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
        from application.services.misbuffet.web.web_interface import WebInterfaceManager
        self.web_interface = WebInterfaceManager()

    def run(self, start_web_interface=True):
        """Main run method that launches web interface and executes backtest
        
        Args:
            start_web_interface (bool): Whether to start web interface (default: True)
                                       Set to False when called from existing web API
        """
        if start_web_interface:
            # Start web interface and open browser
            self.web_interface.start_interface_and_open_browser()
        
        # Start the actual backtest
        return self._run_backtest()
    # Web interface functionality moved to application.services.misbuffet.web_interface
    
    def _run_backtest(self):
        """Execute the actual backtest with progress logging"""
        self.create_five_tech_companies_with_data()
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

    def create_five_tech_companies_with_data(self) -> List[CompanyShareEntity]:
        """
        Create the 5 tech companies (AAPL, MSFT, AMZN, GOOGL) 
        and populate them with market and fundamental data loaded from CSV files.
        """
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL"]
        companies_data = []

        # Path to stock data directory - find project root and build absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # Navigate up to find the project root (where data/ folder is located)
        while not os.path.exists(os.path.join(project_root, 'data', 'stock_data')) and project_root != os.path.dirname(project_root):
            project_root = os.path.dirname(project_root)
        
        stock_data_path = os.path.join(project_root, "data", "stock_data")
        print(f"📁 Loading stock data from: {stock_data_path}")
        
        # Verify the path exists before proceeding
        if not os.path.exists(stock_data_path):
            print(f"❌ Stock data directory not found at: {stock_data_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"File location: {current_dir}")
            print("Available directories in project root:")
            if os.path.exists(project_root):
                for item in os.listdir(project_root):
                    if os.path.isdir(os.path.join(project_root, item)):
                        print(f"  - {item}/")
        else:
            print(f"✅ Stock data directory found with {len(os.listdir(stock_data_path))} files")

        # Load actual stock data from CSV files
        stock_data_cache = {}
        for ticker in tickers:
            csv_path = os.path.join(stock_data_path, f"{ticker}.csv")
            try:
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                    stock_data_cache[ticker] = df
                    print(f"✅ Loaded {len(df)} data points for {ticker} from {df['Date'].min().date()} to {df['Date'].max().date()}")
                else:
                    print(f"⚠️  CSV file not found for {ticker}: {csv_path}")
                    stock_data_cache[ticker] = None
            except Exception as e:
                print(f"❌ Error loading data for {ticker}: {str(e)}")
                stock_data_cache[ticker] = None

        # Sample starting IDs and exchange/company IDs
        start_id = 1
        for i, ticker in enumerate(tickers, start=start_id):
            companies_data.append({
                'id': i,
                'ticker': ticker,
                'exchange_id': 1,
                'company_id': i,
                'start_date': datetime(2020, 1, 1),
                'company_name': f"{ticker} Inc." if ticker != "GOOGL" else "Alphabet Inc.",
                'sector': 'Technology'
            })

        # Step 1: Create companies in bulk
        created_companies = self.create_multiple_companies(companies_data)
        if not created_companies:
            print("❌ No companies were created")
            return []

        # Step 2: Save CSV data to database and enhance with market and fundamental data
        for i, company in enumerate(created_companies):
            ticker = company.ticker
            try:
                # Get stock data for this ticker
                stock_df = stock_data_cache.get(ticker)
                
                if stock_df is not None and not stock_df.empty:
                    # Save CSV data to database for backtesting engine to use
                    table_name = f"stock_price_data_{ticker.lower()}"
                    print(f"💾 Saving {len(stock_df)} price records for {ticker} to database table '{table_name}'")
                    self.database_manager.dataframe_replace_table(stock_df, table_name)
                    
                    # Use the most recent data point for current market data
                    latest_data = stock_df.iloc[-1]
                    latest_price = Decimal(str(latest_data['Close']))
                    latest_volume = Decimal(str(latest_data['Volume']))
                    latest_date = latest_data['Date']
                    
                    # Historical data statistics for fundamental analysis
                    recent_data = stock_df.tail(252)  # Last year of data
                    avg_volume = Decimal(str(recent_data['Volume'].mean()))
                    price_52w_high = Decimal(str(recent_data['High'].max()))
                    price_52w_low = Decimal(str(recent_data['Low'].min()))
                    
                    print(f"📈 Using real data for {ticker}: Latest Close=${latest_price:.2f}, Volume={latest_volume:,}")
                else:
                    # Fallback to mock data if CSV not available
                    latest_price = Decimal(str(100 + i * 50))
                    latest_volume = Decimal(str(1_000_000 + i * 100_000))
                    latest_date = datetime.now()
                    avg_volume = latest_volume
                    price_52w_high = latest_price * Decimal('1.2')
                    price_52w_low = latest_price * Decimal('0.8')
                    print(f"⚠️  Using fallback data for {ticker}")

                # Market data (using real prices and volumes)
                market_data = MarketData(
                    timestamp=latest_date if isinstance(latest_date, datetime) else datetime.now(),
                    price=latest_price,
                    volume=latest_volume
                )
                company.update_market_data(market_data)

                # Fundamental data (mix of real-derived and estimated values)
                # Calculate approximate market cap based on real price
                estimated_shares_outstanding = Decimal(str(1_000_000_000 + i * 100_000_000))  # Estimate
                market_cap = latest_price * estimated_shares_outstanding
                
                

                # Print metrics for confirmation
                metrics = company.get_company_metrics()
                print(f"📊 {company.ticker}: Price=${metrics['current_price']}, "
                    f"P/E={metrics['pe_ratio']}, Market Cap=${market_cap/1_000_000_000:.1f}B, "
                    f"Div Yield={metrics['dividend_yield']}%")

            except Exception as e:
                print(f"❌ Error enhancing company {company.ticker}: {str(e)}")
                continue

        return created_companies

    def create_companies_with_factor_data(self, tickers: List[str] = None) -> List[CompanyShareEntity]:
        """
        Enhanced company creation that integrates with the factor architecture.
        Creates companies and populates factor data for historical prices.
        """
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'SPY']
        
        logger.info(f"Creating companies with factor integration for: {tickers}")
        
        # Initialize factor repository
        share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])
        
        # Create companies using existing method
        created_companies = self.create_five_tech_companies_with_data()
        
        if not created_companies:
            logger.warning("No companies created, skipping factor population")
            return []
        
        # Load historical data and populate factors
        for company in created_companies:
            if company.ticker in tickers:
                try:
                    # Load historical price data from CSV
                    price_data = self._load_stock_price_data(company.ticker)
                    
                    if price_data:
                        # Use mapper to populate factor data
                        created_values = CompanyShareMapper.populate_price_factors(
                            company, 
                            company.id, 
                            price_data, 
                            share_factor_repository
                        )
                        
                        # Also populate current price as a factor
                        current_factor = CompanyShareMapper.populate_current_price_factor(
                            company, 
                            company.id, 
                            share_factor_repository
                        )
                        
                        logger.info(f"Populated {len(created_values)} factor values for {company.ticker}")
                        if current_factor:
                            logger.info(f"Created current price factor for {company.ticker}")
                    
                except Exception as e:
                    logger.error(f"Error populating factors for {company.ticker}: {e}")
                    continue
        
        logger.info(f"Completed factor integration for {len(created_companies)} companies")
        return created_companies

    def _load_stock_price_data(self, ticker: str) -> List[Dict]:
        """
        Load historical stock price data from CSV file.
        """
        try:
            # Find data file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # Navigate up to find project root
            while not os.path.exists(os.path.join(project_root, 'data', 'stock_data')) and project_root != os.path.dirname(project_root):
                project_root = os.path.dirname(project_root)
            
            csv_path = os.path.join(project_root, "data", "stock_data", f"{ticker}.csv")
            
            if not os.path.exists(csv_path):
                logger.warning(f"Stock data file not found: {csv_path}")
                return []
            
            # Load and convert data
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Convert to format expected by mapper
            price_data = []
            for _, row in df.iterrows():
                price_record = {
                    'date': row['Date'],
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'adj_close': row['Adj Close'],
                    'volume': row['Volume']
                }
                price_data.append(price_record)
            
            logger.info(f"Loaded {len(price_data)} price records for {ticker}")
            return price_data
            
        except Exception as e:
            logger.error(f"Error loading price data for {ticker}: {e}")
            return []

    def load_company_with_factors(self, company_id: int) -> Optional[CompanyShareEntity]:
        """
        Load a company share with historical price data populated from factors.
        """
        try:
            # Initialize factor repository
            share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])
            
            # Load ORM company share
            orm_company = self.company_share_repository_local.get_by_id(company_id)
            if not orm_company:
                return None
            
            # Use mapper to load with factor data
            domain_company = CompanyShareMapper.load_price_history_from_factors(orm_company, share_factor_repository)
            
            logger.info(f"Loaded {domain_company.ticker} with factor-based price history")
            return domain_company
            
        except Exception as e:
            logger.error(f"Error loading company with factors: {e}")
            return None

    def get_company_factor_summary(self) -> Dict[str, Any]:
        """
        Get summary of company share factor data.
        """
        try:
            share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])
            
            # Get all company shares
            companies = self.company_share_repository_local.get_all()
            factor_summary = {}
            
            for company in companies:
                try:
                    # Use mapper to get factor summary
                    company_summary = CompanyShareMapper.get_factor_summary(company, share_factor_repository)
                    factor_summary[company.ticker] = company_summary
                    
                except Exception as e:
                    logger.error(f"Error getting factor summary for {company.ticker}: {e}")
                    factor_summary[company.ticker] = {'error': str(e)}
            
            return {
                'total_companies': len(companies),
                'companies_with_factors': len([c for c in factor_summary.values() if 'error' not in c]),
                'factor_details': factor_summary
            }
            
        except Exception as e:
            logger.error(f"Error getting company factor summary: {e}")
            return {'error': str(e)}

    def run_backtest_with_factors(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Run backtest using factor-based data retrieval.
        """
        logger.info("Running backtest with factor integration...")
        
        try:
            # Create companies with factor data
            companies = self.create_companies_with_factor_data()
            
            if not companies:
                raise ValueError("No companies created for backtesting")
            
            # Initialize standard backtest with factor-enhanced data
            result = self.run_backtest(start_date, end_date)
            
            # Add factor summary to result
            factor_summary = self.get_company_factor_summary()
            result['factor_integration'] = {
                'enabled': True,
                'companies_with_factors': len(companies),
                'factor_summary': factor_summary
            }
            
            logger.info("Completed backtest with factor integration")
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest with factors: {e}")
            raise

    