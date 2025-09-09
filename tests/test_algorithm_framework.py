"""
Unit tests for the QuantConnect-style algorithm framework.
Tests core functionality including symbols, securities, orders, portfolio management, and scheduling.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import the framework components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from application.services.misbuffet.algorithm.base import QCAlgorithm
from application.services.misbuffet.algorithm.symbol import Symbol, SymbolProperties
from application.services.misbuffet.algorithm.enums import (
    SecurityType, Resolution, OrderType, OrderStatus, OrderDirection
)
from application.services.misbuffet.algorithm.data_handlers import (
    BaseData, TradeBar, QuoteBar, Tick, Slice, TradeBars, QuoteBars
)
from application.services.misbuffet.algorithm.order import (
    Order, OrderTicket, MarketOrder, LimitOrder, OrderBuilder, create_order
)
from application.services.misbuffet.algorithm.security import (
    Security, Securities, SecurityHolding, SecurityPortfolioManager
)
from application.services.misbuffet.algorithm.scheduling import (
    ScheduleManager, DateRules, TimeRules, DayOfWeek
)
from application.services.misbuffet.algorithm.utils import AlgorithmUtilities


class TestSymbol(unittest.TestCase):
    """Test Symbol and SymbolProperties classes"""
    
    def test_symbol_creation(self):
        """Test basic symbol creation"""
        symbol = Symbol.create_equity("AAPL", "NASDAQ")
        
        self.assertEqual(symbol.value, "AAPL")
        self.assertEqual(symbol.security_type, SecurityType.EQUITY)
        self.assertEqual(symbol.market, "NASDAQ")
        self.assertTrue(symbol.is_equity)
        self.assertFalse(symbol.is_forex)
        self.assertFalse(symbol.is_crypto)
    
    def test_forex_symbol(self):
        """Test forex symbol creation"""
        symbol = Symbol.create_forex("EURUSD", "FXCM")
        
        self.assertEqual(symbol.value, "EURUSD")
        self.assertEqual(symbol.security_type, SecurityType.FOREX)
        self.assertTrue(symbol.is_forex)
        self.assertFalse(symbol.is_equity)
    
    def test_crypto_symbol(self):
        """Test crypto symbol creation"""
        symbol = Symbol.create_crypto("BTCUSD", "Bitfinex")
        
        self.assertEqual(symbol.value, "BTCUSD")
        self.assertEqual(symbol.security_type, SecurityType.CRYPTO)
        self.assertTrue(symbol.is_crypto)
    
    def test_symbol_properties(self):
        """Test SymbolProperties"""
        symbol = Symbol.create_equity("AAPL")
        props = SymbolProperties(symbol, lot_size=100, tick_size=0.01)
        
        self.assertEqual(props.symbol, symbol)
        self.assertEqual(props.lot_size, 100)
        self.assertEqual(props.tick_size, 0.01)
        self.assertTrue(props.is_tradable)
        self.assertEqual(props.get_minimum_order_size(), 100)
        
        # Test price rounding
        rounded_price = props.round_price_to_tick_size(123.456)
        self.assertEqual(rounded_price, 123.46)


class TestDataHandlers(unittest.TestCase):
    """Test data handling classes"""
    
    def setUp(self):
        """Set up test data"""
        self.symbol = Symbol.create_equity("AAPL")
        self.time = datetime(2023, 1, 1, 10, 0, 0)
    
    def test_trade_bar(self):
        """Test TradeBar creation and updates"""
        bar = TradeBar(
            symbol=self.symbol,
            time=self.time,
            end_time=self.time,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=10000
        )
        
        self.assertEqual(bar.symbol, self.symbol)
        self.assertEqual(bar.open, 100.0)
        self.assertEqual(bar.close, 103.0)
        self.assertEqual(bar.price, 103.0)  # Price should equal close
        self.assertEqual(bar.volume, 10000)
    
    def test_quote_bar(self):
        """Test QuoteBar creation"""
        quote_bar = QuoteBar(
            symbol=self.symbol,
            time=self.time,
            end_time=self.time,
            bid_close=100.0,
            ask_close=100.5
        )
        
        self.assertEqual(quote_bar.bid_close, 100.0)
        self.assertEqual(quote_bar.ask_close, 100.5)
        self.assertEqual(quote_bar.spread, 0.5)
        self.assertEqual(quote_bar.price, 100.25)  # Mid price
    
    def test_slice(self):
        """Test Slice data container"""
        slice_time = datetime(2023, 1, 1, 10, 0, 0)
        slice_data = Slice(time=slice_time)
        
        # Add trade bar
        bar = TradeBar(
            symbol=self.symbol,
            time=self.time,
            end_time=self.time,
            close=100.0
        )
        slice_data.bars[self.symbol] = bar
        
        # Test access methods
        self.assertTrue(slice_data.has_data)
        self.assertIn(self.symbol, slice_data)
        self.assertEqual(slice_data[self.symbol], bar)
        self.assertEqual(slice_data.get(self.symbol), bar)


class TestOrders(unittest.TestCase):
    """Test order management classes"""
    
    def setUp(self):
        """Set up test data"""
        self.symbol = Symbol.create_equity("AAPL")
    
    def test_market_order_creation(self):
        """Test market order creation"""
        order = MarketOrder(
            symbol=self.symbol,
            quantity=100,
            direction=OrderDirection.BUY
        )
        
        self.assertEqual(order.symbol, self.symbol)
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.order_type, OrderType.MARKET)
        self.assertTrue(order.is_buy)
        self.assertFalse(order.is_sell)
        self.assertEqual(order.abs_quantity, 100)
    
    def test_limit_order_creation(self):
        """Test limit order creation"""
        order = LimitOrder(
            symbol=self.symbol,
            quantity=-50,  # Sell order
            direction=OrderDirection.SELL,
            limit_price=105.0
        )
        
        self.assertEqual(order.quantity, -50)
        self.assertEqual(order.limit_price, 105.0)
        self.assertEqual(order.order_type, OrderType.LIMIT)
        self.assertTrue(order.is_sell)
        self.assertFalse(order.is_buy)
    
    def test_order_builder(self):
        """Test OrderBuilder pattern"""
        builder = create_order(self.symbol, 100)
        order = builder.as_limit_order(105.0).with_tag("test_order").build()
        
        self.assertIsInstance(order, LimitOrder)
        self.assertEqual(order.symbol, self.symbol)
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.limit_price, 105.0)
        self.assertEqual(order.tag, "test_order")
    
    def test_order_ticket(self):
        """Test OrderTicket functionality"""
        ticket = OrderTicket(
            symbol=self.symbol,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        self.assertEqual(ticket.quantity_remaining, 100)
        self.assertTrue(ticket.is_open)
        self.assertFalse(ticket.is_filled)
        
        # Test cancellation
        self.assertTrue(ticket.cancel())
        self.assertEqual(ticket.status, OrderStatus.CANCELED)
        self.assertFalse(ticket.is_open)


class TestSecurity(unittest.TestCase):
    """Test security and portfolio management"""
    
    def setUp(self):
        """Set up test data"""
        self.symbol = Symbol.create_equity("AAPL")
        self.security = Security(symbol=self.symbol)
    
    def test_security_creation(self):
        """Test Security creation"""
        self.assertEqual(self.security.symbol, self.symbol)
        self.assertEqual(self.security.price, 0.0)
        self.assertFalse(self.security.has_data)
    
    def test_security_data_update(self):
        """Test security data updates"""
        bar = TradeBar(
            symbol=self.symbol,
            time=datetime.now(),
            end_time=datetime.now(),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=10000
        )
        
        self.security.update(bar)
        
        self.assertEqual(self.security.price, 103.0)
        self.assertEqual(self.security.open, 100.0)
        self.assertEqual(self.security.close, 103.0)
        self.assertEqual(self.security.volume, 10000)
        self.assertTrue(self.security.has_data)
    
    def test_securities_collection(self):
        """Test Securities collection"""
        securities = Securities()
        security = securities.add(self.symbol, Resolution.MINUTE)
        
        self.assertIn(self.symbol, securities)
        self.assertEqual(securities[self.symbol], security)
        self.assertEqual(securities.get_by_ticker("AAPL"), security)
        self.assertTrue(securities.contains_key(self.symbol))
        self.assertTrue(securities.contains_key("AAPL"))


class TestPortfolio(unittest.TestCase):
    """Test portfolio management"""
    
    def setUp(self):
        """Set up test data"""
        self.symbol = Symbol.create_equity("AAPL")
        self.portfolio = SecurityPortfolioManager(cash=100000.0)
    
    def test_portfolio_initialization(self):
        """Test portfolio initialization"""
        self.assertEqual(self.portfolio.cash, 100000.0)
        self.assertEqual(self.portfolio.total_portfolio_value, 100000.0)
        self.assertFalse(self.portfolio.invested)
    
    def test_security_holding(self):
        """Test SecurityHolding"""
        holding = SecurityHolding(self.symbol)
        
        # Test initial state
        self.assertEqual(holding.quantity, 0)
        self.assertEqual(holding.market_value, 0.0)
        self.assertFalse(holding.is_invested)
        
        # Test adding transaction
        holding.add_transaction(100, 50.0, 1.0)  # Buy 100 shares at $50, $1 fee
        
        self.assertEqual(holding.quantity, 100)
        self.assertEqual(holding.average_price, 50.0)
        self.assertEqual(holding.total_fees, 1.0)
        self.assertTrue(holding.is_invested)
        self.assertTrue(holding.is_long)
        self.assertFalse(holding.is_short)
    
    def test_portfolio_processing_fill(self):
        """Test portfolio fill processing"""
        initial_cash = self.portfolio.cash
        
        # Process a buy order fill
        self.portfolio.process_fill(self.symbol, 100, 50.0, 1.0)
        
        # Check cash was deducted
        expected_cash = initial_cash - (100 * 50.0) - 1.0
        self.assertEqual(self.portfolio.cash, expected_cash)
        
        # Check holding was created
        holding = self.portfolio[self.symbol]
        self.assertEqual(holding.quantity, 100)
        self.assertEqual(holding.average_price, 50.0)
        
        # Test portfolio is now invested
        self.assertTrue(self.portfolio.invested)
        self.assertTrue(self.portfolio.is_invested(self.symbol))


class TestScheduling(unittest.TestCase):
    """Test scheduling system"""
    
    def test_schedule_manager(self):
        """Test basic scheduling functionality"""
        scheduler = ScheduleManager()
        
        # Mock function to schedule
        mock_func = Mock()
        
        # Schedule daily execution
        event_id = scheduler.schedule(
            mock_func,
            "test_event",
            DateRules.every_day(),
            TimeRules.at(9, 30)
        )
        
        self.assertIsNotNone(event_id)
        events = scheduler.get_scheduled_events()
        self.assertEqual(len(events), 1)
        
        # Test unscheduling
        self.assertTrue(scheduler.unschedule(event_id))
        events = scheduler.get_scheduled_events()
        self.assertEqual(len(events), 0)
    
    def test_date_rules(self):
        """Test DateRules"""
        # Test every day rule
        rule = DateRules.every_day()
        self.assertIn('frequency', rule)
        
        # Test week start rule
        rule = DateRules.week_start()
        self.assertIn('day_of_week', rule)
        self.assertEqual(rule['day_of_week'], DayOfWeek.MONDAY)
        
        # Test month start rule
        rule = DateRules.month_start()
        self.assertIn('day_of_month', rule)
        self.assertEqual(rule['day_of_month'], 1)
    
    def test_time_rules(self):
        """Test TimeRules"""
        # Test specific time
        rule = TimeRules.at(14, 30)
        self.assertIn('time_of_day', rule)
        
        # Test market open
        rule = TimeRules.market_open()
        self.assertIn('time_of_day', rule)
        
        # Test market close
        rule = TimeRules.market_close()
        self.assertIn('time_of_day', rule)


class TestAlgorithmUtilities(unittest.TestCase):
    """Test algorithm utility functions"""
    
    def test_percentage_change(self):
        """Test percentage change calculation"""
        change = AlgorithmUtilities.percentage_change(100.0, 110.0)
        self.assertEqual(change, 10.0)
        
        change = AlgorithmUtilities.percentage_change(100.0, 90.0)
        self.assertEqual(change, -10.0)
    
    def test_position_sizing(self):
        """Test position size calculation"""
        portfolio_value = 100000.0
        risk_percentage = 0.02  # 2%
        entry_price = 100.0
        stop_loss_price = 95.0
        
        position_size = AlgorithmUtilities.calculate_position_size(
            portfolio_value, risk_percentage, entry_price, stop_loss_price
        )
        
        # Expected: $2000 risk / $5 risk per share = 400 shares
        self.assertEqual(position_size, 400)
    
    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        returns = [0.01, 0.02, -0.01, 0.03, 0.005, -0.02, 0.015]
        sharpe = AlgorithmUtilities.sharpe_ratio(returns, 0.02)
        
        # Should return a reasonable Sharpe ratio
        self.assertIsInstance(sharpe, float)
    
    def test_max_drawdown(self):
        """Test max drawdown calculation"""
        values = [100000, 105000, 102000, 108000, 95000, 110000]
        max_dd = AlgorithmUtilities.max_drawdown(values)
        
        # Should be negative percentage
        self.assertLess(max_dd, 0.0)


class TestQCAlgorithm(unittest.TestCase):
    """Test main QCAlgorithm class"""
    
    def setUp(self):
        """Set up test algorithm"""
        self.algorithm = QCAlgorithm()
    
    def test_algorithm_initialization(self):
        """Test algorithm initialization"""
        self.assertIsNotNone(self.algorithm.securities)
        self.assertIsNotNone(self.algorithm.portfolio)
        self.assertIsNotNone(self.algorithm.schedule)
        self.assertIsNotNone(self.algorithm.logger)
        self.assertEqual(self.algorithm.portfolio.cash, 100000.0)
    
    def test_add_equity(self):
        """Test adding equity to algorithm"""
        security = self.algorithm.add_equity("AAPL", Resolution.DAILY)
        
        self.assertIsNotNone(security)
        self.assertEqual(security.symbol.value, "AAPL")
        self.assertEqual(security.resolution, Resolution.DAILY)
        self.assertIn(security.symbol, self.algorithm.securities)
    
    def test_market_order(self):
        """Test placing market order"""
        # First add a security
        self.algorithm.add_equity("AAPL")
        
        # Place market order
        ticket = self.algorithm.market_order("AAPL", 100)
        
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.quantity, 100)
        self.assertEqual(ticket.order_type, OrderType.MARKET)
        self.assertEqual(ticket.status, OrderStatus.SUBMITTED)
    
    def test_set_holdings(self):
        """Test set holdings functionality"""
        # Add security and set some price data
        security = self.algorithm.add_equity("AAPL")
        security.price = 150.0  # Set a price for calculation
        
        # Mock the market order method to avoid actual order placement
        with patch.object(self.algorithm, 'market_order') as mock_order:
            mock_ticket = Mock()
            mock_order.return_value = mock_ticket
            
            # Set holdings to 50% of portfolio
            self.algorithm.set_holdings("AAPL", 0.5)
            
            # Should have called market_order
            mock_order.assert_called_once()
    
    def test_liquidate(self):
        """Test liquidation functionality"""
        # Setup a position in the portfolio
        symbol = Symbol.create_equity("AAPL")
        self.algorithm.portfolio.process_fill(symbol, 100, 150.0)
        
        # Mock the market order method
        with patch.object(self.algorithm, 'market_order') as mock_order:
            mock_ticket = Mock()
            mock_order.return_value = mock_ticket
            
            # Liquidate the position
            tickets = self.algorithm.liquidate(symbol)
            
            # Should have placed a sell order
            self.assertEqual(len(tickets), 1)
            mock_order.assert_called_once_with(symbol, -100, tag="Liquidation")


if __name__ == '__main__':
    # Create test suite
    test_classes = [
        TestSymbol,
        TestDataHandlers,
        TestOrders,
        TestSecurity,
        TestPortfolio,
        TestScheduling,
        TestAlgorithmUtilities,
        TestQCAlgorithm
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"TESTS RUN: {result.testsRun}")
    print(f"FAILURES: {len(result.failures)}")
    print(f"ERRORS: {len(result.errors)}")
    print(f"SUCCESS RATE: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")