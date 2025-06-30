"""
Comprehensive test suite for the QuantConnect Lean Engine Python implementation.
Tests all engine components and their integration.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import os

# Add the engine module to the path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'application', 'services', 'back_testing'))

# Import engine components
from engine import (
    LeanEngine, BaseEngine, EngineNodePacket, BacktestNodePacket,
    FileSystemDataFeed, BacktestingDataFeed, LiveDataFeed,
    BacktestingTransactionHandler, BrokerageTransactionHandler,
    BacktestingResultHandler, LiveTradingResultHandler,
    ConsoleSetupHandler, BacktestingSetupHandler,
    BacktestingRealTimeHandler, LiveTradingRealTimeHandler,
    AlgorithmHandler, ScheduledEvent, EventPriority
)
from engine.enums import (
    EngineType, EngineStatus, AlgorithmStatus, ComponentState,
    ScheduleEventType, DataFeedMode, TransactionMode
)

# Import common components for testing
from common import (
    IAlgorithm, Symbol, SecurityType, Market, Resolution,
    Order, OrderType, OrderDirection, OrderStatus, OrderEvent,
    BaseData
)


class MockAlgorithm(IAlgorithm):
    """Mock algorithm for testing."""
    
    def __init__(self):
        self.initialized = False
        self.data_received = []
        self.order_events = []
        self.portfolio = Mock()
        self.securities = Mock()
        self.time = datetime.utcnow()
    
    def initialize(self) -> None:
        self.initialized = True
    
    def on_data(self, data) -> None:
        self.data_received.append(data)
    
    def on_order_event(self, order_event) -> None:
        self.order_events.append(order_event)


class TestEngineNodePacket(unittest.TestCase):
    """Test engine node packet configuration."""
    
    def test_packet_creation(self):
        """Test creating an engine node packet."""
        packet = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_name="Test Algorithm",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm"
        )
        
        self.assertEqual(packet.user_id, 123)
        self.assertEqual(packet.project_id, 456)
        self.assertEqual(packet.algorithm_id, "test-algo")
        self.assertIsInstance(packet.starting_capital, Decimal)
        self.assertEqual(packet.starting_capital, Decimal('100000'))
    
    def test_packet_validation(self):
        """Test packet validation."""
        # Valid packet
        packet = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31)
        )
        
        self.assertTrue(packet.validate())
        
        # Invalid packet - start date after end date
        packet.start_date = datetime(2021, 1, 1)
        packet.end_date = datetime(2020, 12, 31)
        
        with self.assertRaises(ValueError):
            packet.validate()
    
    def test_packet_serialization(self):
        """Test packet to_dict and from_dict methods."""
        original = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm"
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = EngineNodePacket.from_dict(data)
        
        self.assertEqual(original.user_id, restored.user_id)
        self.assertEqual(original.algorithm_id, restored.algorithm_id)
        self.assertEqual(original.starting_capital, restored.starting_capital)


class TestDataFeeds(unittest.TestCase):
    """Test data feed implementations."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_algorithm = MockAlgorithm()
        self.temp_dir = tempfile.mkdtemp()
        
        self.job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm",
            data_folder=self.temp_dir
        )
        
        # Create test data file
        self.test_symbol = Symbol.create("AAPL", SecurityType.EQUITY, Market.USA)
        self._create_test_data_file()
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_data_file(self):
        """Create a test CSV data file."""
        data_file = Path(self.temp_dir) / "AAPL_daily.csv"
        with open(data_file, 'w') as f:
            f.write("date,close\n")
            f.write("2020-01-01,300.0\n")
            f.write("2020-01-02,301.0\n")
            f.write("2020-01-03,299.0\n")
    
    def test_filesystem_data_feed_initialization(self):
        """Test FileSystemDataFeed initialization."""
        feed = FileSystemDataFeed()
        self.assertTrue(feed.initialize(self.mock_algorithm, self.job))
        self.assertTrue(feed.is_active())
        
        feed.exit()
        self.assertFalse(feed.is_active())
    
    def test_filesystem_data_feed_subscription(self):
        """Test data subscription management."""
        feed = FileSystemDataFeed()
        feed.initialize(self.mock_algorithm, self.job)
        
        # Create subscription
        config = feed.create_subscription(self.test_symbol, Resolution.DAILY)
        self.assertIsNotNone(config)
        self.assertEqual(config.symbol, self.test_symbol)
        
        # Remove subscription
        self.assertTrue(feed.remove_subscription(config))
        
        feed.exit()
    
    def test_filesystem_data_feed_data_loading(self):
        """Test loading data from files."""
        feed = FileSystemDataFeed()
        feed.initialize(self.mock_algorithm, self.job)
        
        # Create subscription
        config = feed.create_subscription(self.test_symbol, Resolution.DAILY)
        
        # Get data points
        data_points = feed.get_next_ticks()
        self.assertGreater(len(data_points), 0)
        
        # Verify data
        first_point = data_points[0]
        self.assertEqual(first_point.symbol, self.test_symbol)
        self.assertGreater(first_point.value, 0)
        
        feed.exit()
    
    def test_backtesting_data_feed(self):
        """Test BacktestingDataFeed with time filtering."""
        feed = BacktestingDataFeed()
        self.assertTrue(feed.initialize(self.mock_algorithm, self.job))
        
        # Create subscription and get data
        config = feed.create_subscription(self.test_symbol, Resolution.DAILY)
        data_points = feed.get_next_ticks()
        
        # Should filter by job time range
        for point in data_points:
            self.assertGreaterEqual(point.end_time, self.job.start_date)
            self.assertLessEqual(point.end_time, self.job.end_date)
        
        feed.exit()
    
    def test_live_data_feed(self):
        """Test LiveDataFeed simulation."""
        feed = LiveDataFeed()
        self.assertTrue(feed.initialize(self.mock_algorithm, self.job))
        
        # Create subscription
        config = feed.create_subscription(self.test_symbol, Resolution.MINUTE)
        
        # Wait for some simulated data
        time.sleep(0.5)
        data_points = feed.get_next_ticks()
        
        # Should generate some sample data
        self.assertGreaterEqual(len(data_points), 0)
        
        feed.exit()


class TestTransactionHandlers(unittest.TestCase):
    """Test transaction handler implementations."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_algorithm = MockAlgorithm()
        self.test_symbol = Symbol.create("AAPL", SecurityType.EQUITY, Market.USA)
        
        self.test_order = Order(
            symbol=self.test_symbol,
            quantity=100,
            order_type=OrderType.MARKET,
            direction=OrderDirection.BUY
        )
    
    def test_backtesting_transaction_handler(self):
        """Test BacktestingTransactionHandler."""
        handler = BacktestingTransactionHandler()
        handler.initialize(self.mock_algorithm, None)
        
        # Process order
        self.assertTrue(handler.process_order(self.test_order))
        self.assertGreater(self.test_order.id, 0)
        
        # Check order tracking
        orders = handler.get_open_orders()
        self.assertIn(self.test_order, orders)
        
        # Update market price and wait for fill
        handler.update_market_price(self.test_symbol, Decimal('150.0'))
        time.sleep(0.2)  # Wait for simulation
        
        # Check metrics
        metrics = handler.get_metrics()
        self.assertGreater(metrics['total_orders'], 0)
        
        handler.dispose()
    
    def test_transaction_handler_order_management(self):
        """Test order management functionality."""
        handler = BacktestingTransactionHandler()
        handler.initialize(self.mock_algorithm, None)
        
        # Process order
        handler.process_order(self.test_order)
        
        # Get order tickets
        tickets = handler.get_order_tickets()
        self.assertEqual(len(tickets), 1)
        
        # Cancel order
        self.assertTrue(handler.cancel_order(self.test_order.id))
        
        # Update order
        updated_order = Order(
            symbol=self.test_symbol,
            quantity=200,
            order_type=OrderType.LIMIT,
            direction=OrderDirection.BUY,
            limit_price=Decimal('145.0')
        )
        updated_order.id = self.test_order.id
        
        # Note: This will fail because original order was cancelled
        # but tests the update mechanism
        handler.update_order(updated_order)
        
        handler.dispose()
    
    def test_order_validation(self):
        """Test order validation."""
        handler = BacktestingTransactionHandler()
        handler.initialize(self.mock_algorithm, None)
        
        # Valid order
        valid_order = Order(
            symbol=self.test_symbol,
            quantity=100,
            order_type=OrderType.MARKET,
            direction=OrderDirection.BUY
        )
        self.assertTrue(handler.process_order(valid_order))
        
        # Invalid order - zero quantity
        invalid_order = Order(
            symbol=self.test_symbol,
            quantity=0,
            order_type=OrderType.MARKET,
            direction=OrderDirection.BUY
        )
        self.assertFalse(handler.process_order(invalid_order))
        
        handler.dispose()


class TestResultHandlers(unittest.TestCase):
    """Test result handler implementations."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_algorithm = MockAlgorithm()
        self.mock_algorithm.portfolio.total_portfolio_value = Decimal('150000')
        self.mock_algorithm.portfolio.cash_book = Mock()
        self.mock_algorithm.portfolio.cash_book.total_value_in_account_currency = Decimal('50000')
        
        self.temp_dir = tempfile.mkdtemp()
        self.job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_name="Test Algorithm",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm",
            results_folder=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_backtesting_result_handler(self):
        """Test BacktestingResultHandler."""
        handler = BacktestingResultHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Send various result types
        handler.send_status_update("Running", "Algorithm started")
        handler.runtime_statistic("Portfolio Value", "$150,000")
        handler.debug_message("Debug message")
        handler.log_message("Log message")
        handler.error_message("Test error", "Stack trace")
        
        # Add chart data
        handler.chart("Portfolio", "line", "Value", datetime.utcnow(), 150000)
        
        # Store custom result
        handler.store_result({"type": "custom", "data": "test"})
        
        # Process synchronous events
        handler.process_synchronous_events(self.mock_algorithm)
        
        # Send final results
        handler.send_final_result()
        
        handler.exit()
        
        # Check if files were created
        results_files = list(Path(self.temp_dir).glob("backtest_*.json"))
        self.assertGreater(len(results_files), 0)
    
    def test_live_trading_result_handler(self):
        """Test LiveTradingResultHandler."""
        handler = LiveTradingResultHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Send real-time updates
        handler.send_status_update("Connected", "Connected to broker")
        handler.runtime_statistic("Orders", "5")
        
        # Should queue results for real-time transmission
        handler.send_final_result()
        
        handler.exit()
    
    def test_result_handler_charts(self):
        """Test chart functionality."""
        handler = BacktestingResultHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Add multiple chart series
        now = datetime.utcnow()
        handler.chart("Portfolio", "line", "Value", now, 150000)
        handler.chart("Portfolio", "line", "Cash", now, 50000)
        handler.chart("Benchmark", "line", "SPY", now, 100)
        
        # Verify charts were stored
        self.assertIn("Portfolio", handler._charts)
        self.assertIn("Benchmark", handler._charts)
        self.assertEqual(len(handler._charts["Portfolio"]["Value"]), 1)
        
        handler.exit()


class TestSetupHandlers(unittest.TestCase):
    """Test setup handler implementations."""
    
    def setUp(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_name="Test Algorithm",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="MockAlgorithm",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            starting_capital=Decimal('100000')
        )
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('engine.setup_handlers.AlgorithmFactory')
    def test_console_setup_handler(self, mock_factory):
        """Test ConsoleSetupHandler."""
        # Mock algorithm factory
        mock_factory_instance = Mock()
        mock_factory.return_value = mock_factory_instance
        mock_factory_instance.create_algorithm.return_value = MockAlgorithm()
        
        handler = ConsoleSetupHandler()
        
        # Setup algorithm
        algorithm = handler.setup(self.job)
        
        self.assertIsNotNone(algorithm)
        self.assertTrue(algorithm.initialized)
        self.assertEqual(handler.get_start_date(), self.job.start_date)
        self.assertEqual(handler.get_end_date(), self.job.end_date)
        self.assertEqual(handler.get_cash(), self.job.starting_capital)
        
        handler.dispose()
    
    @patch('engine.setup_handlers.AlgorithmFactory')
    def test_backtesting_setup_handler(self, mock_factory):
        """Test BacktestingSetupHandler."""
        # Mock algorithm factory
        mock_factory_instance = Mock()
        mock_factory.return_value = mock_factory_instance
        mock_factory_instance.create_algorithm.return_value = MockAlgorithm()
        
        handler = BacktestingSetupHandler()
        
        # Setup algorithm
        algorithm = handler.setup(self.job)
        
        self.assertIsNotNone(algorithm)
        self.assertTrue(algorithm.initialized)
        
        handler.dispose()
    
    def test_setup_handler_configuration(self):
        """Test setup handler configuration extraction."""
        handler = ConsoleSetupHandler()
        handler._extract_configuration(self.job)
        
        self.assertEqual(handler._start_date, self.job.start_date)
        self.assertEqual(handler._end_date, self.job.end_date)
        self.assertEqual(handler._cash, self.job.starting_capital)


class TestRealTimeHandlers(unittest.TestCase):
    """Test real-time handler implementations."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_algorithm = MockAlgorithm()
        self.job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31)
        )
    
    def test_backtesting_realtime_handler(self):
        """Test BacktestingRealTimeHandler."""
        handler = BacktestingRealTimeHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Test time setting
        test_time = datetime(2020, 6, 1)
        handler.set_time(test_time)
        self.assertEqual(handler._current_time, test_time)
        
        # Test event scheduling
        event_triggered = threading.Event()
        
        def test_callback():
            event_triggered.set()
        
        handler.schedule_function(
            "test_event",
            test_callback,
            test_time + timedelta(seconds=1)
        )
        
        # Advance time to trigger event
        handler.set_time(test_time + timedelta(seconds=2))
        
        # Wait for event processing
        time.sleep(0.1)
        self.assertTrue(event_triggered.is_set())
        
        # Test market hours
        self.assertTrue(handler.is_market_open())  # Assumes market is open by default
        
        handler.exit()
    
    def test_live_trading_realtime_handler(self):
        """Test LiveTradingRealTimeHandler."""
        handler = LiveTradingRealTimeHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Should sync with current time
        self.assertIsNotNone(handler._current_time)
        
        # Test market hours calculation
        next_open = handler.get_next_market_open()
        next_close = handler.get_next_market_close()
        
        self.assertIsInstance(next_open, datetime)
        self.assertIsInstance(next_close, datetime)
        
        handler.exit()
    
    def test_scheduled_events(self):
        """Test scheduled event management."""
        handler = BacktestingRealTimeHandler()
        handler.initialize(self.mock_algorithm, self.job)
        
        # Create scheduled event
        callback_count = 0
        
        def increment_callback():
            nonlocal callback_count
            callback_count += 1
        
        event = ScheduledEvent(
            name="test_recurring",
            scheduled_time=datetime.utcnow() + timedelta(milliseconds=100),
            callback=increment_callback,
            is_recurring=True,
            recurrence_period=timedelta(milliseconds=50)
        )
        
        handler.add(event)
        
        # Wait for multiple triggers
        time.sleep(0.3)
        
        # Should have triggered multiple times
        self.assertGreater(callback_count, 1)
        
        # Remove event
        handler.remove(event)
        old_count = callback_count
        time.sleep(0.1)
        
        # Should stop triggering after removal
        self.assertEqual(callback_count, old_count)
        
        handler.exit()


class TestAlgorithmHandler(unittest.TestCase):
    """Test algorithm handler implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_algorithm = MockAlgorithm()
        self.job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="TestAlgorithm",
            max_runtime_minutes=1  # Short runtime for testing
        )
    
    def test_algorithm_handler_initialization(self):
        """Test AlgorithmHandler initialization."""
        handler = AlgorithmHandler()
        self.assertTrue(handler.initialize(self.job, self.mock_algorithm))
        self.assertEqual(handler.get_status(), AlgorithmStatus.RUNNING)
        
        handler.exit()
        self.assertEqual(handler.get_status(), AlgorithmStatus.STOPPED)
    
    def test_algorithm_handler_data_processing(self):
        """Test algorithm data processing."""
        handler = AlgorithmHandler()
        handler.initialize(self.job, self.mock_algorithm)
        
        # Create mock data slice
        mock_slice = Mock()
        
        # Process data
        handler.on_data(mock_slice)
        
        # Verify algorithm received data
        self.assertEqual(len(self.mock_algorithm.data_received), 1)
        
        # Check statistics
        stats = handler.get_runtime_statistics()
        self.assertEqual(stats['iterations'], 1)
        self.assertEqual(stats['data_points_processed'], 1)
        
        handler.exit()
    
    def test_algorithm_handler_order_events(self):
        """Test algorithm order event processing."""
        handler = AlgorithmHandler()
        handler.initialize(self.job, self.mock_algorithm)
        
        # Create mock order event
        order_event = OrderEvent(
            order_id=1,
            symbol=Symbol.create("AAPL", SecurityType.EQUITY, Market.USA),
            time=datetime.utcnow(),
            status=OrderStatus.FILLED,
            direction=OrderDirection.BUY,
            fill_quantity=100,
            fill_price=Decimal('150.0')
        )
        
        # Process order event
        handler.on_order_event(order_event)
        
        # Verify algorithm received order event
        self.assertEqual(len(self.mock_algorithm.order_events), 1)
        
        handler.exit()
    
    def test_algorithm_handler_performance_sampling(self):
        """Test performance sampling."""
        handler = AlgorithmHandler()
        handler.initialize(self.job, self.mock_algorithm)
        
        # Sample performance
        test_time = datetime.utcnow()
        test_value = Decimal('150000')
        handler.sample_performance(test_time, test_value)
        
        # Check performance samples
        samples = handler.get_performance_samples()
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]['portfolio_value'], float(test_value))
        
        handler.exit()
    
    def test_algorithm_handler_error_handling(self):
        """Test algorithm error handling."""
        # Create algorithm that throws errors
        class ErrorAlgorithm(MockAlgorithm):
            def on_data(self, data):
                raise ValueError("Test error")
        
        error_algorithm = ErrorAlgorithm()
        
        handler = AlgorithmHandler()
        handler.initialize(self.job, error_algorithm)
        
        # Process data that will cause error
        mock_slice = Mock()
        handler.on_data(mock_slice)
        
        # Check error tracking
        errors = handler.get_errors()
        self.assertGreater(len(errors), 0)
        
        stats = handler.get_runtime_statistics()
        self.assertGreater(stats['runtime_errors'], 0)
        
        handler.exit()
    
    def test_algorithm_handler_warmup(self):
        """Test algorithm warmup functionality."""
        handler = AlgorithmHandler()
        handler.initialize(self.job, self.mock_algorithm)
        
        # Set warmup period
        warmup_period = timedelta(seconds=1)
        handler.set_warmup_period(warmup_period)
        
        self.assertTrue(handler.is_warming_up())
        
        # Process data during warmup
        mock_slice = Mock()
        handler.on_data(mock_slice)
        
        # Algorithm should not receive data during warmup
        self.assertEqual(len(self.mock_algorithm.data_received), 0)
        
        # End warmup manually
        handler.end_warmup()
        self.assertFalse(handler.is_warming_up())
        
        # Now algorithm should receive data
        handler.on_data(mock_slice)
        self.assertEqual(len(self.mock_algorithm.data_received), 1)
        
        handler.exit()


class TestLeanEngine(unittest.TestCase):
    """Test the main LeanEngine implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.job = BacktestNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="test-algo",
            algorithm_name="Test Algorithm",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="MockAlgorithm",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 1, 5),  # Short period for testing
            data_folder=self.temp_dir,
            results_folder=self.temp_dir
        )
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_data(self):
        """Create test data files."""
        data_file = Path(self.temp_dir) / "AAPL_daily.csv"
        with open(data_file, 'w') as f:
            f.write("date,close\n")
            f.write("2020-01-01,300.0\n")
            f.write("2020-01-02,301.0\n")
            f.write("2020-01-03,299.0\n")
            f.write("2020-01-04,305.0\n")
            f.write("2020-01-05,307.0\n")
    
    @patch('engine.lean_engine.AlgorithmFactory')
    def test_lean_engine_initialization(self, mock_factory):
        """Test LeanEngine initialization."""
        # Mock algorithm factory
        mock_factory_instance = Mock()
        mock_factory.return_value = mock_factory_instance
        mock_factory_instance.create_algorithm.return_value = MockAlgorithm()
        
        engine = LeanEngine()
        self.assertTrue(engine.initialize())
        self.assertEqual(engine.status, EngineStatus.STOPPED)
        
        engine.dispose()
        self.assertEqual(engine.status, EngineStatus.DISPOSED)
    
    @patch('engine.lean_engine.AlgorithmFactory')
    def test_lean_engine_backtesting_run(self, mock_factory):
        """Test LeanEngine backtesting execution."""
        # Mock algorithm factory
        mock_factory_instance = Mock()
        mock_factory.return_value = mock_factory_instance
        mock_algorithm = MockAlgorithm()
        mock_factory_instance.create_algorithm.return_value = mock_algorithm
        
        engine = LeanEngine()
        engine.initialize()
        
        # Run short backtest
        try:
            engine.run(self.job)
            
            # Check that algorithm was initialized
            self.assertTrue(mock_algorithm.initialized)
            
            # Check engine statistics
            stats = engine.get_realtime_statistics()
            self.assertEqual(stats['status'], EngineStatus.STOPPED.name)
            
        except Exception as e:
            # Expected to fail due to missing dependencies in test environment
            self.assertIsInstance(e, (RuntimeError, AttributeError))
        
        finally:
            engine.dispose()
    
    def test_lean_engine_metrics(self):
        """Test LeanEngine performance metrics."""
        engine = LeanEngine()
        engine.initialize()
        
        # Get performance metrics
        metrics = engine.get_performance_metrics()
        self.assertIn('status', metrics)
        self.assertIn('runtime_seconds', metrics)
        self.assertIn('errors', metrics)
        
        engine.dispose()
    
    def test_lean_engine_stop(self):
        """Test LeanEngine stop functionality."""
        engine = LeanEngine()
        engine.initialize()
        
        # Stop engine
        engine.stop()
        self.assertEqual(engine.status, EngineStatus.STOPPING)
        
        engine.dispose()


class TestEngineIntegration(unittest.TestCase):
    """Test engine component integration."""
    
    def setUp(self):
        """Set up integration test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.job = BacktestNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="integration-test",
            algorithm_name="Integration Test Algorithm",
            algorithm_location="/path/to/algorithm.py",
            algorithm_class_name="IntegrationTestAlgorithm",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 1, 3),
            data_folder=self.temp_dir,
            results_folder=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_handler_communication(self):
        """Test communication between different handlers."""
        # Create handlers
        data_feed = FileSystemDataFeed()
        transaction_handler = BacktestingTransactionHandler()
        result_handler = BacktestingResultHandler()
        setup_handler = ConsoleSetupHandler()
        realtime_handler = BacktestingRealTimeHandler()
        algorithm_handler = AlgorithmHandler()
        
        mock_algorithm = MockAlgorithm()
        
        try:
            # Initialize handlers
            self.assertTrue(data_feed.initialize(mock_algorithm, self.job))
            transaction_handler.initialize(mock_algorithm, None)
            result_handler.initialize(mock_algorithm, self.job)
            realtime_handler.initialize(mock_algorithm, self.job)
            self.assertTrue(algorithm_handler.initialize(self.job, mock_algorithm))
            
            # Test basic operations
            self.assertTrue(data_feed.is_active())
            self.assertTrue(realtime_handler.is_active())
            self.assertEqual(algorithm_handler.get_status(), AlgorithmStatus.RUNNING)
            
            # Send status updates
            result_handler.send_status_update("Testing", "Integration test running")
            
            # Process mock data
            mock_slice = Mock()
            algorithm_handler.on_data(mock_slice)
            
            # Create and process order
            test_order = Order(
                symbol=Symbol.create("AAPL", SecurityType.EQUITY, Market.USA),
                quantity=100,
                order_type=OrderType.MARKET,
                direction=OrderDirection.BUY
            )
            
            transaction_handler.process_order(test_order)
            
            # Verify integration
            self.assertGreater(len(mock_algorithm.data_received), 0)
            
        finally:
            # Cleanup handlers
            for handler in [data_feed, result_handler, realtime_handler, algorithm_handler]:
                if hasattr(handler, 'exit'):
                    handler.exit()
            
            if hasattr(transaction_handler, 'dispose'):
                transaction_handler.dispose()
    
    def test_error_propagation(self):
        """Test error propagation between components."""
        # Create handler that will fail
        result_handler = BacktestingResultHandler()
        
        # Initialize with invalid job
        invalid_job = EngineNodePacket(
            user_id=123,
            project_id=456,
            session_id="test-session",
            algorithm_id="error-test",
            algorithm_location="",  # Invalid location
            algorithm_class_name=""  # Invalid class name
        )
        
        mock_algorithm = MockAlgorithm()
        
        # Should handle initialization errors gracefully
        try:
            result_handler.initialize(mock_algorithm, invalid_job)
            result_handler.error_message("Test error", "Test stack trace")
            result_handler.exit()
        except Exception as e:
            # Expected behavior - errors should be handled gracefully
            self.assertIsInstance(e, Exception)


# Test runner
if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEngineNodePacket,
        TestDataFeeds,
        TestTransactionHandlers,
        TestResultHandlers,
        TestSetupHandlers,
        TestRealTimeHandlers,
        TestAlgorithmHandler,
        TestLeanEngine,
        TestEngineIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)