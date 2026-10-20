"""
Basic test for the new trading factors (Position, Transaction, Order).
Tests the domain entities and their calculate methods.
"""

import unittest
from decimal import Decimal
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor


class TestTradingFactors(unittest.TestCase):
    """Test suite for trading factor domain entities."""
    
    def test_order_quantity_factor_creation(self):
        """Test creation of order quantity factor."""
        factor = CompanyShareOrderQuantityFactor(
            name="test_order_quantity",
            group="order",
            subgroup="quantity",
            data_type="numeric"
        )
        
        self.assertEqual(factor.name, "test_order_quantity")
        self.assertEqual(factor.group, "order")
        self.assertEqual(factor.subgroup, "quantity")
        self.assertEqual(factor.data_type, "numeric")
    
    def test_order_price_factor_creation(self):
        """Test creation of order price factor."""
        factor = CompanyShareOrderPriceFactor(
            name="test_order_price",
            group="order",
            subgroup="price",
            data_type="decimal"
        )
        
        self.assertEqual(factor.name, "test_order_price")
        self.assertEqual(factor.group, "order")
        self.assertEqual(factor.subgroup, "price")
        self.assertEqual(factor.data_type, "decimal")
    
    def test_transaction_value_factor_creation(self):
        """Test creation of transaction value factor."""
        factor = CompanyShareTransactionValueFactor(
            name="test_transaction_value",
            group="transaction",
            subgroup="value",
            data_type="decimal"
        )
        
        self.assertEqual(factor.name, "test_transaction_value")
        self.assertEqual(factor.group, "transaction")
        self.assertEqual(factor.subgroup, "value")
        self.assertEqual(factor.data_type, "decimal")
    
    def test_transaction_value_calculation(self):
        """Test transaction value calculation (quantity × price)."""
        factor = CompanyShareTransactionValueFactor()
        
        # Mock factor values: quantity=100, price=50.25
        order_values = [Decimal('100'), Decimal('50.25')]
        result = factor.calculate(order_values)
        
        expected = Decimal('100') * Decimal('50.25')  # 5025.00
        self.assertEqual(result, expected)
    
    def test_transaction_value_calculation_insufficient_values(self):
        """Test transaction value calculation with insufficient values."""
        factor = CompanyShareTransactionValueFactor()
        
        # Only one value provided (need quantity and price)
        order_values = [Decimal('100')]
        result = factor.calculate(order_values)
        
        # Should return 0 when insufficient values
        self.assertEqual(result, Decimal('0'))
    
    def test_position_value_factor_creation(self):
        """Test creation of position value factor."""
        factor = CompanySharePositionValueFactor(
            name="test_position_value",
            group="position",
            subgroup="value",
            data_type="decimal"
        )
        
        self.assertEqual(factor.name, "test_position_value")
        self.assertEqual(factor.group, "position")
        self.assertEqual(factor.subgroup, "value")
        self.assertEqual(factor.data_type, "decimal")
    
    def test_position_value_calculation(self):
        """Test position value calculation (sum of transaction values)."""
        factor = CompanySharePositionValueFactor()
        
        # Mock transaction values
        transaction_values = [Decimal('5025.00'), Decimal('2500.75'), Decimal('1000.25')]
        result = factor.calculate(transaction_values)
        
        expected = Decimal('5025.00') + Decimal('2500.75') + Decimal('1000.25')  # 8526.00
        self.assertEqual(result, expected)
    
    def test_position_value_calculation_empty(self):
        """Test position value calculation with empty transaction list."""
        factor = CompanySharePositionValueFactor()
        
        transaction_values = []
        result = factor.calculate(transaction_values)
        
        # Should return 0 for empty list
        self.assertEqual(result, Decimal('0'))


if __name__ == '__main__':
    unittest.main()