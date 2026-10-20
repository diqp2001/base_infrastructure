"""
Unit tests for ENTITY_FACTOR_MAPPING completeness.

Ensures that every financial-entity class that can appear in an algorithm universe
has a corresponding entry in ENTITY_FACTOR_MAPPING, and that the mapped factor
class is a non-empty list of valid Factor subclasses.

Add a row to EXPECTED_MAPPINGS whenever a new entity + factor pair is created.
"""

import unittest

from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING
from src.domain.entities.factor.factor import Factor

# ── entity classes ────────────────────────────────────────────────────────────
from src.domain.entities.continent import Continent
from src.domain.entities.country import Country
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.financial_assets.security import Security
from src.domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.index.index_bond import IndexBond
from src.domain.entities.finance.financial_assets.index.index_company_share import IndexCompanyShare
from src.domain.entities.finance.financial_assets.index.index_company_share_portfolio import IndexCompanySharePortfolio
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.equity import Equity
from src.domain.entities.finance.financial_assets.share.share import Share
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.bond import Bond
from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future
from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio

# ── factor entity classes ─────────────────────────────────────────────────────
from src.domain.entities.factor.continent_factor import ContinentFactor
from src.domain.entities.factor.country_factor import CountryFactor
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


# ── expected pairs ────────────────────────────────────────────────────────────
# Each tuple is (EntityClass, ExpectedFirstFactorClass).
# The test checks: EntityClass is a key, and ExpectedFirstFactorClass is the
# first element of the mapped list.
EXPECTED_MAPPINGS = [
    (Continent,                    ContinentFactor),
    (Country,                      CountryFactor),
    (FinancialAsset,               FinancialAssetFactor),
    (Security,                     SecurityFactor),
    (Index,                        IndexFactor),
    (IndexBond,                    IndexFactor),
    (IndexCompanyShare,            IndexFactor),
    (IndexCompanySharePortfolio,   IndexFactor),
    (Currency,                     CurrencyFactor),
    (Equity,                       EquityFactor),
    (Share,                        ShareFactor),
    (CompanyShare,                 CompanyShareFactor),
    (Bond,                         BondFactor),
    (Derivative,                   DerivativeFactor),
    (Option,                       OptionFactor),
    (IndexFutureOption,            IndexFutureOptionFactor),
    (CompanyShareOption,           CompanyShareOptionFactor),
    (CompanySharePortfolioOption,  CompanyShareOptionPortfolioFactor),
    (CompanySharePortfolio,        CompanySharePortfolioFactor),
    (Future,                       FutureFactor),
    (BondFuture,                   BondFutureFactor),
    (IndexFuture,                  IndexFutureFactor),
]


class TestEntityFactorMappingCoverage(unittest.TestCase):
    """Each financial entity must be a key in ENTITY_FACTOR_MAPPING."""

    def test_all_expected_entities_are_present(self):
        missing = [
            entity_cls.__name__
            for entity_cls, _ in EXPECTED_MAPPINGS
            if entity_cls not in ENTITY_FACTOR_MAPPING
        ]
        self.assertEqual(
            missing, [],
            f"Entities missing from ENTITY_FACTOR_MAPPING: {missing}",
        )

    def test_no_empty_factor_list(self):
        for entity_cls, _ in EXPECTED_MAPPINGS:
            with self.subTest(entity=entity_cls.__name__):
                factor_list = ENTITY_FACTOR_MAPPING.get(entity_cls, [])
                self.assertTrue(
                    len(factor_list) > 0,
                    f"ENTITY_FACTOR_MAPPING[{entity_cls.__name__}] is empty",
                )

    def test_first_factor_matches_expected(self):
        for entity_cls, expected_factor_cls in EXPECTED_MAPPINGS:
            with self.subTest(entity=entity_cls.__name__):
                factor_list = ENTITY_FACTOR_MAPPING.get(entity_cls)
                self.assertIsNotNone(
                    factor_list,
                    f"{entity_cls.__name__} not in ENTITY_FACTOR_MAPPING",
                )
                actual = factor_list[0]
                self.assertIs(
                    actual,
                    expected_factor_cls,
                    f"{entity_cls.__name__} → expected {expected_factor_cls.__name__}, "
                    f"got {actual.__name__}",
                )

    def test_all_mapped_factor_classes_are_factor_subclasses(self):
        for entity_cls, factor_list in ENTITY_FACTOR_MAPPING.items():
            for factor_cls in factor_list:
                with self.subTest(entity=entity_cls.__name__, factor=factor_cls.__name__):
                    self.assertTrue(
                        issubclass(factor_cls, Factor),
                        f"{factor_cls.__name__} is not a subclass of Factor",
                    )

    def test_no_none_values_in_mapping(self):
        for entity_cls, factor_list in ENTITY_FACTOR_MAPPING.items():
            with self.subTest(entity=entity_cls.__name__):
                for factor_cls in factor_list:
                    self.assertIsNotNone(
                        factor_cls,
                        f"ENTITY_FACTOR_MAPPING[{entity_cls.__name__}] contains None",
                    )


class TestFutureEntityMappings(unittest.TestCase):
    """Focused checks on the three Future-family entities the session added."""

    def test_future_maps_to_future_factor(self):
        self.assertIn(Future, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[Future][0], FutureFactor)

    def test_bond_future_maps_to_bond_future_factor(self):
        self.assertIn(BondFuture, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[BondFuture][0], BondFutureFactor)

    def test_index_future_maps_to_index_future_factor(self):
        self.assertIn(IndexFuture, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[IndexFuture][0], IndexFutureFactor)

    def test_bond_future_factor_is_subclass_of_future_factor(self):
        self.assertTrue(issubclass(BondFutureFactor, FutureFactor))


class TestIndexEntityMappings(unittest.TestCase):
    """Index subtypes (IndexBond, IndexCompanyShare, IndexCompanySharePortfolio)."""

    def test_index_bond_in_mapping(self):
        self.assertIn(IndexBond, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[IndexBond][0], IndexFactor)

    def test_index_company_share_in_mapping(self):
        self.assertIn(IndexCompanyShare, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[IndexCompanyShare][0], IndexFactor)

    def test_index_company_share_portfolio_in_mapping(self):
        self.assertIn(IndexCompanySharePortfolio, ENTITY_FACTOR_MAPPING)
        self.assertIs(ENTITY_FACTOR_MAPPING[IndexCompanySharePortfolio][0], IndexFactor)


if __name__ == "__main__":
    unittest.main()
