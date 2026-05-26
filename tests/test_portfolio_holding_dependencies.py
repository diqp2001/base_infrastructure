"""
Test file to validate the portfolio holding dependency chain implementation.

Tests the relationships between:
- PortfolioValueFactor -> CompanySharePortfolioPortfolioHolding
- CompanySharePortfolioPortfolioHoldingValueFactor -> CompanySharePortfolioHoldingValueFactor + Position
- CompanySharePortfolioHoldingValueFactor -> CompanySharePriceFactor + Position
- Position -> Transaction
"""

import unittest
from datetime import datetime, date
from decimal import Decimal

from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.domain.entities.finance.holding.position import Position, PositionType
from src.domain.entities.finance.transaction.transaction import Transaction, TransactionType, TransactionStatus
from src.domain.entities.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHolding

# Factor imports
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor import CompanySharePortfolioPortfolioHoldingValueFactor
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor


class TestPortfolioHoldingDependencies(unittest.TestCase):
    """Test the portfolio holding dependency chain."""

    def setUp(self):
        """Set up test data."""
        # Create a transaction
        self.transaction = Transaction(
            id=1,
            portfolio_id=1,
            holding_id=1,
            order_id=1,
            date=datetime.now(),
            transaction_type=TransactionType.MARKET_ORDER,
            transaction_id="TXN-001",
            account_id="ACC-001",
            trade_date=date.today(),
            value_date=date.today(),
            settlement_date=date.today(),
            status=TransactionStatus.EXECUTED,
            spread=0.01,
            currency_id=1,
            exchange_id=1
        )

        # Create a position that depends on transaction
        self.position = Position(
            id=1,
            quantity=100,
            position_type=PositionType.LONG,
            asset_id=1,
            transactions=[self.transaction]
        )

        # Create portfolios
        self.main_portfolio = Portfolio(
            id=1,
            name="Main Portfolio",
            start_date=date.today()
        )
        
        self.company_share_portfolio = CompanySharePortfolio(
            id=2,
            name="Tech Stocks Portfolio",
            start_date=date.today()
        )

        # Create the portfolio holding
        self.portfolio_holding = CompanySharePortfolioPortfolioHolding(
            id=1,
            portfolio=self.main_portfolio,
            company_share_portfolio=self.company_share_portfolio,
            position=self.position,
            start_date=datetime.now()
        )

    def test_position_depends_on_transaction(self):
        """Test that Position depends on Transaction."""
        self.assertTrue(self.position.has_transactions())
        self.assertEqual(len(self.position.transactions), 1)
        self.assertEqual(self.position.transactions[0], self.transaction)

    def test_company_share_portfolio_holding_value_factor_dependencies(self):
        """Test CompanySharePortfolioHoldingValueFactor dependencies."""
        factor = CompanySharePortfolioHoldingValueFactor()
        dependencies = factor.get_dependencies()
        
        self.assertIn("company_share_mid_price_factor", dependencies)
        self.assertIn("position", dependencies)

    def test_company_share_portfolio_holding_value_factor_calculation(self):
        """Test CompanySharePortfolioHoldingValueFactor calculation."""
        factor = CompanySharePortfolioHoldingValueFactor()
        
        # Mock dependencies
        dependencies = {
            'company_share_price_factor': Decimal('150.00'),  # Price per share
            'position': self.position  # 100 shares
        }
        
        result = factor.calculate(dependencies)
        expected = Decimal('150.00') * Decimal('100')  # 15,000
        
        self.assertEqual(result, expected)

    def test_company_share_portfolio_portfolio_holding_value_factor_dependencies(self):
        """Test CompanySharePortfolioPortfolioHoldingValueFactor dependencies."""
        factor = CompanySharePortfolioPortfolioHoldingValueFactor()
        dependencies = factor.get_dependencies()
        
        self.assertIn("company_share_portfolio_holding_value_factor", dependencies)
        self.assertIn("position", dependencies)

    def test_company_share_portfolio_portfolio_holding_value_factor_calculation(self):
        """Test CompanySharePortfolioPortfolioHoldingValueFactor calculation."""
        factor = CompanySharePortfolioPortfolioHoldingValueFactor()
        
        # Mock dependencies
        dependencies = {
            'company_share_portfolio_value': Decimal('50000.00'),  # Portfolio value
            'position': self.position  # Quantity of portfolios held
        }
        
        result = factor.calculate(dependencies)
        expected = Decimal('50000.00') * Decimal('100')  # 5,000,000
        
        self.assertEqual(result, expected)

    def test_portfolio_value_factor_dependencies(self):
        """Test PortfolioValueFactor dependencies."""
        factor = PortfolioValueFactor("Test Portfolio Value")
        dependencies = factor.get_dependencies()
        
        self.assertIn("company_share_portfolio_portfolio_holding_value_factor", dependencies)
        self.assertIn("company_share_holding_value_factor", dependencies)

    def test_portfolio_supports_all_holding_types(self):
        """Test that Portfolio can support all holding types."""
        # Add the holding to the main portfolio
        self.main_portfolio.add_holding(self.portfolio_holding)
        
        self.assertTrue(self.main_portfolio.has_holdings())
        self.assertEqual(self.main_portfolio.holding_count(), 1)
        
        # Test filtering by type
        portfolio_holdings = self.main_portfolio.get_holdings_by_type("CompanySharePortfolioPortfolioHolding")
        self.assertEqual(len(portfolio_holdings), 1)
        self.assertEqual(portfolio_holdings[0], self.portfolio_holding)

    def test_dependency_chain_integration(self):
        """Test the complete dependency chain integration."""
        # This tests the conceptual flow:
        # Transaction -> Position -> CompanySharePortfolioHoldingValueFactor -> 
        # CompanySharePortfolioPortfolioHoldingValueFactor -> PortfolioValueFactor
        
        # 1. Position depends on Transaction
        self.assertTrue(self.position.has_transactions())
        
        # 2. CompanySharePortfolioHoldingValueFactor uses position and price
        holding_value_factor = CompanySharePortfolioHoldingValueFactor()
        holding_deps = {
            'company_share_price_factor': Decimal('100.00'),
            'position': self.position
        }
        holding_value = holding_value_factor.calculate(holding_deps)
        
        # 3. CompanySharePortfolioPortfolioHoldingValueFactor uses holding value and position
        portfolio_holding_factor = CompanySharePortfolioPortfolioHoldingValueFactor()
        portfolio_holding_deps = {
            'company_share_portfolio_value': holding_value,
            'position': self.position
        }
        portfolio_holding_value = portfolio_holding_factor.calculate(portfolio_holding_deps)
        
        # 4. PortfolioValueFactor aggregates all holding values
        portfolio_factor = PortfolioValueFactor("Test Portfolio")
        portfolio_deps = {
            'company_share_portfolio_portfolio_holding_value_factor': portfolio_holding_value
        }
        portfolio_value = portfolio_factor.calculate(portfolio_deps)
        
        # Verify the chain works
        self.assertGreater(holding_value, Decimal('0'))
        self.assertGreater(portfolio_holding_value, Decimal('0'))
        self.assertGreater(portfolio_value, Decimal('0'))
        self.assertEqual(portfolio_value, portfolio_holding_value)


if __name__ == '__main__':
    unittest.main()