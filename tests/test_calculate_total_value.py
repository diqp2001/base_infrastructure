import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal

from src.application.services.portfolio_service.portfolio_service import PortfolioService


class TestCalculateTotalValue(unittest.TestCase):
    """Test cases for the calculate_total_value function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()
        self.mock_session = Mock()
        self.mock_db_service.session = self.mock_session
        self.portfolio_service = PortfolioService(database_service=self.mock_db_service)

    def test_calculate_total_value_basic(self):
        """Test basic calculation with quantity × mid_price approach."""
        # Mock list_portfolios
        mock_portfolios = [
            {'id': 1, 'name': 'Portfolio 1'},
            {'id': 2, 'name': 'Portfolio 2'}
        ]
        
        # Mock calculate_portfolio_value
        mock_portfolio_values = [
            {
                'total_portfolio_value': 10000.0,
                'current_cash': 2000.0,
                'total_market_value': 8000.0
            },
            {
                'total_portfolio_value': 15000.0,
                'current_cash': 3000.0,
                'total_market_value': 12000.0
            }
        ]
        
        # Mock calculate_holding_total_value
        mock_holdings_data = {
            'holdings': {'count': 10, 'total_market_value': 20000.0, 'details': []},
            'positions': {'count': 5, 'total_market_value': 0.0, 'details': []},
            'total_holdings_value': 20000.0,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', side_effect=mock_portfolio_values):
                with patch.object(self.portfolio_service, 'calculate_holding_total_value', return_value=mock_holdings_data):
                    # Mock database queries for orders, transactions, accounts
                    self.mock_session.execute.side_effect = [
                        # Orders query (exception case)
                        Exception("Table not found"),
                        # Transactions query (exception case)  
                        Exception("Table not found"),
                        # Accounts query (exception case)
                        Exception("Table not found")
                    ]
                    
                    result = self.portfolio_service.calculate_total_value()
                    
                    # Verify result structure
                    self.assertIn('total_value', result)
                    self.assertIn('portfolios', result)
                    self.assertIn('holdings', result)
                    self.assertIn('positions', result)
                    self.assertIn('orders', result)
                    self.assertIn('transactions', result)
                    self.assertIn('accounts', result)
                    self.assertIn('calculation_timestamp', result)
                    
                    # Verify portfolio calculations (now depends on holdings)
                    self.assertEqual(result['portfolios']['count'], 2)
                    self.assertEqual(result['portfolios']['cash'], 5000.0)  # Cash from portfolios
                    self.assertEqual(result['portfolios']['market_value'], 20000.0)  # From holdings calculation
                    self.assertEqual(result['portfolios']['total_value'], 25000.0)  # Cash + market value
                    
                    # Verify holdings calculations
                    self.assertEqual(result['holdings']['count'], 10)
                    self.assertEqual(result['holdings']['total_market_value'], 20000.0)
                    
                    # Verify positions included
                    self.assertEqual(result['positions']['count'], 5)

    def test_calculate_total_value_with_all_entities(self):
        """Test calculation with all entity types present."""
        # Mock portfolios
        mock_portfolios = [{'id': 1, 'name': 'Portfolio 1'}]
        mock_portfolio_value = {
            'total_portfolio_value': 10000.0,
            'current_cash': 2000.0,
            'total_market_value': 8000.0
        }
        
        # Mock holdings calculation
        mock_holdings_data = {
            'holdings': {'count': 5, 'total_market_value': 8000.0, 'details': []},
            'positions': {'count': 3, 'total_market_value': 0.0, 'details': []},
            'total_holdings_value': 8000.0,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=mock_portfolio_value):
                with patch.object(self.portfolio_service, 'calculate_holding_total_value', return_value=mock_holdings_data):
                    # Mock successful database queries
                    self.mock_session.execute.side_effect = [
                        # Orders query
                        MagicMock(fetchone=MagicMock(return_value=(3, 1500.0))),
                        # Transactions query
                        MagicMock(fetchone=MagicMock(return_value=(8, 500.0))),
                        # Accounts query
                        MagicMock(fetchone=MagicMock(return_value=(2, 3000.0)))
                    ]
                    
                    result = self.portfolio_service.calculate_total_value()
                    
                    # Verify all entities are counted
                    self.assertEqual(result['portfolios']['count'], 1)
                    self.assertEqual(result['holdings']['count'], 5)
                    self.assertEqual(result['positions']['count'], 3)
                    self.assertEqual(result['orders']['count'], 3)
                    self.assertEqual(result['transactions']['count'], 8)
                    self.assertEqual(result['accounts']['count'], 2)
                    
                    # Verify total value calculation (portfolios + orders + accounts)
                    # Note: transactions are historical, not added to current value
                    portfolio_total = 2000.0 + 8000.0  # cash + market_value from holdings
                    expected_total = portfolio_total + 1500.0 + 3000.0
                    self.assertEqual(result['total_value'], expected_total)

    def test_calculate_total_value_empty_data(self):
        """Test calculation with no data."""
        # Mock empty holdings data
        mock_empty_holdings = {
            'holdings': {'count': 0, 'total_market_value': 0.0, 'details': []},
            'positions': {'count': 0, 'total_market_value': 0.0, 'details': []},
            'total_holdings_value': 0.0,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=[]):
            with patch.object(self.portfolio_service, 'calculate_holding_total_value', return_value=mock_empty_holdings):
                # Mock database queries returning zero/None
                self.mock_session.execute.side_effect = [
                    # Orders query (exception case)
                    Exception("Table not found"),
                    # Transactions query (exception case)
                    Exception("Table not found"),
                    # Accounts query (exception case)
                    Exception("Table not found")
                ]
                
                result = self.portfolio_service.calculate_total_value()
                
                # Verify zero values
                self.assertEqual(result['total_value'], 0.0)
                self.assertEqual(result['portfolios']['count'], 0)
                self.assertEqual(result['portfolios']['total_value'], 0.0)
                self.assertEqual(result['holdings']['count'], 0)
                self.assertEqual(result['holdings']['total_market_value'], 0.0)
                self.assertEqual(result['positions']['count'], 0)

    def test_calculate_total_value_error_handling(self):
        """Test error handling in calculate_total_value."""
        with patch.object(self.portfolio_service, 'list_portfolios', side_effect=Exception("Database error")):
            result = self.portfolio_service.calculate_total_value()
            
            # Verify error is handled gracefully
            self.assertIn('error', result)
            self.assertEqual(result['total_value'], 0.0)
            self.assertIn('calculation_timestamp', result)

    def test_calculate_total_value_none_portfolio_value(self):
        """Test handling when calculate_portfolio_value returns None."""
        mock_portfolios = [{'id': 1, 'name': 'Portfolio 1'}]
        
        # Mock empty holdings data
        mock_empty_holdings = {
            'holdings': {'count': 0, 'total_market_value': 0.0, 'details': []},
            'positions': {'count': 0, 'total_market_value': 0.0, 'details': []},
            'total_holdings_value': 0.0,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=None):
                with patch.object(self.portfolio_service, 'calculate_holding_total_value', return_value=mock_empty_holdings):
                    # Mock database queries
                    self.mock_session.execute.side_effect = [
                        Exception("Orders table not found"),
                        Exception("Transactions table not found"),
                        Exception("Accounts table not found")
                    ]
                    
                    result = self.portfolio_service.calculate_total_value()
                    
                    # Should handle None gracefully
                    self.assertEqual(result['portfolios']['count'], 1)
                    self.assertEqual(result['portfolios']['total_value'], 0.0)

    def test_calculate_total_value_decimal_handling(self):
        """Test proper handling of Decimal types in calculations."""
        mock_portfolios = [{'id': 1, 'name': 'Portfolio 1'}]
        mock_portfolio_value = {
            'total_portfolio_value': Decimal('10000.50'),
            'current_cash': Decimal('2000.25'),
            'total_market_value': Decimal('8000.25')
        }
        
        # Mock holdings data with decimal values
        mock_holdings_data = {
            'holdings': {'count': 1, 'total_market_value': 8000.25, 'details': []},
            'positions': {'count': 0, 'total_market_value': 0.0, 'details': []},
            'total_holdings_value': 8000.25,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=mock_portfolio_value):
                with patch.object(self.portfolio_service, 'calculate_holding_total_value', return_value=mock_holdings_data):
                    # Mock database queries
                    self.mock_session.execute.side_effect = [
                        Exception("Orders table not found"),
                        Exception("Transactions table not found"), 
                        Exception("Accounts table not found")
                    ]
                    
                    result = self.portfolio_service.calculate_total_value()
                    
                    # Verify Decimal values are handled correctly
                    expected_portfolio_total = 2000.25 + 8000.25  # cash + market_value from holdings
                    self.assertEqual(result['portfolios']['total_value'], expected_portfolio_total)
                    self.assertEqual(result['portfolios']['cash'], 2000.25)
                    self.assertEqual(result['portfolios']['market_value'], 8000.25)
                    self.assertEqual(result['holdings']['total_market_value'], 8000.25)


    def test_calculate_holding_total_value(self):
        """Test the new calculate_holding_total_value method."""
        # Mock holdings query results
        mock_holdings_results = [
            (1, 101, 1, 50, datetime.now(), None, 'AAPL', 'Apple Inc.'),
            (2, 102, 1, 25, datetime.now(), None, 'GOOGL', 'Alphabet Inc.'),
        ]
        
        # Mock positions query results
        mock_positions_results = [
            (1, 1, 100, 'LONG'),
            (2, 1, 50, 'SHORT'),
        ]
        
        # Mock database queries
        self.mock_session.execute.side_effect = [
            # Holdings query
            MagicMock(fetchall=MagicMock(return_value=mock_holdings_results)),
            # Positions query  
            MagicMock(fetchall=MagicMock(return_value=mock_positions_results))
        ]
        
        # Mock mid price lookup
        with patch.object(self.portfolio_service, '_get_asset_mid_price', side_effect=[150.0, 2800.0]):
            result = self.portfolio_service.calculate_holding_total_value()
            
            # Verify structure
            self.assertIn('holdings', result)
            self.assertIn('positions', result)
            self.assertIn('total_holdings_value', result)
            
            # Verify holdings calculations
            self.assertEqual(result['holdings']['count'], 2)
            expected_total = (50 * 150.0) + (25 * 2800.0)  # 7500 + 70000 = 77500
            self.assertEqual(result['holdings']['total_market_value'], expected_total)
            self.assertEqual(result['total_holdings_value'], expected_total)
            
            # Verify details
            self.assertEqual(len(result['holdings']['details']), 2)
            self.assertEqual(result['holdings']['details'][0]['quantity'], 50)
            self.assertEqual(result['holdings']['details'][0]['mid_price'], 150.0)
            self.assertEqual(result['holdings']['details'][0]['market_value'], 7500.0)

    def test_get_asset_mid_price(self):
        """Test the _get_asset_mid_price method."""
        # Mock successful price query
        self.mock_session.execute.return_value.fetchone.return_value = (150.75,)
        
        price = self.portfolio_service._get_asset_mid_price(101)
        self.assertEqual(price, 150.75)
        
        # Mock no price found (None result)
        self.mock_session.execute.return_value.fetchone.return_value = None
        
        price = self.portfolio_service._get_asset_mid_price(102)
        self.assertEqual(price, 100.0)  # Default fallback price
        
        # Mock database error
        self.mock_session.execute.side_effect = Exception("Database error")
        
        price = self.portfolio_service._get_asset_mid_price(103)
        self.assertEqual(price, 100.0)  # Default fallback price


if __name__ == '__main__':
    unittest.main()