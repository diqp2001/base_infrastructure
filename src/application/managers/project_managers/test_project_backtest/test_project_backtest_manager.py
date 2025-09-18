import time
import logging
import random
import os
import threading
import webbrowser
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import queue

import pandas as pd
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
            # Check if ticker exists in securities and the security object is not None
            if ticker not in self.my_securities:
                self.log(f"Warning: {ticker} not found in my_securities dictionary")
                continue
            elif self.my_securities[ticker] is None:
                self.log(f"Warning: {ticker} security object is None")
                continue
            elif not self._symbol_in_data(self.my_securities[ticker].symbol, data):
                self.log(f"Warning: {ticker} symbol not found in current data slice")
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
            
            # Check if we have a holding for this security, if not assume zero value
            portfolio_holding = self.portfolio[security.symbol]
            if portfolio_holding is None:
                # No existing holding, current value is zero
                current_value = 0.0
                self.log(f"No existing holding for {ticker}, starting from zero")
            else:
                # Convert existing holding value to float
                current_value = float(portfolio_holding.holdings_value)
            
            diff_value = target_value - current_value
            # Find the matching symbol in data and get its price
            data_symbol = self._find_matching_symbol(security.symbol, data)
            if data_symbol is None:
                self.log(f"Warning: Cannot find price data for {ticker}")
                continue
            price = data[data_symbol].close
            qty = int(diff_value / price)
            if qty != 0:
                self.log(f"Executing order for {ticker}: target=${target_value:.2f}, current=${current_value:.2f}, qty={qty}")
                self.market_order(security.symbol, qty)

    def _symbol_in_data(self, security_symbol, data_slice) -> bool:
        """
        Check if a security symbol exists in the data slice.
        Handles different symbol representations (e.g., with/without country codes).
        
        Args:
            security_symbol: The Symbol object from the security
            data_slice: The Slice object containing market data
        
        Returns:
            bool: True if the symbol is found in the data slice
        """
        # Direct comparison first (fastest)
        if security_symbol in data_slice:
            return True
        
        # Check if any symbol in data matches the ticker
        security_ticker = str(security_symbol).split(',')[0].strip("Symbol('")
        
        for data_symbol in data_slice.bars.keys():
            data_ticker = str(data_symbol).split(',')[0].strip("Symbol('")
            if security_ticker == data_ticker:
                return True
        
        return False
    
    def _find_matching_symbol(self, security_symbol, data_slice):
        """
        Find the matching symbol in the data slice for a given security symbol.
        
        Args:
            security_symbol: The Symbol object from the security
            data_slice: The Slice object containing market data
        
        Returns:
            Symbol: The matching symbol from data_slice, or None if not found
        """
        # Direct comparison first
        if security_symbol in data_slice:
            return security_symbol
        
        # Check if any symbol in data matches the ticker
        security_ticker = str(security_symbol).split(',')[0].strip("Symbol('")
        
        for data_symbol in data_slice.bars.keys():
            data_ticker = str(data_symbol).split(',')[0].strip("Symbol('")
            if security_ticker == data_ticker:
                return data_symbol
        
        return None
    
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
        
        # Web interface components
        self.flask_app = None
        self.flask_thread = None
        self.progress_queue = queue.Queue()
        self.is_running = False
        
        # Set up shared progress handler
        self._setup_progress_logging()

    def run(self):
        """Main run method that launches web interface and executes backtest"""
        # Start Flask web interface first
        self._start_web_interface()
        
        # Give Flask a moment to start
        time.sleep(5)
        
        # Open browser automatically
        self._open_browser()

        # Give Flask a moment to start
        time.sleep(5)
        
        # Start the actual backtest
        return self._run_backtest()
    
    def _setup_progress_logging(self):
        """Set up logging handler to capture progress messages"""
        # Create custom handler that puts messages in queue
        class ProgressHandler(logging.Handler):
            def __init__(self, progress_queue):
                super().__init__()
                self.progress_queue = progress_queue
                
            def emit(self, record):
                message = self.format(record)
                self.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'message': message
                })
        
        # Add handler to capture all misbuffet logs
        progress_handler = ProgressHandler(self.progress_queue)
        progress_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add to main loggers
        logging.getLogger("misbuffet-main").addHandler(progress_handler)
        logging.getLogger("misbuffet.engine").addHandler(progress_handler)
        logging.getLogger(self.__class__.__name__).addHandler(progress_handler)
    
    def _start_web_interface(self):
        """Start Flask web interface in a separate thread"""
        from src.interfaces.flask.flask import FlaskApp
        from flask import Flask, render_template, request, Response, jsonify
        import json
        
        # Create Flask app instance
        self.flask_app = FlaskApp()
        
        # Add progress streaming endpoint
        def generate_progress():
            """Server-Sent Events generator for progress updates"""
            try:
                while True:
                    try:
                        # Wait for new message with timeout
                        message = self.progress_queue.get(timeout=1)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send heartbeat to keep connection alive
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
            except GeneratorExit:
                # Client disconnected, clean exit
                print("🔌 Client disconnected from progress stream")
                return
            except Exception as e:
                print(f"❌ Error in progress stream: {e}")
                return
        
        @self.flask_app.app.route('/progress_stream')
        def progress_stream():
            """Server-Sent Events endpoint for progress updates"""
            return Response(generate_progress(), mimetype='text/event-stream', headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            })
        
        # Add backtest progress page
        @self.flask_app.app.route('/backtest_progress')
        def backtest_progress():
            """Display backtest progress with real-time updates"""
            return render_template('backtest_progress.html')
        
        # Add shutdown endpoint for clean server shutdown
        @self.flask_app.app.route('/shutdown', methods=['POST'])
        def shutdown_server():
            """Shutdown the Flask server gracefully"""
            print("🛑 Shutdown request received")
            self.is_running = False
            # Use Werkzeug's shutdown function
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                return 'Server shutdown failed - not running with Werkzeug server', 500
            func()
            return 'Server shutting down...', 200
        
        # Start Flask in separate thread
        def run_flask():
            try:
                self.flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"❌ Flask server error: {e}")
            finally:
                print("🛑 Flask server stopped")
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        
        self.is_running = True
        print("🌐 Flask web interface started at http://localhost:5000")
        print("📊 Progress monitor available at http://localhost:5000/backtest_progress")
    
    def _open_browser(self):
        """Automatically open browser to progress page"""
        try:
            webbrowser.open('http://localhost:5000/backtest_progress')
            print("🖥️  Browser opened automatically to backtest progress page")
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print("📍 Please manually navigate to: http://localhost:5000/backtest_progress")
    
    def _run_backtest(self):
        """Execute the actual backtest with progress logging"""
        self.create_five_tech_companies_with_data()
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("misbuffet-main")

        # Send initial progress message
        self.progress_queue.put({
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': 'Starting TestProjectBacktestManager...'
        })

        logger.info("Launching Misbuffet...")

        try:
            # Step 1: Launch package
            self.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Loading Misbuffet framework...'
            })
            
            misbuffet = Misbuffet.launch(config_file="launch_config.py")

            # Step 2: Configure engine with LauncherConfiguration
            self.progress_queue.put({
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

            self.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Starting backtest engine...'
            })
            
            logger.info("Starting engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")

            # Step 3: Run backtest
            self.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Executing backtest algorithm...'
            })
            
            result = engine.run(config)

            logger.info("Backtest finished.")
            logger.info(f"Result summary: {result.summary()}")
            
            self.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'SUCCESS',
                'message': f'Backtest completed successfully! Result: {result.summary()}'
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            self.progress_queue.put({
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
                
                # Estimate P/E ratio based on sector averages
                pe_ratios = {"AAPL": 25.0, "MSFT": 28.0, "AMZN": 35.0, "GOOGL": 22.0}
                pe_ratio = Decimal(str(pe_ratios.get(ticker, 25.0)))
                
                fundamentals = FundamentalData(
                    pe_ratio=pe_ratio,
                    dividend_yield=Decimal(str(1.0 + i * 0.3)),  # Estimated dividend yields
                    market_cap=market_cap,
                    shares_outstanding=estimated_shares_outstanding,
                    sector='Technology',
                    industry='Software' if ticker not in ["AMZN", "GOOGL"] else ('E-commerce' if ticker == "AMZN" else 'Internet Services')
                )
                company.update_company_fundamentals(fundamentals)

                # Sample dividend (estimated based on dividend yield)
                dividend_amount = (fundamentals.dividend_yield / 100) * latest_price / 4  # Quarterly dividend
                dividend = Dividend(
                    amount=dividend_amount,
                    ex_date=datetime(2024, 3, 15),
                    pay_date=datetime(2024, 3, 30)
                )
                company.add_dividend(dividend)

                # Print metrics for confirmation
                metrics = company.get_company_metrics()
                print(f"📊 {company.ticker}: Price=${metrics['current_price']}, "
                    f"P/E={metrics['pe_ratio']}, Market Cap=${market_cap/1_000_000_000:.1f}B, "
                    f"Div Yield={metrics['dividend_yield']}%")

            except Exception as e:
                print(f"❌ Error enhancing company {company.ticker}: {str(e)}")
                continue

        return created_companies

    
    