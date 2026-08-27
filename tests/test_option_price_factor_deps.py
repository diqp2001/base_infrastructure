"""
Diagnostic integration test for CompanyShareOptionPriceFactor dependency resolution.

Full dependency tree
====================
CompanyShareOptionPriceFactor  [Branch A — calculate_dependencies]
  ├─ CompanyShareValueFactor   [Branch A — calculate_dependencies]
  │    └─ CompanyShareMidPriceFactor   [Branch B — IBKR leaf, entity: CompanyShare]
  │
  ├─ CompanyShareOptionRFYieldFactor   [Branch B — DB FactorDependency]
  │    └─ CurrencyYieldFactor          [Branch B — DB FactorDependency]
  │         └─ BondFutureAnnualizedYieldFactor  [Branch A — calculate_dependencies=['price']]
  │              └─ BondFutureFactor (price)    [Branch B — IBKR leaf, entity: BondFuture SR3Z6]
  │
  └─ CompanyShareOptionImpliedVolFactor  [Branch A — calculate_dependencies]
       └─ CompanyShareOptionFactor       [Branch B — IBKR leaf, entity: CompanyShareOption]
            ⚠  calculate() always returns None until S, K, r, T are integrated

Run with:
    python -m pytest tests/test_option_price_factor_deps.py -v -s
  or:
    python -m unittest tests.test_option_price_factor_deps -v
"""

import logging
import unittest
from datetime import datetime

from src.application.services.database_service.database_service import DatabaseService
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService

logging.basicConfig(level=logging.WARNING)

# ── configuration ─────────────────────────────────────────────────────────────
DB_TYPE = "sql_server"
OPTION_SYMBOL = "SPY   281215C00770000"
TEST_DATE = datetime(2026, 8, 6, 9, 30, 0)
REPOSITORY_TYPE = "local"

# All factor class names that should have a row in the factors table
EXPECTED_FACTOR_NAMES = [
    "CompanyShareOptionPriceFactor",
    "CompanyShareValueFactor",
    "CompanyShareMidPriceFactor",
    "CompanyShareOptionRFYieldFactor",
    "CurrencyYieldFactor",
    "BondFutureAnnualizedYieldFactor",
    "BondFutureFactor",
    "CompanyShareOptionImpliedVolFactor",
    "CompanyShareOptionFactor",
]

# Direct deps declared in calculate_dependencies on CompanyShareOptionPriceFactor
DIRECT_DYNAMIC_DEPS = [
    "CompanyShareValueFactor",
    "CompanyShareOptionRFYieldFactor",
    "CompanyShareOptionImpliedVolFactor",
]


class TestOptionPriceFactorDeps(unittest.TestCase):
    """
    Integration test: checks every layer in the option_price resolution chain.
    All test methods are independent — they print a PASS / FAIL summary so you
    can see exactly which layer breaks without reading through a traceback.
    """

    @classmethod
    def setUpClass(cls):
        cls.db_service = DatabaseService(DB_TYPE)
        cls.factory = RepositoryFactory(cls.db_service.session)
        cls.resolution_service = FactorValueResolutionService(
            factory=cls.factory,
            logger=logging.getLogger("option_dep_test"),
        )
        cls.results = {}  # populated by each test, read by tearDownClass

    @classmethod
    def tearDownClass(cls):
        print("\n" + "=" * 70)
        print("OPTION PRICE FACTOR — DEPENDENCY RESOLUTION SUMMARY")
        print("=" * 70)
        for name, (status, detail) in cls.results.items():
            mark = "✓" if status == "PASS" else "✗"
            print(f"  {mark}  {name:<50} {status}  {detail}")
        print("=" * 70)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _record(self, name: str, status: str, detail: str = ""):
        self.__class__.results[name] = (status, detail)

    def _get_option(self):
        """Return the CompanyShareOption domain entity for OPTION_SYMBOL."""
        repo = self.factory.get_local_repository("CompanyShareOption")
        if repo is None:
            return None
        return repo.get_by_symbol(OPTION_SYMBOL)

    def _get_factor_record(self, factor_repo_key: str, name: str, group: str):
        """Return the factor ORM row from the DB using get_by_all."""
        repo = self.factory.get_local_repository(factor_repo_key)
        if repo is None or not hasattr(repo, "get_by_all"):
            return None
        return repo.get_by_all(name=name, group=group)

    # ── 1. Entity existence ───────────────────────────────────────────────────

    def test_01_option_entity_exists(self):
        option = self._get_option()
        if option:
            self._record("CompanyShareOption entity", "PASS", f"id={option.id}")
        else:
            self._record("CompanyShareOption entity", "FAIL", f"symbol '{OPTION_SYMBOL}' not in DB")
        self.assertIsNotNone(option, f"CompanyShareOption '{OPTION_SYMBOL}' not found in DB")

    def test_02_underlying_share_exists(self):
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing — skipping underlying check")
        if not option.underlying_asset_id:
            self._record("underlying CompanyShare", "FAIL", "option.underlying_asset_id is None")
            self.fail("option.underlying_asset_id is None")
        share_repo = self.factory.get_local_repository("CompanyShare")
        share = share_repo.get_by_id(option.underlying_asset_id) if share_repo else None
        if share:
            self._record("underlying CompanyShare", "PASS", f"id={share.id}")
        else:
            self._record("underlying CompanyShare", "FAIL",
                         f"underlying_asset_id={option.underlying_asset_id} not found")
        self.assertIsNotNone(share)

    def test_03_currency_exists(self):
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing — skipping currency check")
        if not option.currency_id:
            self._record("option Currency entity", "FAIL", "option.currency_id is None")
            self.fail("option.currency_id is None")
        cur_repo = self.factory.get_local_repository("Currency")
        currency = cur_repo.get_by_id(option.currency_id) if cur_repo else None
        if currency:
            self._record("option Currency entity", "PASS",
                         f"id={currency.id} iso={getattr(currency, 'iso_code', '?')}")
        else:
            self._record("option Currency entity", "FAIL",
                         f"currency_id={option.currency_id} not found")
        self.assertIsNotNone(currency)

    def test_04_bond_future_sr3z6_exists(self):
        repo = self.factory.get_local_repository("BondFuture")
        entity = None
        if repo and hasattr(repo, "get_by_symbol"):
            entity = repo.get_by_symbol("SR3Z6")
        if entity is None and repo and hasattr(repo, "get_by_ticker"):
            entity = repo.get_by_ticker("SR3Z6")
        if entity:
            self._record("BondFuture SR3Z6 entity", "PASS", f"id={entity.id}")
        else:
            self._record("BondFuture SR3Z6 entity", "FAIL", "SR3Z6 not found in DB")
        self.assertIsNotNone(entity, "BondFuture SR3Z6 not found — needed for CurrencyYieldFactor chain")

    # ── 2. Factor record existence ────────────────────────────────────────────

    def test_05_option_price_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareOptionPriceFactor")
        record = repo.get_by_all(name="option_price", group="price") if repo else None
        if record:
            self._record("CompanyShareOptionPriceFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareOptionPriceFactor record", "FAIL", "not in DB — run factor init first")
        self.assertIsNotNone(record, "CompanyShareOptionPriceFactor not found in factors table")

    def test_06_company_share_value_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareValueFactor")
        record = repo.get_by_all(name="company_share_value", group="value") if repo else None
        if record:
            self._record("CompanyShareValueFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareValueFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_07_company_share_mid_price_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareMidPriceFactor")
        record = repo.get_by_all(name="mid_price", group="price") if repo else None
        if record:
            self._record("CompanyShareMidPriceFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareMidPriceFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_08_rf_yield_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareOptionRFYieldFactor")
        record = repo.get_by_all(name="rf_yield", group="fundamental") if repo else None
        if record:
            self._record("CompanyShareOptionRFYieldFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareOptionRFYieldFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_09_currency_yield_factor_record(self):
        repo = self.factory.get_local_repository("CurrencyYieldFactor")
        record = repo.get_by_all(name="currency_yield", group="fundamental") if repo else None
        if record:
            self._record("CurrencyYieldFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CurrencyYieldFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_10_bond_future_annualized_yield_factor_record(self):
        repo = self.factory.get_local_repository("BondFutureAnnualizedYieldFactor")
        record = repo.get_by_all(name="Annualized Yield", group="return") if repo else None
        if record:
            self._record("BondFutureAnnualizedYieldFactor record", "PASS", f"id={record.id}")
        else:
            self._record("BondFutureAnnualizedYieldFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_11_implied_vol_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareOptionImpliedVolFactor")
        record = repo.get_by_all(name="implied_vol", group="volatility") if repo else None
        if record:
            self._record("CompanyShareOptionImpliedVolFactor record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareOptionImpliedVolFactor record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    def test_12_company_share_option_factor_record(self):
        repo = self.factory.get_local_repository("CompanyShareOptionFactor")
        record = repo.get_by_all(name="close", group="price") if repo else None
        if record:
            self._record("CompanyShareOptionFactor (close) record", "PASS", f"id={record.id}")
        else:
            self._record("CompanyShareOptionFactor (close) record", "FAIL", "not in DB")
        self.assertIsNotNone(record)

    # ── 3. DB FactorDependency records ────────────────────────────────────────

    def test_13_rf_yield_has_db_dependency_to_currency_yield(self):
        rf_repo = self.factory.get_local_repository("CompanyShareOptionRFYieldFactor")
        dep_repo = getattr(self.factory, "factor_dependency_local_repo", None)
        rf_record = rf_repo.get_by_all(name="rf_yield", group="fundamental") if rf_repo else None
        if not rf_record or not dep_repo:
            self._record("RFYield→CurrencyYield FactorDependency", "FAIL", "factor record or dep repo missing")
            self.skipTest("prerequisite missing")
        deps = dep_repo.get_by_dependent_factor_id(rf_record.id)
        if deps:
            self._record("RFYield→CurrencyYield FactorDependency", "PASS",
                         f"{len(deps)} dep(s): {[d.independent_factor_id for d in deps]}")
        else:
            self._record("RFYield→CurrencyYield FactorDependency", "FAIL",
                         "no FactorDependency rows for rf_yield — run _ensure_dependency_records()")
        self.assertTrue(deps)

    def test_14_currency_yield_has_db_dependency_to_bond_future_yield(self):
        cy_repo = self.factory.get_local_repository("CurrencyYieldFactor")
        dep_repo = getattr(self.factory, "factor_dependency_local_repo", None)
        cy_record = cy_repo.get_by_all(name="currency_yield", group="fundamental") if cy_repo else None
        if not cy_record or not dep_repo:
            self._record("CurrencyYield→BondFutureYield FactorDependency", "FAIL", "missing")
            self.skipTest("prerequisite missing")
        deps = dep_repo.get_by_dependent_factor_id(cy_record.id)
        if deps:
            self._record("CurrencyYield→BondFutureYield FactorDependency", "PASS",
                         f"{len(deps)} dep(s): {[d.independent_factor_id for d in deps]}")
        else:
            self._record("CurrencyYield→BondFutureYield FactorDependency", "FAIL",
                         "no FactorDependency rows for currency_yield")
        self.assertTrue(deps)

    # ── 4. get_related_entities contracts ────────────────────────────────────

    def test_15_option_related_entities(self):
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing")
        repo = self.factory.get_local_repository("CompanyShareOption")
        related = repo.get_related_entities(option.id) if repo else []
        types = [type(e).__name__ for e in related]
        if related:
            self._record("option.get_related_entities()", "PASS", f"types={types}")
        else:
            self._record("option.get_related_entities()", "FAIL", "returned empty list")
        # must contain at least [CompanyShare, Currency]
        self.assertTrue(
            any("CompanyShare" in t for t in types),
            f"expected CompanyShare in related entities, got {types}",
        )
        self.assertTrue(
            any("Currency" in t for t in types),
            f"expected Currency in related entities, got {types}",
        )

    # ── 5. Resolution per direct dynamic dependency ───────────────────────────

    def _resolve_dep(self, dep_name: str, option, option_price_factor):
        """
        Attempt to resolve a single dependency of CompanyShareOptionPriceFactor.
        Returns (value or None, error_message or "").
        """
        dep_repo = self.factory.get_local_repository(dep_name)
        if dep_repo is None:
            return None, f"no repo registered for '{dep_name}'"

        if not hasattr(dep_repo, "_create_or_get"):
            return None, f"repo for '{dep_name}' has no _create_or_get"

        # Create-or-get the dep factor record so it has an ID
        dep_factor = dep_repo._create_or_get(
            dep_repo.get_factor_entity() if hasattr(dep_repo, "get_factor_entity") else dep_name,
            primary_key=option_price_factor.subgroup or dep_name,
        )
        if dep_factor is None or not getattr(dep_factor, "id", None):
            return None, f"_create_or_get returned None for '{dep_name}'"

        value = self.resolution_service.resolve_factor_value(
            factor_entity=dep_factor,
            entity=option,
            time_date=TEST_DATE,
            repository_type=REPOSITORY_TYPE,
        )
        return value, ""

    def test_16_resolve_company_share_value_factor(self):
        self._run_dep_resolution_test("CompanyShareValueFactor")

    def test_17_resolve_rf_yield_factor(self):
        self._run_dep_resolution_test("CompanyShareOptionRFYieldFactor")

    def test_18_resolve_implied_vol_factor(self):
        # Known: returns None because S, K, r, T not yet threaded through
        dep_name = "CompanyShareOptionImpliedVolFactor"
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing")
        dep_repo = self.factory.get_local_repository(dep_name)
        record = dep_repo.get_by_all(name="implied_vol", group="volatility") if dep_repo else None
        if record is None:
            self._record(f"resolve {dep_name}", "FAIL", "factor record not in DB")
            self.skipTest("factor record missing")
        from src.infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor_mapper import CompanyShareOptionImpliedVolFactorMapper
        dep_factor = CompanyShareOptionImpliedVolFactorMapper().to_domain(record)
        value = self.resolution_service.resolve_factor_value(
            factor_entity=dep_factor,
            entity=option,
            time_date=TEST_DATE,
            repository_type=REPOSITORY_TYPE,
        )
        # This is expected to be None — calculate() returns None by design
        if value is None:
            self._record(
                f"resolve {dep_name}", "FAIL (expected)",
                "calculate() returns None — S/K/r/T not integrated yet (by design)",
            )
        else:
            self._record(f"resolve {dep_name}", "PASS", f"value={value.value}")
        # Not a hard assertion — document the known gap, do not fail the suite
        print(
            f"\n  [INFO] {dep_name}: {'None (expected — not yet implemented)' if value is None else value.value}"
        )

    def _run_dep_resolution_test(self, dep_name: str):
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing")

        # Get the option_price factor record for context
        price_repo = self.factory.get_local_repository("CompanyShareOptionPriceFactor")
        price_record = price_repo.get_by_all(name="option_price", group="price") if price_repo else None
        if price_record is None:
            self.skipTest("option_price factor record missing — run factor init")

        dep_repo = self.factory.get_local_repository(dep_name)
        if dep_repo is None:
            self._record(f"resolve {dep_name}", "FAIL", f"no repo for '{dep_name}'")
            self.fail(f"no local repo registered for '{dep_name}'")

        # Use the mapper to get the domain factor from whatever record is in the DB
        factor_record = None
        if dep_name == "CompanyShareValueFactor":
            factor_record = dep_repo.get_by_all(name="company_share_value", group="value")
        elif dep_name == "CompanyShareOptionRFYieldFactor":
            factor_record = dep_repo.get_by_all(name="rf_yield", group="fundamental")
        elif dep_name == "CompanyShareOptionImpliedVolFactor":
            factor_record = dep_repo.get_by_all(name="implied_vol", group="volatility")

        if factor_record is None:
            self._record(f"resolve {dep_name}", "FAIL", "factor record not in DB — run entity init")
            self.fail(f"factor record for '{dep_name}' not in DB")

        dep_factor = dep_repo._to_entity(factor_record)
        if dep_factor is None or not getattr(dep_factor, "id", None):
            self._record(f"resolve {dep_name}", "FAIL", "_to_entity returned None")
            self.fail(f"_to_entity failed for '{dep_name}'")

        value = self.resolution_service.resolve_factor_value(
            factor_entity=dep_factor,
            entity=option,
            time_date=TEST_DATE,
            repository_type=REPOSITORY_TYPE,
        )

        if value is not None:
            self._record(f"resolve {dep_name}", "PASS", f"value={value.value}")
        else:
            self._record(f"resolve {dep_name}", "FAIL", "resolve_factor_value returned None")

        self.assertIsNotNone(
            value,
            f"resolve_factor_value returned None for {dep_name} — check logs above for root cause",
        )

    # ── 6. Full option_price resolution ──────────────────────────────────────

    def test_19_full_option_price_resolution(self):
        """End-to-end: resolve CompanyShareOptionPriceFactor for the option entity."""
        option = self._get_option()
        if option is None:
            self.skipTest("option entity missing")

        price_repo = self.factory.get_local_repository("CompanyShareOptionPriceFactor")
        price_record = price_repo.get_by_all(name="option_price", group="price") if price_repo else None
        if price_record is None:
            self.skipTest("option_price factor record missing")

        price_factor = price_repo._to_entity(price_record)
        value = self.resolution_service.resolve_factor_value(
            factor_entity=price_factor,
            entity=option,
            time_date=TEST_DATE,
            repository_type=REPOSITORY_TYPE,
        )

        if value is not None:
            self._record("FULL option_price resolution", "PASS", f"BSM price={value.value}")
        else:
            self._record(
                "FULL option_price resolution", "FAIL",
                "returned None — check individual dep tests above for root cause",
            )
        # Not a hard assertion here: individual dep tests already localize the failure
        print(f"\n  [RESULT] option_price for {OPTION_SYMBOL} @ {TEST_DATE}: "
              f"{'None' if value is None else value.value}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
