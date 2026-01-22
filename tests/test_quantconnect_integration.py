"""
Tests for QuantConnect Integration with Misbuffet Service

Tests the QuantConnect-style data management layer, history provider,
and frontier time management functionality.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd

from src.application.services.misbuffet.common.symbol import Symbol
from src.application.services.misbuffet.common.enums import Resolution, SecurityType
from src.application.services.misbuffet.common.data_types import Slice, TradeBar, QuoteBar
from src.application.services.misbuffet.data.quantconnect_data_manager import (
    QuantConnectDataManager, QuantConnectCompatibilityLayer
)
from src.application.services.misbuffet.data.quantconnect_history_provider import (
    QuantConnectHistoryProvider, HistoryRequest, QuantConnectSliceBuilder
)
from src.application.services.misbuffet.engine.quantconnect_frontier_manager import (
    FrontierTimeManager, AlgorithmTimeCoordinator
)


class TestQuantConnectDataManager(unittest.TestCase):
    """Test QuantConnect data manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_feed = Mock()
        self.mock_entity_service = Mock()
        self.mock_factor_service = Mock()
        
        self.data_manager = QuantConnectDataManager(
            data_feed=self.mock_data_feed,
            entity_service=self.mock_entity_service,
            factor_service=self.mock_factor_service
        )
    
    def test_initialization(self):
        """Test data manager initialization."""
        self.assertIsNotNone(self.data_manager)
        self.assertEqual(self.data_manager._data_feed, self.mock_data_feed)
        self.assertEqual(self.data_manager._entity_service, self.mock_entity_service)
        self.assertEqual(self.data_manager._factor_service, self.mock_factor_service)
    
    def test_add_equity(self):
        """Test adding equity subscription."""
        # Mock data feed methods
        self.mock_data_feed.initialize.return_value = True
        self.mock_data_feed.create_subscription.return_value = Mock()
        
        # Initialize data manager
        success = self.data_manager.initialize()
        self.assertTrue(success)
        
        # Add equity
        symbol = self.data_manager.add_equity("AAPL", Resolution.DAILY)
        
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.value, "AAPL")
        self.assertEqual(symbol.security_type, SecurityType.EQUITY)
        self.assertIn("AAPL", self.data_manager.get_universe())
    
    def test_add_forex(self):
        """Test adding forex subscription."""
        self.mock_data_feed.initialize.return_value = True
        self.mock_data_feed.create_subscription.return_value = Mock()
        
        self.data_manager.initialize()
        symbol = self.data_manager.add_forex("EURUSD", Resolution.DAILY)
        
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.value, "EURUSD")
        self.assertEqual(symbol.security_type, SecurityType.FOREX)
    
    def test_add_crypto(self):
        """Test adding crypto subscription."""
        self.mock_data_feed.initialize.return_value = True
        self.mock_data_feed.create_subscription.return_value = Mock()
        
        self.data_manager.initialize()
        symbol = self.data_manager.add_crypto("BTCUSD", Resolution.DAILY)
        
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.value, "BTCUSD")
        self.assertEqual(symbol.security_type, SecurityType.CRYPTO)
    
    def test_history_single_symbol(self):
        """Test getting history for single symbol."""
        # Mock factor service response
        mock_entity = Mock()
        mock_entity.id = 1
        self.mock_entity_service.get_by_symbol.return_value = mock_entity
        
        mock_factor = Mock()
        mock_factor.id = 1
        self.mock_factor_service.get_factor_by_name.return_value = mock_factor
        
        mock_factor_value = Mock()
        mock_factor_value.date = datetime.now().date()
        mock_factor_value.value = 150.0
        self.mock_factor_service.get_factor_values.return_value = [mock_factor_value]
        
        # Test history call
        history = self.data_manager.history("AAPL", 10, Resolution.DAILY)
        
        self.assertIsInstance(history, pd.DataFrame)
    
    def test_history_multiple_symbols(self):
        """Test getting history for multiple symbols."""
        # Setup mocks
        mock_entity = Mock()
        mock_entity.id = 1
        self.mock_entity_service.get_by_symbol.return_value = mock_entity
        
        mock_factor = Mock()
        mock_factor.id = 1
        self.mock_factor_service.get_factor_by_name.return_value = mock_factor
        
        mock_factor_value = Mock()
        mock_factor_value.date = datetime.now().date()
        mock_factor_value.value = 150.0
        self.mock_factor_service.get_factor_values.return_value = [mock_factor_value]
        
        # Test multiple symbols
        history = self.data_manager.history(["AAPL", "MSFT"], 10, Resolution.DAILY)
        
        self.assertIsInstance(history, dict)
        self.assertIn("AAPL", history)
        self.assertIn("MSFT", history)
    
    def test_create_data_slice(self):
        """Test creating data slice."""
        # Mock data feed
        mock_trade_bar = TradeBar(
            symbol=Symbol.create_equity("AAPL"),
            time=datetime.now(),
            end_time=datetime.now(),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000
        )
        
        self.mock_data_feed.get_next_ticks.return_value = [mock_trade_bar]
        
        # Create slice
        current_time = datetime.now()
        slice_obj = self.data_manager.create_data_slice(current_time, ["AAPL"])
        
        self.assertIsInstance(slice_obj, Slice)
        self.assertEqual(slice_obj.time, current_time)
        self.assertTrue(slice_obj.has_data)
    
    def test_set_universe(self):
        """Test setting universe of symbols."""
        self.mock_data_feed.initialize.return_value = True
        self.mock_data_feed.create_subscription.return_value = Mock()
        
        self.data_manager.initialize()
        
        universe = ["AAPL", "MSFT", "GOOGL"]
        self.data_manager.set_universe(universe, Resolution.DAILY)
        
        actual_universe = self.data_manager.get_universe()
        self.assertEqual(set(actual_universe), set(universe))
    
    def test_frontier_time_management(self):
        """Test frontier time get/set."""
        test_time = datetime(2023, 1, 1, 10, 0, 0)
        
        self.data_manager.set_frontier_time(test_time)
        frontier_time = self.data_manager.get_frontier_time()
        
        self.assertEqual(frontier_time, test_time)


class TestQuantConnectHistoryProvider(unittest.TestCase):
    """Test QuantConnect history provider functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_entity_service = Mock()
        self.mock_factor_service = Mock()
        
        self.history_provider = QuantConnectHistoryProvider(
            entity_service=self.mock_entity_service,
            factor_service=self.mock_factor_service
        )
    
    def test_initialization(self):
        """Test history provider initialization."""
        self.assertTrue(self.history_provider.initialize())
    
    def test_get_history_periods(self):
        """Test getting history for specified periods."""
        # Setup mocks
        mock_entity = Mock()
        mock_entity.id = 1
        self.mock_entity_service.get_by_symbol.return_value = mock_entity
        
        mock_factor = Mock()
        mock_factor.id = 1
        self.mock_factor_service.get_factor_by_name.return_value = mock_factor
        
        mock_factor_values = []
        for i in range(10):
            mock_fv = Mock()
            mock_fv.date = datetime.now().date() - timedelta(days=i)
            mock_fv.value = 150.0 + i
            mock_factor_values.append(mock_fv)
        
        self.mock_factor_service.get_factor_values.return_value = mock_factor_values
        
        # Test history retrieval
        symbol = Symbol.create_equity("AAPL")
        history = self.history_provider.get_history_periods(
            symbol, 10, Resolution.DAILY
        )
        
        self.assertIsInstance(history, pd.DataFrame)
    
    def test_get_history_single(self):
        """Test getting history for date range."""
        # Setup mocks similar to above
        mock_entity = Mock()
        mock_entity.id = 1
        self.mock_entity_service.get_by_symbol.return_value = mock_entity
        
        mock_factor = Mock()
        mock_factor.id = 1
        self.mock_factor_service.get_factor_by_name.return_value = mock_factor
        
        self.mock_factor_service.get_factor_values.return_value = []
        
        symbol = Symbol.create_equity("AAPL")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        history = self.history_provider.get_history_single(
            symbol, start_date, end_date, Resolution.DAILY
        )
        
        self.assertIsInstance(history, pd.DataFrame)
    
    def test_is_valid_trading_day(self):
        """Test trading day validation."""
        # Test weekday (should be valid)
        weekday = datetime(2023, 1, 3)  # Tuesday
        self.assertTrue(self.history_provider.is_valid_trading_day(weekday))
        
        # Test weekend (should be invalid) 
        weekend = datetime(2023, 1, 7)  # Saturday
        self.assertFalse(self.history_provider.is_valid_trading_day(weekend))
        
        # Test holiday (should be invalid)
        new_years = datetime(2023, 1, 1)  # New Year's Day
        self.assertFalse(self.history_provider.is_valid_trading_day(new_years))


class TestFrontierTimeManager(unittest.TestCase):
    """Test frontier time manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock()
        self.mock_history_provider = Mock()
        
        self.frontier_manager = FrontierTimeManager(
            data_manager=self.mock_data_manager,
            history_provider=self.mock_history_provider
        )
    
    def test_initialization(self):
        """Test frontier time manager initialization."""
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 12, 31)
        
        success = self.frontier_manager.initialize(
            start_time, end_time, Resolution.DAILY
        )
        
        self.assertTrue(success)
        self.assertEqual(self.frontier_manager.get_frontier_time(), start_time)
    
    def test_advance_time(self):
        """Test advancing frontier time."""
        start_time = datetime(2023, 1, 2)  # Monday
        end_time = datetime(2023, 1, 31)
        
        # Initialize
        self.frontier_manager.initialize(start_time, end_time, Resolution.DAILY)
        
        # Mock data manager methods
        mock_slice = Mock(spec=Slice)
        mock_slice.has_data = True
        self.mock_data_manager.create_data_slice.return_value = mock_slice
        
        # Advance time
        slice_obj = self.frontier_manager.advance_time(["AAPL"])
        
        self.assertIsNotNone(slice_obj)
        self.assertGreater(self.frontier_manager.get_frontier_time(), start_time)
    
    def test_market_hours_validation(self):
        """Test market hours validation."""
        # Market open time
        market_open = datetime(2023, 1, 3, 9, 30, 0)  # Tuesday 9:30 AM
        self.assertTrue(self.frontier_manager.is_market_open_time(market_open))
        
        # Market closed time
        market_closed = datetime(2023, 1, 3, 20, 0, 0)  # Tuesday 8:00 PM
        self.assertFalse(self.frontier_manager.is_market_open_time(market_closed))
        
        # Weekend
        weekend = datetime(2023, 1, 7, 10, 0, 0)  # Saturday
        self.assertFalse(self.frontier_manager.is_market_open_time(weekend))
    
    def test_trading_day_validation(self):
        """Test trading day validation."""
        # Weekday
        weekday = datetime(2023, 1, 3).date()  # Tuesday
        self.assertTrue(self.frontier_manager.is_trading_day(weekday))
        
        # Weekend
        weekend = datetime(2023, 1, 7).date()  # Saturday
        self.assertFalse(self.frontier_manager.is_trading_day(weekend))
        
        # Holiday
        holiday = datetime(2023, 1, 1).date()  # New Year's Day
        self.assertFalse(self.frontier_manager.is_trading_day(holiday))
    
    def test_callback_scheduling(self):
        """Test callback scheduling functionality."""
        callback_executed = {"value": False}
        
        def test_callback():
            callback_executed["value"] = True
        
        # Schedule callback
        callback_time = datetime(2023, 1, 3, 10, 0, 0)
        callback_id = self.frontier_manager.schedule_callback(callback_time, test_callback)
        
        self.assertIsNotNone(callback_id)
        self.assertNotEqual(callback_id, "")
    
    def test_get_statistics(self):
        """Test getting frontier time manager statistics."""
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 12, 31)
        
        self.frontier_manager.initialize(start_time, end_time, Resolution.DAILY)
        
        stats = self.frontier_manager.get_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('current_frontier_time', stats)
        self.assertIn('start_time', stats)
        self.assertIn('end_time', stats)
        self.assertIn('slices_created', stats)


class TestQuantConnectCompatibilityLayer(unittest.TestCase):
    """Test QuantConnect compatibility layer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock()
        self.compatibility_layer = QuantConnectCompatibilityLayer(self.mock_data_manager)
    
    def test_pascal_case_methods(self):
        """Test PascalCase method aliases."""
        # Test AddEquity
        mock_symbol = Mock()
        self.mock_data_manager.add_equity.return_value = mock_symbol
        
        result = self.compatibility_layer.AddEquity("AAPL", Resolution.DAILY)
        
        self.mock_data_manager.add_equity.assert_called_with("AAPL", Resolution.DAILY)
        self.assertEqual(result, mock_symbol)
        
        # Test AddForex
        self.mock_data_manager.add_forex.return_value = mock_symbol
        
        result = self.compatibility_layer.AddForex("EURUSD", Resolution.DAILY)
        
        self.mock_data_manager.add_forex.assert_called_with("EURUSD", Resolution.DAILY)
        
        # Test AddCrypto
        self.mock_data_manager.add_crypto.return_value = mock_symbol
        
        result = self.compatibility_layer.AddCrypto("BTCUSD", Resolution.DAILY)
        
        self.mock_data_manager.add_crypto.assert_called_with("BTCUSD", Resolution.DAILY)
    
    def test_history_method(self):
        """Test History method alias."""
        mock_history = pd.DataFrame({'Close': [100, 101, 102]})
        self.mock_data_manager.history.return_value = mock_history
        
        result = self.compatibility_layer.History(["AAPL"], 10, Resolution.DAILY)
        
        self.mock_data_manager.history.assert_called_with(["AAPL"], 10, Resolution.DAILY)
        self.assertEqual(result.equals(mock_history), True)
    
    def test_time_property(self):
        """Test Time property."""
        test_time = datetime(2023, 1, 1, 10, 0, 0)
        self.mock_data_manager.get_frontier_time.return_value = test_time
        
        result = self.compatibility_layer.Time
        
        self.assertEqual(result, test_time)


class TestAlgorithmTimeCoordinator(unittest.TestCase):
    """Test algorithm time coordinator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_frontier_manager = Mock()
        self.mock_algorithm = Mock()
        
        self.time_coordinator = AlgorithmTimeCoordinator(
            self.mock_frontier_manager,
            self.mock_algorithm
        )
    
    def test_sync_algorithm_time(self):
        """Test algorithm time synchronization."""
        test_time = datetime(2023, 1, 1, 10, 0, 0)
        self.mock_frontier_manager.get_frontier_time.return_value = test_time
        
        self.time_coordinator.sync_algorithm_time()
        
        # Verify algorithm time was set
        self.assertEqual(self.mock_algorithm.time, test_time)
    
    def test_sync_callbacks(self):
        """Test sync callback functionality."""
        callback_executed = {"value": False, "time": None}
        
        def test_callback(time):
            callback_executed["value"] = True
            callback_executed["time"] = time
        
        # Add callback
        self.time_coordinator.add_sync_callback(test_callback)
        
        # Execute sync
        test_time = datetime(2023, 1, 1, 10, 0, 0)
        self.mock_frontier_manager.get_frontier_time.return_value = test_time
        
        self.time_coordinator.sync_algorithm_time()
        
        # Verify callback was executed
        self.assertTrue(callback_executed["value"])
        self.assertEqual(callback_executed["time"], test_time)


if __name__ == '__main__':
    unittest.main()