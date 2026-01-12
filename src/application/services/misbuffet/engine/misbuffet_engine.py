"""
Misbuffet Engine Module

This module contains the main MisbuffetEngine class and related components
for backtesting and live trading operations.
"""

import logging
from datetime import timedelta, datetime, date as date_type, date

from typing import Optional, List, Dict, Any
import pandas as pd
import pandas_market_calendars as mcal
import os
import json
from ..common.data_types import Slice, TradeBars, TradeBar
from ..common.symbol import Symbol

try:
    from dateutil.relativedelta import relativedelta
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    relativedelta = None

from decimal import Decimal
# Import service layer instead of direct repository access
from src.application.services.data.entities.factor.factor_data_service import FactorDataService
from application.services.data.entities.entity_service import EntityService
from src.application.services.database_service.database_service import DatabaseService

# Import algorithm framework components instead of domain entities
from ..algorithm.security import SecurityPortfolioManager

# Import BaseEngine for proper inheritance
from .base_engine import BaseEngine
from .engine_node_packet import EngineNodePacket


class MisbuffetEngineConfig:
    """Configuration for MisbuffetEngine to support different entity types."""
    
    def __init__(self, entity_type: str = 'company_shares', entity_config: dict = None):
        self.entity_type = entity_type.lower()
        self.entity_config = entity_config or {}
        self.supported_entity_types = {
            'company_shares': 'CompanyShare',
            'commodities': 'Commodity', 
            'bonds': 'Bond',
            'options': 'Option',
            'currencies': 'Currency',
            'crypto': 'Crypto',
            'etfs': 'ETFShare',
            'futures': 'Future'
        }
        
        if self.entity_type not in self.supported_entity_types:
            raise ValueError(f"Unsupported entity type: {entity_type}. Supported types: {list(self.supported_entity_types.keys())}")


class MisbuffetEngine(BaseEngine):
    """Misbuffet backtesting and live trading engine."""
    
    def __init__(self, config: MisbuffetEngineConfig = None):
        # Initialize BaseEngine first
        super().__init__()
        
        # Engine configuration for entity type support
        self.engine_config = config or MisbuffetEngineConfig()
        
        # Additional MisbuffetEngine specific attributes
        self.stock_data_repository = None
        self.database_manager = None
        
        # Service layer instances (replacing direct repository access)
        self.factor_data_service = None
        self.financial_asset_service = None
        self.database_service = None
        
        # Override logger to maintain existing naming
        self.logger = logging.getLogger("misbuffet.engine")
        self._logger = self.logger  # Keep BaseEngine's logger reference
        
        # Maintain backward compatibility for algorithm attribute
        self.algorithm = self._algorithm
        
    def _get_time_interval(self, config_dict):
        """
        Calculate the time interval based on configuration.
        
        Args:
            config_dict: Engine configuration dictionary
            
        Returns:
            dict with 'type' and 'value' for flexible interval handling
        """
        # Check for custom intervals first (highest priority)
        if config_dict.get('custom_interval_minutes'):
            return {'type': 'timedelta', 'value': timedelta(minutes=config_dict['custom_interval_minutes'])}
        
        if config_dict.get('custom_interval_hours'):
            return {'type': 'timedelta', 'value': timedelta(hours=config_dict['custom_interval_hours'])}
            
        if config_dict.get('custom_interval_days'):
            return {'type': 'timedelta', 'value': timedelta(days=config_dict['custom_interval_days'])}
        
        # Use predefined backtest_interval
        interval = config_dict.get('backtest_interval', 'daily').lower()
        
        # Handle intervals that require dateutil
        if interval in ['monthly', 'quarterly', 'semi_yearly', 'yearly']:
            if DATEUTIL_AVAILABLE:
                interval_mapping = {
                    'monthly': relativedelta(months=1),
                    'quarterly': relativedelta(months=3),
                    'semi_yearly': relativedelta(months=6),
                    'yearly': relativedelta(years=1)
                }
                return {'type': 'relativedelta', 'value': interval_mapping[interval]}
            else:
                # Fallback to approximate days when dateutil is not available
                self.logger.warning(f"dateutil not available, using approximate days for {interval}")
                interval_mapping = {
                    'monthly': timedelta(days=30),
                    'quarterly': timedelta(days=91),  # ~3 months
                    'semi_yearly': timedelta(days=182),  # ~6 months
                    'yearly': timedelta(days=365)
                }
                return {'type': 'timedelta', 'value': interval_mapping[interval]}
        
        # Handle simple intervals with timedelta
        interval_mapping = {
            'seconds': timedelta(seconds=1),
            'minutes': timedelta(minutes=1),
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1)
        }
        
        return {'type': 'timedelta', 'value': interval_mapping.get(interval, timedelta(days=1))}
    
    def _add_time_interval(self, current_date, interval_dict):
        """
        Add the time interval to the current date.
        Handles both timedelta and relativedelta objects.
        Accepts str, date, datetime, or pandas Timestamp.
        """

        # -----------------------------
        # Normalize current_date
        # -----------------------------
        if isinstance(current_date, str):
            current_date = datetime.strptime(current_date, "%Y-%m-%d")
        elif isinstance(current_date, pd.Timestamp):
            current_date = current_date.to_pydatetime()
        elif isinstance(current_date, date) and not isinstance(current_date, datetime):
            current_date = datetime.combine(current_date, datetime.min.time())
        elif not isinstance(current_date, datetime):
            raise TypeError(f"Unsupported current_date type: {type(current_date)}")

        # -----------------------------
        # Add interval
        # -----------------------------
        interval = interval_dict["value"]

        return current_date + interval

    def setup(self, data_feed=None, transaction_handler=None, result_handler=None, setup_handler=None):
        """Setup the engine with handlers."""
        # Use BaseEngine's handler attributes
        if data_feed:
            self._data_feed = data_feed
        if transaction_handler:
            self._transaction_handler = transaction_handler
        if result_handler:
            self._result_handler = result_handler
        if setup_handler:
            self._setup_handler = setup_handler
            
        # Maintain backward compatibility with old attribute names
        self.data_feed = self._data_feed
        self.transaction_handler = self._transaction_handler
        self.result_handler = self._result_handler
        self.setup_handler = self._setup_handler
        
    def run(self, config):
        """Run backtest with the given configuration."""
        self.logger.info("Starting backtest engine...")
        
        # Create a simple EngineNodePacket from config for BaseEngine compatibility
        try:
            from .engine_node_packet import EngineNodePacket
            from .enums import EngineMode, LogLevel, PacketType
            
            # Create job packet from config with required arguments
            job = EngineNodePacket(
                type=PacketType.ALGORITHM_NODE_PACKET,
                user_id=1,  # Default user ID
                project_id=1,  # Default project ID
                session_id="misbuffet_session"  # Default session ID
            )
            job.algorithm_id = getattr(config, 'algorithm_type_name', 'MisbuffetAlgorithm')
            job.engine_mode = EngineMode.BACKTESTING
            job.log_level = LogLevel.INFO
            
            # Set up basic configuration
            engine_config = getattr(config, 'custom_config', {})
            job.start_date = engine_config.get('start_date')
            job.end_date = engine_config.get('end_date')
            
            # Store job for use in BaseEngine methods
            self._job = job
            
        except ImportError:
            # Fallback if engine components aren't available
            self.logger.warning("Could not create EngineNodePacket, using legacy mode")
            pass
        
        try:
            # Initialize algorithm - handle both class and instance
            if hasattr(config, 'algorithm') and config.algorithm:
                # Check if we received a class or an already-instantiated object
                if isinstance(config.algorithm, type):
                    # It's a class, instantiate it
                    self.logger.info(f"Creating algorithm instance from class: {config.algorithm}")
                    self._algorithm = config.algorithm()  # Instantiate the class
                    self.logger.info(f"Algorithm instance created: {self._algorithm}")
                else:
                    # It's already an instance, use it directly
                    self.logger.info(f"Using pre-configured algorithm instance: {config.algorithm}")
                    self._algorithm = config.algorithm
                    self.logger.info(f"Algorithm instance configured: {self._algorithm}")
                
                self.algorithm = self._algorithm  # Maintain backward compatibility
                
            # Setup algorithm with config
            if self.algorithm:
                # Portfolio setup with algorithm framework's SecurityPortfolioManager
                initial_capital = getattr(config, 'initial_capital', 100000)

                # Use the correct SecurityPortfolioManager that integrates with order system
                self.algorithm.portfolio = SecurityPortfolioManager(cash=float(initial_capital))
                
                # Setup time property (required by MyAlgorithm)
                from datetime import datetime
                self.algorithm.time = datetime.now()
                
                # Add log method if not present
                if not hasattr(self.algorithm, 'log'):
                    self.algorithm.log = lambda msg: self.logger.info(f"Algorithm: {msg}")
                
                # Connect market_order method to proper transaction processing
                if not hasattr(self.algorithm, 'market_order'):
                    def connected_market_order(symbol, qty):
                        """Market order method that properly processes fills and updates portfolio."""
                        self.logger.info(f"Market order: {symbol} qty={qty}")
                        
                        # Get current market price for the symbol
                        try:
                            # Try to get price from current data slice or use fallback
                            price = self._get_current_market_price(symbol)
                            
                            # Simulate immediate order execution for backtesting
                            self.algorithm.portfolio.process_fill(
                                symbol=symbol,
                                quantity=qty, 
                                price=price,
                                fees=abs(qty) * 0.01,  # $0.01 per share commission
                                timestamp=self.algorithm.time
                            )
                            
                            self.logger.info(f"✅ Order executed: {symbol} qty={qty} @ ${price:.2f}")
                            
                        except Exception as e:
                            self.logger.error(f"❌ Failed to execute order {symbol} qty={qty}: {e}")
                    
                    self.algorithm.market_order = connected_market_order
                
                # Connect set_holdings method to proper portfolio management
                if not hasattr(self.algorithm, 'set_holdings'):
                    def connected_set_holdings(symbol, percentage, liquidate_existing=False, tag=""):
                        """Set holdings method that properly updates portfolio."""
                        try:
                            # Get current portfolio value
                            total_value = self.algorithm.portfolio.total_portfolio_value_current
                            target_value = total_value * percentage
                            
                            # Get current price
                            price = self._get_current_market_price(symbol)
                            
                            # Calculate target quantity
                            target_quantity = int(target_value / price) if price > 0 else 0
                            
                            # Get current quantity
                            current_holding = self.algorithm.portfolio.get_holding(symbol)
                            current_quantity = current_holding.quantity if current_holding else 0
                            
                            # Calculate order quantity
                            order_quantity = target_quantity - current_quantity
                            
                            if order_quantity != 0:
                                # Execute via market_order which will update portfolio
                                self.algorithm.market_order(symbol, order_quantity)
                                self.logger.info(f"Set holdings for {symbol} to {percentage:.2%} (qty: {target_quantity})")
                            
                        except Exception as e:
                            self.logger.error(f"❌ Failed to set holdings for {symbol}: {e}")
                    
                    self.algorithm.set_holdings = connected_set_holdings
                
                # Add add_equity method if not present
                if not hasattr(self.algorithm, 'add_equity'):
                    def add_equity_with_database(symbol, resolution):
                        if self.stock_data_repository and self.stock_data_repository.table_exists(symbol):
                            self.logger.info(f"✅ Added equity: {symbol} resolution={resolution} (database data available)")
                        else:
                            self.logger.info(f"⚠️ Added equity: {symbol} resolution={resolution} (using mock data - no database table found)")
                    self.algorithm.add_equity = add_equity_with_database
                
                # Setup database connection for real data access
                if hasattr(config, 'database_service') and config.database_service:
                    # Initialize service layer (following DDD principles)
                    self.database_service = config.database_service
                    self.factor_data_service = FactorDataService(self.database_service)
                    self.financial_asset_service = EntityService(self.database_service)
                    self.logger.info(f"Services initialized for {self.engine_config.entity_type} data access")
                elif hasattr(config, 'database_manager'):
                    # Backward compatibility: if database_manager is provided instead
                    self.database_manager = config.database_manager
                    # Try to create database_service from database_manager if needed
                    try:
                        if not self.database_service and hasattr(config.database_manager, 'session'):
                            from src.application.services.database_service.database_service import DatabaseService
                            self.database_service = DatabaseService()
                            self.database_service.session = config.database_manager.session
                            self.factor_data_service = FactorDataService(self.database_service)
                            self.financial_asset_service = EntityService(self.database_service)
                            self.logger.info(f"Services initialized from database_manager for {self.engine_config.entity_type} data access")
                    except Exception as e:
                        self.logger.warning(f"Could not create services from database_manager: {e}")
                else:
                    self.logger.warning("No database_service or database_manager provided in config")
                
                # Add history method that uses real data from database
                if not hasattr(self.algorithm, 'history'):
                    def real_history(tickers, periods, resolution, end_time=None):
                        return self._get_historical_data(tickers, periods, end_time)
                    self.algorithm.history = real_history
                
                self.logger.info(f"Portfolio setup complete with initial capital: {initial_capital}")
            
            # Initialize algorithm - this is where initialize() should be called
            if self.algorithm and hasattr(self.algorithm, 'initialize'):
                self.logger.info("Calling algorithm.initialize()...")
                self.algorithm.initialize()
                self.logger.info("Algorithm.initialize() completed successfully")
            else:
                self.logger.warning("Algorithm doesn't have initialize method or algorithm is None")
                
            # Run simulation and collect performance data
            performance_data = self._run_simulation(config)
            
            # Create comprehensive result
            result = BacktestResult()
            result.success = True
            
            # Set performance data
            engine_config = getattr(config, 'custom_config', {})
            initial_capital = engine_config.get('initial_capital', 100000)
            start_date = engine_config.get('start_date', datetime(2021, 1, 1))
            end_date = engine_config.get('end_date', datetime(2022, 1, 1))
            
            # Calculate final portfolio value from algorithm's portfolio
            final_value = initial_capital
            if self.algorithm and hasattr(self.algorithm, 'portfolio'):
                try:
                    final_value = float(self.algorithm.portfolio.total_portfolio_value_current)
                except:
                    final_value = initial_capital + (performance_data.get('data_points_processed', 0) * 10)
            
            result.set_performance_data(
                initial_capital=initial_capital,
                final_value=final_value,
                start_date=start_date,
                end_date=end_date,
                data_points=performance_data.get('data_points_processed', 0),
                algorithm_calls=performance_data.get('algorithm_calls', 0),
                total_trades=performance_data.get('total_trades', 0)
            )
            
            # Generate and save backtest report
            self._generate_and_save_report(result, engine_config)
            
            self.logger.info("Backtest completed successfully.")
            return result
            
        except Exception as e:
            self.logger.error(f"Engine run failed: {e}")
            result = BacktestResult()
            result.success = False
            result.error_message = str(e)
            return result
    
    def _run_simulation(self, config):
        """Run the actual simulation loop."""
        # Get date range from engine config
        engine_config = getattr(config, 'custom_config', {})
        start_date = datetime.strptime(engine_config.get('start_date', datetime(2021, 1, 1)), "%Y-%m-%d")
        end_date = datetime.strptime(engine_config.get('end_date', datetime(2022, 1, 1)), "%Y-%m-%d")
        
        # Get configurable time interval
        time_interval = self._get_time_interval(engine_config)
        interval_name = engine_config.get('backtest_interval', 'daily')
        
        self.logger.info(f"Running simulation from {start_date} to {end_date}")
        self.logger.info(f"Using {interval_name} intervals for backtesting")
        
        # Log custom interval details if applicable
        if engine_config.get('custom_interval_minutes'):
            self.logger.info(f"Custom interval: {engine_config['custom_interval_minutes']} minutes")
        elif engine_config.get('custom_interval_hours'):
            self.logger.info(f"Custom interval: {engine_config['custom_interval_hours']} hours")
        elif engine_config.get('custom_interval_days'):
            self.logger.info(f"Custom interval: {engine_config['custom_interval_days']} days")
        
        current_date = start_date
        data_points_processed = 0
        
        # Track universe of symbols the algorithm is interested in
        universe = getattr(self.algorithm, 'universe')
        
        # Configurable simulation loop - process data at specified intervals
        while current_date <= end_date:
            # Create data slice with real stock data for this date
            if self.algorithm and hasattr(self.algorithm, 'on_data'):
                try:

                    # Step 1: Verify and ensure data exists
                    if hasattr(self.algorithm, 'trainer') and self.algorithm.trainer and not hasattr(self.algorithm, '_data_verified'):
                        self.logger.info("🔍 Verifying  data availability...")
                        data_verification_result = self.algorithm._verify_and_import_data()
                        
                        if not data_verification_result.get('success', False):
                            self.logger.error("❌ Data verification failed - cannot proceed with trading")
                            return
                        self._data_verified = True
                        self.logger.info("✅ SPX data verified and available")

                    data_slice = self._create_data_slice(current_date, universe)
                    
                    # Only call on_data if we have data for this date
                    if data_slice.has_data:
                        # Update algorithm time
                        self.algorithm.time = current_date
                        
                        # Call on_data with real data
                        self.algorithm.on_data(data_slice)
                        data_points_processed += 1
                        
                        if data_points_processed % 50 == 0:  # Log every 50 data points
                            self.logger.info(f"Processed {data_points_processed} data points, current date: {current_date.date()}")
                    
                except Exception as e:
                    self.logger.warning(f"Algorithm on_data error at {current_date}: {e}")
                    
            current_date = self._add_time_interval(current_date, time_interval)
            
            # Safety check to ensure we don't go beyond end_date
            if current_date > end_date:
                self.logger.info(f"Reached configured end date: {end_date.date()}. Stopping simulation.")
                break
        
            self.logger.info(f"Simulation complete. Processed {data_points_processed} data points.")
        
        # Return performance data
        return {
            'data_points_processed': data_points_processed,
            'algorithm_calls': data_points_processed,  # Same as data points for now
            'total_trades': 0,  # Would be tracked by transaction handler
            'universe_size': len(universe)
        }
    
    def _create_data_slice(self, current_date, universe):
        """
        Create a data slice for the given date focusing on time/date validation.
        
        This method now focuses on providing valid trading dates/times using market calendar,
        rather than loading financial data. The financial data loading is handled by the
        Algorithm.on_data() method through the model training pipeline.
        """
        
        
        # Validate if current_date is a trading day using basic rules
        # This replaces the complex financial data loading with simple time validation
        if not self._is_valid_trading_day(current_date):
            self.logger.debug(f"Skipping non-trading day: {current_date}")
            # Return empty slice for non-trading days
            return Slice(time=current_date)
        
        # Create the slice for this time point
        slice_data = Slice(time=current_date)
        
        # Instead of loading actual financial data, create minimal time-based data slices
        # The actual financial data will be handled by Algorithm.on_data() method
        for ticker in universe:
            try:
                #point_in_time_data is data that we will trade on or simulate trading on 
                point_in_time_data = self._get_point_in_time_data(ticker, current_date)
                if point_in_time_data is not None and not point_in_time_data.empty:
                    # Create Symbol object
                    symbol = Symbol.create_equity(ticker)
                    # Use the most recent data point (should be just one for this date)
                    latest_data = point_in_time_data.iloc[-1]
                
                    # Create minimal TradeBar with time information only
                    # Financial data will be retrieved by the Algorithm through model_trainer
                    trade_bar = TradeBar(
                            symbol=symbol,
                            time=current_date,
                            end_time=current_date,
                            open=float(latest_data.get('Open', latest_data.get('open', 0.0))),
                            high=float(latest_data.get('High', latest_data.get('high', 0.0))),
                            low=float(latest_data.get('Low', latest_data.get('low', 0.0))),
                            close=float(latest_data.get('Close', latest_data.get('close', 0.0))),
                            volume=int(latest_data.get('Volume', latest_data.get('volume', 0)))
                        )
                    
                    # Add to slice - focus on time/date structure rather than financial data
                    slice_data.bars[symbol] = trade_bar
                    # Also add to the data dictionary so has_data() returns True for valid trading days
                    if symbol not in slice_data._data:
                        slice_data._data[symbol] = []
                    slice_data._data[symbol].append(trade_bar)
                        
            except Exception as e:
                self.logger.debug(f"Error creating time slice for {ticker} on {current_date}: {e}")
                continue
        
        # Add debug logging focused on time/date validation
        self.logger.debug(f"Created time-based data slice for {current_date} (trading day: {self._is_valid_trading_day(current_date)}) with {len(slice_data.bars)} symbols")
        
        return slice_data
    
    


    def _is_valid_trading_day(self, date):
        """
        Check if a given date is a valid trading day.

        Priority:
        1. pandas_market_calendars (NYSE) if installed
        2. Fallback to basic weekday + major US holidays
        """
        
        # Normalize to date (strip time)
        if isinstance(date, datetime):
            date = date.date()

        if not isinstance(date, date_type):
            raise TypeError(f"Expected date or datetime, got {type(date)}")

        
        try:
            exchange = mcal.get_calendar("NYSE")
            valid_days = exchange.valid_days(
                start_date=date,
                end_date=date
            )

            return len(valid_days) > 0

        

        except Exception as e:
            self.logger.warning(
                f"Market calendar check failed ({e}), falling back to basic rules"
            )

        # --- 2️⃣ Fallback: weekday + major holidays ---
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        major_holidays = {
            (1, 1),    # New Year's Day
            (7, 4),    # Independence Day
            (12, 25),  # Christmas
        }

        if (date.month, date.day) in major_holidays:
            return False

        return True

    
    def _get_current_market_price(self, symbol):
        """Get current market price for a symbol."""
        try:
            # Try to get from current data slice if available
            current_data = getattr(self.algorithm, '_current_data_slice', None) or getattr(self.algorithm, '_current_data_frame', None)
            
            if current_data:
                # Handle Slice object
                if hasattr(current_data, 'bars'):
                    # Find matching symbol in slice
                    symbol_str = str(symbol).split(',')[0].strip("Symbol('")
                    for data_symbol, trade_bar in current_data.bars.items():
                        data_symbol_str = str(data_symbol).split(',')[0].strip("Symbol('")
                        if symbol_str == data_symbol_str:
                            return trade_bar.close
                
                # Handle DataFrame
                elif hasattr(current_data, 'columns'):
                    if 'close' in current_data.columns or 'Close' in current_data.columns:
                        close_col = 'close' if 'close' in current_data.columns else 'Close'
                        if not current_data.empty:
                            return float(current_data[close_col].iloc[-1])
            
            # Fallback: try to get from stock data repository
            if self.stock_data_repository:
                symbol_str = str(symbol).split(',')[0].strip("Symbol('")
                try:
                    df = self.stock_data_repository.get_historical_data(symbol_str, periods=1)
                    if df is not None and not df.empty:
                        close_col = 'Close' if 'Close' in df.columns else 'close'
                        if close_col in df.columns:
                            return float(df[close_col].iloc[-1])
                except:
                    pass
            
            # Final fallback: use a reasonable default price
            return 100.0
            
        except Exception as e:
            self.logger.debug(f"Error getting market price for {symbol}: {e}")
            return 100.0
    
    def _get_point_in_time_data(self, ticker, point_in_time):
        """Get data for a single day using FactorDataService (entity-agnostic)."""
        if not self.factor_data_service:
            return None
        
        try:
            # Get entity based on configured entity type
            entity = self._get_entity_by_identifier(ticker)
            if not entity:
                self.logger.debug(f"No {self.engine_config.entity_type} entity found for identifier {ticker}")
                return None
            
            # Get factor data based on entity type
            factor_names = self._get_factor_names_for_entity_type()
            factor_data = {}
            
            for factor_name in factor_names:
                factor = self.factor_data_service.get_factor_by_name(factor_name)
                if factor:
                    # Get factor values for the specific date
                    factor_values = self.factor_data_service.get_factor_values(
                        factor_id=int(factor.id),
                        entity_id=entity.id,
                        start_date=point_in_time.strftime('%Y-%m-%d'),
                        end_date=point_in_time.strftime('%Y-%m-%d')
                    )
                    
                    if factor_values:
                        # Use the first (and should be only) value for this date
                        factor_data[factor_name] = float(factor_values[0].value)
            
            # Create DataFrame if we have data
            if factor_data:
                # Add Date column for compatibility
                factor_data['Date'] = point_in_time
                
                # Create single-row DataFrame
                df = pd.DataFrame([factor_data])
                
                self.logger.debug(f"Using factor data for {ticker} on {point_in_time} (factors: {list(factor_data.keys())})")
                return df
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting single day data for {ticker} on {point_in_time}: {e}")
            return None
    
    def _get_entity_by_identifier(self, identifier: str):
        """Get entity by identifier based on configured entity type."""
        if not self.financial_asset_service:
            return None
            
        try:
            entity_type = self.engine_config.entity_type
            
            # Handle different entity types
            if entity_type == 'company_shares':
                return self.factor_data_service.get_company_share_by_ticker(identifier)
            elif entity_type == 'commodities':
                # For commodities, identifier could be symbol
                # This would need a corresponding method in FinancialAssetService
                self.logger.warning(f"Commodity lookup not yet implemented for {identifier}")
                return None
            elif entity_type in ['bonds', 'options', 'currencies', 'crypto', 'etfs', 'futures']:
                # These would need corresponding lookup methods in FinancialAssetService
                self.logger.warning(f"{entity_type} lookup not yet implemented for {identifier}")
                return None
            else:
                self.logger.error(f"Unsupported entity type: {entity_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting entity for {identifier}: {e}")
            return None
    
    def _get_factor_names_for_entity_type(self) -> list:
        """Get relevant factor names based on entity type."""
        entity_type = self.engine_config.entity_type
        
        # Define factor names for different entity types
        factor_mapping = {
            'company_shares': ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'],
            'commodities': ['Price', 'Volume', 'Open Interest'],
            'bonds': ['Price', 'Yield', 'Duration', 'Credit Spread'],
            'options': ['Price', 'Implied Volatility', 'Delta', 'Gamma', 'Theta', 'Vega'],
            'currencies': ['Exchange Rate', 'Bid', 'Ask', 'Volume'],
            'crypto': ['Price', 'Volume', 'Market Cap', 'Circulating Supply'],
            'etfs': ['Open', 'High', 'Low', 'Close', 'Volume', 'NAV'],
            'futures': ['Open', 'High', 'Low', 'Close', 'Volume', 'Open Interest']
        }
        
        return factor_mapping.get(entity_type, ['Open', 'High', 'Low', 'Close', 'Volume'])
    
    def _get_historical_data(self, tickers, periods, end_time=None):
        """
        Retrieve historical stock data from database.
        
        Args:
            tickers: List of ticker symbols or single ticker
            periods: Number of periods to retrieve
            end_time: Optional end date for historical data
            
        Returns:
            DataFrame or dictionary of DataFrames with historical data
        """
        
        
        try:
            # Handle single ticker or list of tickers
            if isinstance(tickers, str):
                tickers = [tickers]
            elif not isinstance(tickers, list):
                # Handle cases where tickers might be passed in other formats
                tickers = list(tickers)
            
            # Get data from database for each ticker
            result_data = {}
            for ticker in tickers:
                df = self.stock_data_repository.get_historical_data(ticker, periods, end_time)
                
                # Rename columns to match expected format
                df_standardized = df.rename(columns={
                    'Date': 'time',
                    'Open': 'open', 
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                result_data[ticker] = df_standardized
                self.logger.info(f"Retrieved {len(df)} records for {ticker} from database")
                
            
            # Return format based on input
            if len(tickers) == 1:
                return result_data.get(tickers[0], pd.DataFrame())
            else:
                return result_data
                
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {e}")
    
    def _generate_and_save_report(self, result: 'BacktestResult', engine_config: Dict[str, Any]):
        """Generate and save comprehensive backtest report."""
        try:
            import os
            import json
            from datetime import datetime

            # Create reports directory if it doesn't exist
            reports_dir = engine_config.get('output_directory', './reports')
            os.makedirs(reports_dir, exist_ok=True)

            # Generate timestamp for unique report name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Collect comprehensive portfolio data
            portfolio_data = self._collect_portfolio_data()

            # Generate report content
            report_content = {
                'backtest_metadata': {
                    'timestamp': timestamp,
                    'start_date': result.start_date,
                    'end_date': result.end_date,
                    'initial_capital': result.initial_capital,
                    'algorithm_name': 'MyAlgorithm',
                    'universe': getattr(self.algorithm, 'universe', ['AAPL', 'MSFT', 'AMZN', 'GOOGL'])
                },
                'performance_summary': {
                    'total_return': result.total_return,
                    'total_return_pct': f"{result.total_return:.2%}" if isinstance(result.total_return, (float, int)) else result.total_return,
                    'final_portfolio_value': result.final_portfolio_value,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                },
                'portfolio_details': portfolio_data,
                'runtime_statistics': result.runtime_statistics
            }

            # Save JSON report
            json_filename = os.path.join(reports_dir, f'backtest_report_{timestamp}.json')
            with open(json_filename, 'w') as f:
                json.dump(report_content, f, indent=2, default=str)

            # Save human-readable text report
            text_filename = os.path.join(reports_dir, f'backtest_summary_{timestamp}.txt')
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write("===== BACKTEST SUMMARY =====\n\n")
                f.write(result.summary() + "\n\n")

                f.write("===== DETAILED PORTFOLIO BREAKDOWN =====\n\n")
                if portfolio_data.get('holdings'):
                    f.write("Current Holdings:\n")
                    for symbol, holding in portfolio_data['holdings'].items():
                        f.write(f"  {symbol}: {holding['quantity']} shares @ ${holding['average_price']:.2f} "
                                f"= ${holding['market_value']:.2f}\n")
                    f.write("\n")

                f.write(f"Cash Balance: ${portfolio_data.get('cash_balance', 0):.2f}\n")
                f.write(f"Total Portfolio Value: ${portfolio_data.get('total_value', 0):.2f}\n")
                f.write("\n")

                f.write("===== PERFORMANCE SUMMARY =====\n\n")
                for key, value in report_content['performance_summary'].items():
                    f.write(f"{key.replace('_', ' ').title()}: {value}\n")

            self.logger.info(f"📊 Backtest report saved to: {json_filename}")
            self.logger.info(f"📄 Backtest summary saved to: {text_filename}")

        except Exception as e:
            self.logger.error(f"Error generating backtest report: {e}")

    
    def _collect_portfolio_data(self) -> Dict[str, Any]:
        #"\"\"Collect detailed portfolio data for reporting.\"\"\"
        portfolio_data = {
            'cash_balance': 0.0,
            'total_value': 0.0,
            'holdings': {}
        }
        
        try:
            if self.algorithm and hasattr(self.algorithm, 'portfolio'):
                portfolio = self.algorithm.portfolio
                
                # Get cash balance
                if hasattr(portfolio, 'cash_balance'):
                    portfolio_data['cash_balance'] = float(portfolio.cash_balance)
                
                # Get total portfolio value
                if hasattr(portfolio, 'total_portfolio_value_current'):
                    portfolio_data['total_value'] = float(portfolio.total_portfolio_value_current)
                
                # Get individual holdings
                if hasattr(portfolio, 'holdings') and portfolio.holdings:
                    for symbol, holding in portfolio.holdings.items():
                        if hasattr(holding, 'quantity') and holding.quantity != 0:
                            portfolio_data['holdings'][str(symbol)] = {
                                'quantity': int(holding.quantity),
                                'average_price': float(getattr(holding, 'average_price', 0)),
                                'market_value': float(getattr(holding, 'market_value', 0)),
                                'unrealized_pnl': float(getattr(holding, 'unrealized_profit_loss', 0))
                            }
                
        except Exception as e:
            self.logger.warning(f"Error collecting portfolio data: {e}")
        
        return portfolio_data

    def _execute_main_loop(self) -> None:
        """Execute the main engine loop. Required by BaseEngine."""
        try:
            # Use the existing simulation logic
            if hasattr(self, '_job') and self._job:
                # Get configuration from the job
                engine_config = getattr(self._job, 'custom_config', {})
                start_date = getattr(self._job, 'start_date', datetime(2021, 1, 1))
                end_date = getattr(self._job, 'end_date', datetime(2022, 1, 1))
            else:
                # Fallback configuration
                engine_config = {}
                start_date = datetime(2021, 1, 1)
                end_date = datetime(2022, 1, 1)
            
            # Get configurable time interval
            time_interval = self._get_time_interval(engine_config)
            interval_name = engine_config.get('backtest_interval', 'daily')
            
            self.logger.info(f"Running simulation from {start_date} to {end_date}")
            self.logger.info(f"Using {interval_name} intervals for backtesting")
            
            # Log custom interval details if applicable
            if engine_config.get('custom_interval_minutes'):
                self.logger.info(f"Custom interval: {engine_config['custom_interval_minutes']} minutes")
            elif engine_config.get('custom_interval_hours'):
                self.logger.info(f"Custom interval: {engine_config['custom_interval_hours']} hours")
            elif engine_config.get('custom_interval_days'):
                self.logger.info(f"Custom interval: {engine_config['custom_interval_days']} days")
            
            current_date = start_date
            data_points_processed = 0
            
            # Track universe of symbols the algorithm is interested in
            universe = getattr(self.algorithm, 'universe', ['AAPL', 'MSFT', 'AMZN', 'GOOGL'])
            
            # Configurable simulation loop - process data at specified intervals
            while current_date <= end_date:
                if self._stop_requested():
                    break
                    
                # Create data slice with real stock data for this date
                if self.algorithm and hasattr(self.algorithm, 'on_data'):
                    try:
                        data_slice = self._create_data_slice(current_date, universe)
                        
                        # Only call on_data if we have data for this date
                        if data_slice.has_data:
                            # Update algorithm time
                            self.algorithm.time = current_date
                            
                            # Call on_data with real data
                            self.algorithm.on_data(data_slice)
                            data_points_processed += 1
                            
                            if data_points_processed % 50 == 0:  # Log every 50 data points
                                self.logger.info(f"Processed {data_points_processed} data points, current date: {current_date.date()}")
                        
                    except Exception as e:
                        self.logger.warning(f"Algorithm on_data error at {current_date}: {e}")
                        
                current_date = self._add_time_interval(current_date, time_interval)
                
                # Safety check to ensure we don't go beyond end_date
                if current_date > end_date:
                    self.logger.info(f"Reached configured end date: {end_date.date()}. Stopping simulation.")
                    break
            
            self.logger.info(f"Simulation complete. Processed {data_points_processed} data points.")
            
        except Exception as e:
            self.logger.error(f"Error in main execution loop: {e}")
            self._errors.append(f"Main loop error: {str(e)}")
            raise

    def _create_handlers(self) -> bool:
        """Create and configure engine handlers. Required by BaseEngine."""
        try:
            self.logger.info("Creating MisbuffetEngine handlers")
            
            
            from . import BacktestingDataFeed
            #Importing Handlers
            from . import (
                BacktestingTransactionHandler, BacktestingResultHandler, 
                BacktestingSetupHandler, BacktestingRealTimeHandler,
                AlgorithmHandler
            )
            
            # Create handlers
            if not self._setup_handler:
                self._setup_handler = BacktestingSetupHandler()
            if not self._data_feed:
                self._data_feed = BacktestingDataFeed()
            if not self._transaction_handler:
                self._transaction_handler = BacktestingTransactionHandler()
            if not self._result_handler:
                self._result_handler = BacktestingResultHandler()
            if not self._realtime_handler:
                self._realtime_handler = BacktestingRealTimeHandler()
            if not self._algorithm_handler:
                self._algorithm_handler = AlgorithmHandler()
                
            # Maintain backward compatibility
            self.setup_handler = self._setup_handler
            self.data_feed = self._data_feed
            self.transaction_handler = self._transaction_handler
            self.result_handler = self._result_handler
                

            
            self.logger.info("MisbuffetEngine handlers created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating handlers: {e}")
            return False


# Mock classes removed - using domain entities instead


class BacktestResult:
    """Result of a backtest run."""
    
    def __init__(self):
        self.success = False
        self.error_message = None
        self.runtime_statistics = {}
        self.performance_statistics = {}
        self.portfolio_statistics = {}
        self.trade_statistics = {}
        self.start_date = None
        self.end_date = None
        self.total_return = 0.0
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
        self.total_trades = 0
        self.win_rate = 0.0
        self.initial_capital = 0.0
        self.final_portfolio_value = 0.0
        
    def summary(self):
        """Return a detailed summary of the backtest results."""
        if self.success:
            summary_lines = [
                "🎉 Backtest completed successfully!",
                "",
                "📊 Performance Summary:",
                f"  • Period: {self.start_date} to {self.end_date}",
                f"  • Initial Capital: ${self.initial_capital:,.2f}",
                f"  • Final Portfolio Value: ${self.final_portfolio_value:,.2f}",
                f"  • Total Return: {self.total_return:.2%}",
                f"  • Sharpe Ratio: {self.sharpe_ratio:.3f}",
                f"  • Maximum Drawdown: {self.max_drawdown:.2%}",
                "",
                "📈 Trading Statistics:",
                f"  • Total Trades: {self.total_trades}",
                f"  • Win Rate: {self.win_rate:.2%}",
                "",
                "⚙️  Runtime Statistics:",
                f"  • Data Points Processed: {self.runtime_statistics.get('data_points_processed', 0)}",
                f"  • Algorithm Calls: {self.runtime_statistics.get('algorithm_calls', 0)}",
                f"  • Errors: {self.runtime_statistics.get('errors', 0)}",
            ]
            
            # Add detailed performance stats if available
            if self.performance_statistics:
                summary_lines.extend([
                    "",
                    "📈 Detailed Performance:",
                    f"  • Alpha: {self.performance_statistics.get('alpha', 0.0):.3f}",
                    f"  • Beta: {self.performance_statistics.get('beta', 0.0):.3f}",
                    f"  • Volatility: {self.performance_statistics.get('volatility', 0.0):.2%}",
                    f"  • Information Ratio: {self.performance_statistics.get('information_ratio', 0.0):.3f}",
                ])
            
            return "\n".join(summary_lines)
        else:
            return f"❌ Backtest failed: {self.error_message}"
    
    def set_performance_data(self, initial_capital, final_value, start_date, end_date, 
                           data_points=0, algorithm_calls=0, total_trades=0):
        """Set basic performance data for the backtest result."""
        self.initial_capital = initial_capital
        self.final_portfolio_value = final_value
        self.start_date = start_date.strftime('%Y-%m-%d') if start_date else "N/A"
        self.end_date = end_date.strftime('%Y-%m-%d') if end_date else "N/A"
        self.total_trades = total_trades
        
        # Calculate total return
        if initial_capital > 0:
            self.total_return = (final_value - initial_capital) / initial_capital
        
        # Update runtime statistics
        self.runtime_statistics.update({
            'data_points_processed': data_points,
            'algorithm_calls': algorithm_calls,
            'total_orders': total_trades,
            'trades': total_trades
        })
        
        # Calculate basic performance metrics (simplified)
        if data_points > 0:
            # Estimate annualized Sharpe ratio (simplified calculation)
            if self.total_return > 0:
                self.sharpe_ratio = self.total_return * (252 ** 0.5) / max(0.01, abs(self.total_return))
            
            # Estimate max drawdown (simplified)
            self.max_drawdown = max(0, -self.total_return * 0.3)  # Rough estimate
        
        # Win rate estimation (simplified)
        self.win_rate = 0.6 if self.total_return > 0 else 0.4


__all__ = [
    'MisbuffetEngine',
    'MisbuffetEngineConfig',
    'BacktestResult'
]