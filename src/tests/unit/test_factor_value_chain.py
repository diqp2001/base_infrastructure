"""
Unit tests for the factor value chain.

Verifies three families of bug that produce silent zeros or IntegrityErrors:

1. Leaf factor entities have valid defaults (frequency not None, source in SOURCES).
   The resolution service calls `get_factor_entity()()` with no args to read defaults.
   If `frequency=None`, the DB INSERT fails with NOT NULL constraint.
   If `source='multiple'` (not in SOURCES), Factor.__init__ raises ValueError before
   any INSERT.

2. calculate() methods use the class name as the dependency dict key.
   The resolution service keys dependency values by dep class name (e.g.
   'CurrencyRateFactor'), not by the factor_library alias ('currency_mid_price_factor').
   Wrong key → calculate() falls back to default (often 0 or 1) → silent wrong result.

3. Holding value factors return non-zero when both price/rate and quantity are known.
   These catch the 'value = 0' regression caused by bugs in (1) or (2).
"""

import unittest
from decimal import Decimal

from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor
from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.domain.entities.factor.finance.holding.currency_portfolio_holding_value_factor import CurrencyPortfolioHoldingValueFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor


class TestLeafFactorDefaults(unittest.TestCase):
    """
    Leaf factors must have valid defaults.
    The resolution service calls get_factor_entity()() to read entity defaults
    and then passes them to _create_or_get. Any None or invalid value in those
    defaults propagates directly into the DB INSERT.
    """

    def test_company_share_mid_price_factor_frequency_not_none(self):
        # frequency=None → NULL INSERT → IntegrityError on NOT NULL column
        f = CompanyShareMidPriceFactor()
        self.assertIsNotNone(f.frequency, "frequency must not be None — causes NULL DB INSERT")
        self.assertEqual(f.frequency, '1d')

    def test_company_share_mid_price_factor_source_in_whitelist(self):
        f = CompanyShareMidPriceFactor()
        self.assertIn(f.source, Factor.SOURCES, f"source '{f.source}' not in Factor.SOURCES")

    def test_currency_rate_factor_source_not_multiple(self):
        # 'multiple' is not in Factor.SOURCES — Factor.__init__ raises ValueError
        f = CurrencyRateFactor()
        self.assertIn(f.source, Factor.SOURCES, f"source '{f.source}' not in Factor.SOURCES")
        self.assertNotEqual(f.source, 'multiple')

    def test_currency_rate_factor_frequency_propagates_through_super(self):
        # frequency must be passed to super().__init__(), not set via self.frequency after
        f = CurrencyRateFactor(frequency='1d')
        self.assertEqual(f.frequency, '1d')

    def test_currency_value_factor_frequency_not_none(self):
        f = CurrencyValueFactor()
        self.assertIsNotNone(f.frequency)
        self.assertIn(f.source, Factor.SOURCES)

    def test_company_share_value_factor_frequency_not_none(self):
        f = CompanyShareValueFactor()
        self.assertIsNotNone(f.frequency)
        self.assertIn(f.source, Factor.SOURCES)

    def test_company_share_option_mid_price_factor_frequency_not_none(self):
        f = CompanyShareOptionMidPriceFactor()
        self.assertIsNotNone(f.frequency, "frequency must not be None — causes NULL DB INSERT")
        self.assertEqual(f.frequency, '1d')

    def test_company_share_option_mid_price_factor_source_in_whitelist(self):
        f = CompanyShareOptionMidPriceFactor()
        self.assertIn(f.source, Factor.SOURCES, f"source '{f.source}' not in Factor.SOURCES")
        self.assertNotEqual(f.source, 'multiple')
        # Like CompanyShareMidPriceFactor, the mid-price is a calculated aggregate;
        # source='calculated' so the DependencySpec source_not_in=["calculated"] excludes
        # this factor from its own deps (preventing circular resolution).
        self.assertEqual(f.source, 'calculated')


class TestOptionMidPriceFactorResolution(unittest.TestCase):
    """
    CompanyShareOptionMidPriceFactor must use Branch A (calculate_dependencies property)
    so the resolution service queries CompanyShareOptionFactor records — not share factors.
    """

    def test_has_calculate_dependencies_property(self):
        f = CompanyShareOptionMidPriceFactor()
        self.assertTrue(
            hasattr(f, 'calculate_dependencies'),
            "Must be a @property so hasattr() returns True and routes to Branch A"
        )

    def test_calculate_dependencies_references_option_factor(self):
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
        f = CompanyShareOptionMidPriceFactor()
        deps = f.calculate_dependencies
        self.assertEqual(len(deps), 1)
        spec = deps[0]
        self.assertIsInstance(spec, DependencySpec)
        self.assertIs(spec.factor_type, CompanyShareOptionFactor,
                      "Must depend on CompanyShareOptionFactor, not CompanyShareFactor")

    def test_calculate_returns_average_of_two_prices(self):
        f = CompanyShareOptionMidPriceFactor(min_sources=2)
        result = f.calculate({'CompanyShareOptionFactor': [10.0, 12.0]})
        self.assertIsNotNone(result)
        self.assertEqual(result, Decimal('11'))

    def test_calculate_returns_none_when_insufficient_sources(self):
        f = CompanyShareOptionMidPriceFactor(min_sources=2)
        result = f.calculate({'CompanyShareOptionFactor': [10.0]})
        self.assertIsNone(result)

    def test_calculate_wrong_key_returns_none(self):
        # If the resolution service mistakenly uses share factors, the key won't match
        f = CompanyShareOptionMidPriceFactor(min_sources=2)
        result = f.calculate({'CompanyShareFactor': [10.0, 12.0]})
        self.assertIsNone(result)


class TestCalculateDependencyKeys(unittest.TestCase):
    """
    calculate() must look up dependency values by class name (the key the resolution
    service uses), not by factor_library alias.

    Pattern: the resolution service sets dependency_values[dep.__name__] = resolved_value.
    So calculate({'CurrencyRateFactor': 1.25}) is correct;
       calculate({'currency_mid_price_factor': 1.25}) is wrong (key never found).
    """

    def test_company_share_value_factor_class_name_key(self):
        price = Decimal('150.50')
        result = CompanyShareValueFactor().calculate({'CompanyShareMidPriceFactor': price})
        self.assertEqual(result, price)

    def test_company_share_value_factor_wrong_key_gives_zero(self):
        # Documents the bug: wrong key returns the 0 default, not the price
        price = Decimal('150.50')
        result = CompanyShareValueFactor().calculate({'company_share_mid_price_factor': price})
        self.assertEqual(result, Decimal('0'))

    def test_currency_value_factor_class_name_key(self):
        rate = Decimal('1.25')
        result = CurrencyValueFactor().calculate({'CurrencyRateFactor': rate})
        self.assertEqual(result, rate)

    def test_currency_value_factor_none_rate_falls_back_to_one(self):
        # When CurrencyRateFactor resolves to None (IBKR unavailable in backtest),
        # CurrencyValueFactor must default to 1.0 (identity rate) not crash or return 0.
        result = CurrencyValueFactor().calculate({'CurrencyRateFactor': None})
        self.assertEqual(result, Decimal('1'))

    def test_currency_value_factor_missing_key_falls_back_to_one(self):
        result = CurrencyValueFactor().calculate({})
        self.assertEqual(result, Decimal('1'))


class TestHoldingValueChainNonZero(unittest.TestCase):
    """
    Holding value factors must return the product of asset value × position quantity.
    A result of 0 when both inputs are non-zero signals a broken dependency key or
    a failed upstream resolution that was silently coerced to 0.
    """

    def test_company_share_holding_value_is_price_times_quantity(self):
        factor = CompanySharePortfolioHoldingValueFactor()
        result = factor.calculate({
            'CompanyShareValueFactor': Decimal('150.50'),
            'Position': Decimal('100'),
        })
        self.assertEqual(result, Decimal('150.50') * Decimal('100'))
        self.assertGreater(result, Decimal('0'))

    def test_company_share_holding_value_zero_price_gives_zero(self):
        # Zero price is semantically valid (e.g. no market data); result must be 0
        factor = CompanySharePortfolioHoldingValueFactor()
        result = factor.calculate({
            'CompanyShareValueFactor': Decimal('0'),
            'Position': Decimal('100'),
        })
        self.assertEqual(result, Decimal('0'))

    def test_currency_holding_value_is_rate_times_quantity(self):
        factor = CurrencyPortfolioHoldingValueFactor()
        result = factor.calculate({
            'CurrencyValueFactor': Decimal('1.25'),
            'Position': Decimal('1000000'),
        })
        self.assertEqual(result, Decimal('1.25') * Decimal('1000000'))
        self.assertGreater(result, Decimal('0'))

    def test_currency_holding_value_identity_rate(self):
        # USD portfolio holding USD: rate = 1.0, holding value = raw position quantity
        factor = CurrencyPortfolioHoldingValueFactor()
        result = factor.calculate({
            'CurrencyValueFactor': Decimal('1'),
            'Position': Decimal('1000000'),
        })
        self.assertEqual(result, Decimal('1000000'))


if __name__ == '__main__':
    unittest.main()
