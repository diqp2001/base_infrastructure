"""
tests/test_company_share_mid_price_factor.py

Comprehensive tests for CompanyShareMidPriceFactor and related components.
"""

import unittest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, MagicMock

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor


class TestCompanyShareMidPriceFactor(unittest.TestCase):
    """Test cases for CompanyShareMidPriceFactor domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.factor = CompanyShareMidPriceFactor(
            outlier_threshold=2.0,
            min_sources=2
        )
        
        self.sample_prices = [
            {
                'source': 'ibkr',
                'price': Decimal('100.50'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'fmp',
                'price': Decimal('100.75'),
                'timestamp': datetime.now(),
                'group': 'price', 
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'yahoo',
                'price': Decimal('100.60'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            }
        ]

    def test_factor_initialization(self):
        """Test factor initialization with default values."""
        factor = CompanyShareMidPriceFactor()
        
        self.assertEqual(factor.name, "mid_price")
        self.assertEqual(factor.group, "price")
        self.assertEqual(factor.subgroup, "mid_price_true")
        self.assertEqual(factor.data_type, "decimal")
        self.assertEqual(factor.source, "multiple")
        self.assertEqual(factor.outlier_threshold, 2.0)
        self.assertEqual(factor.min_sources, 2)

    def test_factor_initialization_custom_values(self):
        """Test factor initialization with custom values."""
        factor = CompanyShareMidPriceFactor(
            name="custom_mid_price",
            outlier_threshold=1.5,
            min_sources=3
        )
        
        self.assertEqual(factor.name, "custom_mid_price")
        self.assertEqual(factor.outlier_threshold, 1.5)
        self.assertEqual(factor.min_sources, 3)

    def test_calculate_with_sufficient_sources(self):
        """Test calculation with sufficient data sources."""
        result = self.factor.calculate(self.sample_prices)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Decimal)
        
        # Expected average: (100.50 + 100.75 + 100.60) / 3 = 100.616...
        expected = Decimal('100.50') + Decimal('100.75') + Decimal('100.60')
        expected = expected / 3
        self.assertEqual(result, expected)

    def test_calculate_with_insufficient_sources(self):
        """Test calculation with insufficient data sources."""
        single_price = [self.sample_prices[0]]
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
        mixed_prices = self.sample_prices + [
            {
                'source': 'other',
                'price': Decimal('200.00'),
                'timestamp': datetime.now(),
                'group': 'volume',  # Different group
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'another',
                'price': Decimal('300.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'high'  # Different subgroup
            }
        ]
        
        filtered = self.factor._filter_same_group_subgroup(mixed_prices)
        
        self.assertEqual(len(filtered), 3)  # Only the original 3 should remain
        for price in filtered:
            self.assertEqual(price['group'], 'price')
            self.assertEqual(price['subgroup'], 'mid_price_true')

    def test_remove_outliers_no_outliers(self):
        """Test outlier removal when no outliers exist."""
        valid_prices = self.factor._remove_outliers(self.sample_prices)
        
        self.assertEqual(len(valid_prices), 3)
        self.assertEqual(valid_prices, self.sample_prices)

    def test_remove_outliers_with_outliers(self):
        """Test outlier removal when outliers exist."""
        prices_with_outlier = self.sample_prices + [
            {
                'source': 'outlier_source',
                'price': Decimal('200.00'),  # Significantly higher than others
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            }
        ]
        
        valid_prices = self.factor._remove_outliers(prices_with_outlier)
        
        # Should remove the outlier but keep the original prices
        self.assertEqual(len(valid_prices), 3)
        self.assertNotIn(prices_with_outlier[-1], valid_prices)

    def test_remove_outliers_too_few_prices(self):
        """Test outlier removal with too few prices."""
        two_prices = self.sample_prices[:2]
        valid_prices = self.factor._remove_outliers(two_prices)
        
        # Should return all prices when there are 2 or fewer
        self.assertEqual(len(valid_prices), 2)
        self.assertEqual(valid_prices, two_prices)

    def test_calculate_average_price(self):
        """Test average price calculation."""
        average = self.factor._calculate_average_price(self.sample_prices)
        
        expected = (Decimal('100.50') + Decimal('100.75') + Decimal('100.60')) / 3
        self.assertEqual(average, expected)

    def test_get_dependencies(self):
        """Test factor dependencies."""
        dependencies = self.factor.get_dependencies()
        
        expected_sources = ["ibkr", "fmp", "yahoo", "alpha_vantage", "quandl"]
        expected_deps = [f"company_share_price_{source}" for source in expected_sources]
        
        self.assertEqual(dependencies, expected_deps)

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.factor)
        expected = "CompanyShareMidPriceFactor(name=mid_price, group=price, subgroup=mid_price_true)"
        self.assertEqual(repr_str, expected)

    def test_calculate_integration_with_outlier_removal(self):
        """Test full calculation pipeline including outlier removal."""
        prices_with_outlier = [
            {
                'source': 'source1',
                'price': Decimal('100.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'source2',
                'price': Decimal('100.10'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'outlier',
                'price': Decimal('150.00'),  # Clear outlier
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'source3',
                'price': Decimal('99.90'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            }
        ]
        
        result = self.factor.calculate(prices_with_outlier)
        
        # Should calculate average without the outlier
        # Expected: (100.00 + 100.10 + 99.90) / 3 = 100.00
        self.assertIsNotNone(result)
        expected = (Decimal('100.00') + Decimal('100.10') + Decimal('99.90')) / 3
        self.assertAlmostEqual(float(result), float(expected), places=2)

    def test_different_groups_filtered_out(self):
        """Test that prices with different groups are filtered out."""
        mixed_group_prices = [
            {
                'source': 'good1',
                'price': Decimal('100.00'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'bad1',
                'price': Decimal('200.00'),
                'timestamp': datetime.now(),
                'group': 'volume',  # Wrong group
                'subgroup': 'mid_price_true'
            },
            {
                'source': 'good2',
                'price': Decimal('100.20'),
                'timestamp': datetime.now(),
                'group': 'price',
                'subgroup': 'mid_price_true'
            }
        ]
        
        result = self.factor.calculate(mixed_group_prices)
        
        # Should average only the 2 valid prices
        expected = (Decimal('100.00') + Decimal('100.20')) / 2
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()