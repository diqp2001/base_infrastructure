"""
tests/test_company_share_option_mid_price_factor.py

Comprehensive tests for CompanyShareOptionMidPriceFactor and related components.
"""

import unittest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, MagicMock

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor


class TestCompanyShareOptionMidPriceFactor(unittest.TestCase):
    """Test cases for CompanyShareOptionMidPriceFactor domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.factor = CompanyShareOptionMidPriceFactor(
            outlier_threshold=2.0,
            min_sources=2
        )
        
        self.sample_option_prices = [
            {
                'source': 'ibkr',
                'price': Decimal('5.50'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'fmp',
                'price': Decimal('5.75'),
                'timestamp': datetime.now(),
                'group': 'price', 
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'yahoo',
                'price': Decimal('5.60'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]

    def test_factor_initialization(self):
        """Test factor initialization with default values."""
        factor = CompanyShareOptionMidPriceFactor()
        
        self.assertEqual(factor.name, "mid_price")
        self.assertEqual(factor.group, "price")
        self.assertEqual(factor.subgroup, "mid_price_true")
        self.assertEqual(factor.data_type, "decimal")
        self.assertEqual(factor.source, "multiple")
        self.assertEqual(factor.outlier_threshold, 2.0)
        self.assertEqual(factor.min_sources, 2)

    def test_factor_initialization_custom_values(self):
        """Test factor initialization with custom values."""
        factor = CompanyShareOptionMidPriceFactor(
            name="custom_option_mid_price",
            outlier_threshold=1.5,
            min_sources=3
        )
        
        self.assertEqual(factor.name, "custom_option_mid_price")
        self.assertEqual(factor.outlier_threshold, 1.5)
        self.assertEqual(factor.min_sources, 3)

    def test_calculate_with_sufficient_sources(self):
        """Test calculation with sufficient data sources."""
        result = self.factor.calculate(self.sample_option_prices)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Decimal)
        
        # Expected average: (5.50 + 5.75 + 5.60) / 3 = 5.616...
        expected = Decimal('5.50') + Decimal('5.75') + Decimal('5.60')
        expected = expected / 3
        self.assertEqual(result, expected)

    def test_calculate_with_insufficient_sources(self):
        """Test calculation with insufficient data sources."""
        single_price = [self.sample_option_prices[0]]
        result = self.factor.calculate(single_price)
        
        self.assertIsNone(result)

    def test_calculate_with_empty_sources(self):
        """Test calculation with empty source list."""
        result = self.factor.calculate([])
        
        self.assertIsNone(result)

    def test_calculate_with_none_sources(self):
        """Test calculation with None sources."""
        result = self.factor.calculate(None)
        
        self.assertIsNone(result)

    def test_filter_same_group_subgroup(self):
        """Test filtering by same group and subgroup."""
        mixed_prices = self.sample_option_prices + [
            {
                'source': 'other',
                'price': Decimal('10.00'),
                'timestamp': datetime.now(),
                'group': 'greek',  # Different group
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'another',
                'price': Decimal('15.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'high',  # Different subgroup
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]
        
        filtered = self.factor._filter_same_group_subgroup(mixed_prices)
        
        self.assertEqual(len(filtered), 3)  # Only the original 3 should remain
        for price in filtered:
            self.assertEqual(price['group'], 'price')
            self.assertEqual(price['subgroup'], 'mid_price_true')

    def test_remove_outliers_no_outliers(self):
        """Test outlier removal when no outliers exist."""
        valid_prices = self.factor._remove_outliers(self.sample_option_prices)
        
        self.assertEqual(len(valid_prices), 3)
        self.assertEqual(valid_prices, self.sample_option_prices)

    def test_remove_outliers_with_outliers(self):
        """Test outlier removal when outliers exist."""
        prices_with_outlier = self.sample_option_prices + [
            {
                'source': 'outlier_source',
                'price': Decimal('20.00'),  # Significantly higher than others
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]
        
        valid_prices = self.factor._remove_outliers(prices_with_outlier)
        
        # Should remove the outlier but keep the original prices
        self.assertEqual(len(valid_prices), 3)
        self.assertNotIn(prices_with_outlier[-1], valid_prices)

    def test_remove_outliers_too_few_prices(self):
        """Test outlier removal with too few prices."""
        two_prices = self.sample_option_prices[:2]
        valid_prices = self.factor._remove_outliers(two_prices)
        
        # Should return all prices when there are 2 or fewer
        self.assertEqual(len(valid_prices), 2)
        self.assertEqual(valid_prices, two_prices)

    def test_calculate_average_price(self):
        """Test average price calculation."""
        average = self.factor._calculate_average_price(self.sample_option_prices)
        
        expected = (Decimal('5.50') + Decimal('5.75') + Decimal('5.60')) / 3
        self.assertEqual(average, expected)

    def test_get_dependencies(self):
        """Test factor dependencies."""
        dependencies = self.factor.get_dependencies()
        
        expected_sources = ["ibkr", "fmp", "yahoo", "alpha_vantage", "quandl"]
        expected_deps = [f"company_share_option_price_{source}" for source in expected_sources]
        
        self.assertEqual(dependencies, expected_deps)

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.factor)
        expected = "CompanyShareOptionMidPriceFactor(name=mid_price, group=price, subgroup=mid_price_true)"
        self.assertEqual(repr_str, expected)

    def test_calculate_integration_with_outlier_removal(self):
        """Test full calculation pipeline including outlier removal."""
        prices_with_outlier = [
            {
                'source': 'source1',
                'price': Decimal('5.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'source2',
                'price': Decimal('5.10'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'outlier',
                'price': Decimal('15.00'),  # Clear outlier
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'source3',
                'price': Decimal('4.90'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]
        
        result = self.factor.calculate(prices_with_outlier)
        
        # Should calculate average without the outlier
        # Expected: (5.00 + 5.10 + 4.90) / 3 = 5.00
        self.assertIsNotNone(result)
        expected = (Decimal('5.00') + Decimal('5.10') + Decimal('4.90')) / 3
        self.assertAlmostEqual(float(result), float(expected), places=2)

    def test_different_groups_filtered_out(self):
        """Test that prices with different groups are filtered out."""
        mixed_group_prices = [
            {
                'source': 'good1',
                'price': Decimal('5.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'bad1',
                'price': Decimal('0.25'),
                'timestamp': datetime.now(),
                'group': 'greek',  # Wrong group
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            },
            {
                'source': 'good2',
                'price': Decimal('5.20'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true',
                'strike': Decimal('100.00'),
                'expiry': date(2024, 12, 20)
            }
        ]
        
        result = self.factor.calculate(mixed_group_prices)
        
        # Should average only the 2 valid prices
        expected = (Decimal('5.00') + Decimal('5.20')) / 2
        self.assertEqual(result, expected)

    def test_option_specific_attributes(self):
        """Test that option-specific attributes are handled correctly."""
        option_price = {
            'source': 'test_source',
            'price': Decimal('5.50'),
            'timestamp': datetime.now(),
            'group': 'price',
            'subgroup': 'mid_price_true',
            'strike': Decimal('105.00'),  # Different strike
            'expiry': date(2024, 6, 21)   # Different expiry
        }
        
        # The factor should still work with option-specific attributes
        prices = [option_price, self.sample_option_prices[0]]
        result = self.factor.calculate(prices)
        
        self.assertIsNotNone(result)
        expected = (Decimal('5.50') + Decimal('5.50')) / 2
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()