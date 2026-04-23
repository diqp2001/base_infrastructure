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
        """Test basic calculation with portfolios only."""
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
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', side_effect=mock_portfolio_values):
                # Mock database queries
                self.mock_session.execute.side_effect = [
                    # Holdings query
                    MagicMock(fetchone=MagicMock(return_value=(10, 20000.0))),
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
                self.assertIn('orders', result)
                self.assertIn('transactions', result)
                self.assertIn('accounts', result)
                self.assertIn('calculation_timestamp', result)
                
                # Verify portfolio calculations
                self.assertEqual(result['portfolios']['count'], 2)
                self.assertEqual(result['portfolios']['total_value'], 25000.0)
                self.assertEqual(result['portfolios']['cash'], 5000.0)
                self.assertEqual(result['portfolios']['market_value'], 20000.0)
                
                # Verify holdings calculations
                self.assertEqual(result['holdings']['count'], 10)
                self.assertEqual(result['holdings']['total_market_value'], 20000.0)

    def test_calculate_total_value_with_all_entities(self):
        """Test calculation with all entity types present."""
        # Mock portfolios
        mock_portfolios = [{'id': 1, 'name': 'Portfolio 1'}]
        mock_portfolio_value = {
            'total_portfolio_value': 10000.0,
            'current_cash': 2000.0,
            'total_market_value': 8000.0
        }
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=mock_portfolio_value):
                # Mock successful database queries
                self.mock_session.execute.side_effect = [
                    # Holdings query
                    MagicMock(fetchone=MagicMock(return_value=(5, 8000.0))),
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
                self.assertEqual(result['orders']['count'], 3)
                self.assertEqual(result['transactions']['count'], 8)
                self.assertEqual(result['accounts']['count'], 2)
                
                # Verify total value calculation
                expected_total = 10000.0 + 1500.0 + 500.0 + 3000.0
                self.assertEqual(result['total_value'], expected_total)

    def test_calculate_total_value_empty_data(self):
        """Test calculation with no data."""
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=[]):
            # Mock database queries returning zero/None
            self.mock_session.execute.side_effect = [
                # Holdings query
                MagicMock(fetchone=MagicMock(return_value=(0, None))),
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
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=None):
                # Mock holdings query
                self.mock_session.execute.side_effect = [
                    MagicMock(fetchone=MagicMock(return_value=(0, 0.0))),
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
        
        with patch.object(self.portfolio_service, 'list_portfolios', return_value=mock_portfolios):
            with patch.object(self.portfolio_service, 'calculate_portfolio_value', return_value=mock_portfolio_value):
                # Mock database queries
                self.mock_session.execute.side_effect = [
                    MagicMock(fetchone=MagicMock(return_value=(1, 8000.25))),
                    Exception("Orders table not found"),
                    Exception("Transactions table not found"), 
                    Exception("Accounts table not found")
                ]
                
                result = self.portfolio_service.calculate_total_value()
                
                # Verify Decimal values are handled correctly
                self.assertEqual(result['portfolios']['total_value'], 10000.50)
                self.assertEqual(result['portfolios']['cash'], 2000.25)
                self.assertEqual(result['portfolios']['market_value'], 8000.25)
                self.assertEqual(result['holdings']['total_market_value'], 8000.25)


if __name__ == '__main__':
    unittest.main()