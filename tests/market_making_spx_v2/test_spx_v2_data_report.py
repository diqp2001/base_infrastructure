"""
SPX v2 data report (data_report.txt) and the dependency explainer behind it.

The explainer runs on the SQLite market of tests/component/factor_context/factor_world.py (AAPL option
position, USD, dated SOFR future SR3H6 at T); the report / cycle / manager parts use the fakes of
test_spx_v2_project.py.
"""

import logging
import os
import tempfile
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config as v2_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.data.position_book import (
    FACTOR_REPO_KEYS, PositionBook,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.project_manager import (
    MarketMakingSPXCallSpreadV2ProjectManager,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.utils.data_report import (
    REPORT_FILE, DataReport,
)
from src.application.services.data.entities.factor.factor_dependency_explainer import FactorDependencyExplainer
from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from tests.component.factor_context.factor_catalog import factor_classes
from tests.component.factor_context.factor_world import FUTURE_SYMBOL, OPTION_SYMBOL, T, FactorWorld
from tests.market_making_spx_v2.test_spx_v2_project import FakeStrategy, FakePortfolio, OPTION, T0, make_cycle, slice_with

logging.getLogger("PositionBook").setLevel(logging.CRITICAL)


@pytest.fixture
def world():
    w = FactorWorld()
    w.option_portfolio()
    for repo_key in FACTOR_REPO_KEYS.values():
        w.definition(dict(factor_classes())[repo_key])
    yield w
    w.close()


def drop_sofr_contract(w):
    """The bar's SOFR contract is not stored (only another contract is) — the reported failure."""
    from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
    w.s.query(FinancialAssetModel).filter(FinancialAssetModel.symbol == FUTURE_SYMBOL).update({"symbol": "SR3Z6"})
    w.s.commit()


def explain(w, factor_name, when=T):
    option = w.f.get_local_repository("CompanyShareOption").get_by_symbol(OPTION_SYMBOL)
    resolver = FactorValueResolutionService(factory=w.f, logger=logging.getLogger("explainer-test"))
    return FactorDependencyExplainer(resolver, w.f).explain(w.definition(dict(factor_classes())[factor_name]),
                                                            option, when)


# ---- the explainer -----------------------------------------------------------------------------

class TestExplainer:

    def test_missing_sofr_contract_is_the_root_cause_with_the_contract_named(self, world):
        drop_sofr_contract(world)
        tree = explain(world, "CompanyShareOptionImpliedVolFactor")
        assert tree.missing
        causes = tree.root_causes()
        rate = [c for c in causes if c.status == "no_related_entity"]
        assert rate and "SR3H6" in rate[0].detail and "USD" in rate[0].entity
        found = {c.factor.split(" ")[0]: c.value for c in tree.children if not c.missing}
        assert found.get("CompanyShareOptionValueFactor") == pytest.approx(8.0)   # values found are shown

    def test_missing_definition_shows_the_stored_ones(self, world):
        """A spec no stored definition can satisfy is reported with the definitions that do exist."""
        from unittest.mock import PropertyMock, patch
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
            CompanyShareValueFactor,
        )
        iv = dict(factor_classes())["CompanyShareOptionImpliedVolFactor"]
        impossible = [DependencySpec(factor_type=CompanyShareValueFactor, group="value", source_in=["no_such_source"])]
        with patch.object(iv, "calculate_dependencies", new_callable=PropertyMock, return_value=impossible):
            tree = explain(world, "CompanyShareOptionImpliedVolFactor")
        details = [c.detail for c in tree.root_causes() if c.status == "no_definition"]
        assert details and "stored:" in details[0] and "no_such_source" in details[0]

    def test_a_resolved_factor_has_nothing_missing(self, world):
        tree = explain(world, "CompanyShareOptionImpliedVolFactor")
        assert not tree.missing and tree.value == pytest.approx(0.3091, abs=1e-3)
        assert tree.root_causes() == []

    def test_render_is_a_readable_tree(self, world):
        drop_sofr_contract(world)
        text = explain(world, "CompanyShareOptionImpliedVolFactor").render()
        assert text.splitlines()[0].startswith("CompanyShareOptionImpliedVolFactor")
        assert "└─ " in text and "MISSING (no_related_entity)" in text and "= 8" in text


# ---- the report, fed by PositionBook ------------------------------------------------------------

class TestReportFromPositionBook:

    def test_misses_are_grouped_by_option_greek_and_cause_across_bars(self, world):
        drop_sofr_contract(world)
        report = DataReport(project="test", period=("a", "b"))
        book = PositionBook(world.f, lambda: world.s, report=report)
        for when in (T, T + timedelta(days=1)):
            positions = book.load_positions(when)
            book.enrich(positions, book.market_data(positions, when))
        assert {m.greek for m in report.misses.values()} >= {"delta", "gamma", "vega", "implied_vol"}
        iv = [m for m in report.misses.values() if m.greek == "implied_vol"]
        assert sum(m.count for m in iv) == 2 and min(m.first for m in iv) == T
        assert "SR3H6" in iv[0].cause and "└─" in iv[0].tree

    def test_unknown_option_is_reported(self, world):
        report = DataReport()
        PositionBook(world.f, lambda: world.s, report=report).market_data({"p": {"symbol": "NOPE"}}, T)
        assert {(m.symbol, m.cause) for m in report.misses.values()} == {
            ("NOPE", "option not found in CompanyShareOption")}

    def test_explanations_are_bounded_per_run(self, world):
        drop_sofr_contract(world)
        report = DataReport()
        book = PositionBook(world.f, lambda: world.s, report=report)
        book.MAX_EXPLANATIONS = 1
        positions = book.load_positions(T)
        book.market_data(positions, T)
        assert book._explained == 1
        assert any("explanation limit" in m.cause for m in report.misses.values())


# ---- report content and start checks ------------------------------------------------------------

class TestReportContent:

    def test_sofr_contract_check_flags_the_missing_contract_of_the_window(self):
        report = DataReport()
        report.check_sofr_contracts(date(2026, 8, 5), date(2026, 8, 30), ["SR3Z6"])
        ok, title, detail = report.checks[0]
        assert not ok and "SR3U6" in detail and "2026-08-05" in detail

    def test_sofr_contract_check_passes_when_registered(self):
        report = DataReport()
        report.check_sofr_contracts(date(2026, 8, 5), date(2026, 8, 30), ["SR3U6", "SR3Z6"])
        assert report.checks[0][0] is True

    def test_written_file_has_the_three_sections(self):
        report = DataReport(project="spx", period=("2026-08-05", "2026-08-30"), bars=3)
        report.check(False, "SR3 contract", "SR3U6 needed")
        report.greek_missing(datetime(2026, 8, 5, 16), OPTION, "delta", "rate missing", "delta  [x]  MISSING")
        report.hedge_decided_without_greeks(datetime(2026, 8, 5, 16), [OPTION], 0.0)
        with tempfile.TemporaryDirectory() as tmp:
            text = open(report.write(tmp), encoding="utf-8").read()
        for expected in ("1. CHECKS AT START  (0 ok, 1 failed)", "[MISSING] SR3 contract", "2. GREEKS THAT DID NOT RESOLVE",
                         f"{OPTION}  delta: 1 bar(s)", "root cause: rate missing", "3. HEDGE DECIDED WITH POSITIONS MISSING GREEKS  (1",
                         "book delta used: 0.0"):
            assert expected in text, expected


# ---- the cycle and the project manager -----------------------------------------------------------

class TestCycleAndManager:

    def test_cycle_records_a_hedge_decided_while_greeks_are_missing(self):
        portfolio = FakePortfolio({OPTION: -10})
        cycle = make_cycle(portfolio, FakeStrategy(hedge={'should_hedge': False, 'portfolio_delta': 0.0}))
        cycle.position_book.greeks = {}                                    # greeks did not resolve
        cycle.position_book.report = DataReport()
        cycle.step(T0, slice_with("SPY", 640.0), portfolio)
        assert cycle.position_book.report.hedges_without_greeks == [(T0, [OPTION], 0.0)]

    def test_cycle_with_greeks_records_nothing(self):
        portfolio = FakePortfolio({OPTION: -10})
        cycle = make_cycle(portfolio, FakeStrategy())
        cycle.position_book.report = DataReport()
        cycle.step(T0, slice_with("SPY", 640.0), portfolio)
        assert cycle.position_book.report.hedges_without_greeks == []

    def _manager(self, tmp, engine_result):
        cfg = dict(v2_config.get_config(), results_dir=tmp, mlflow_experiment_name="spx_v2_report_test",
                   mlflow_tracking_uri=os.path.join(tmp, "mlruns"))
        manager = MarketMakingSPXCallSpreadV2ProjectManager(config=cfg, database_service=object())
        report = DataReport(project=cfg["project_name"])
        report.greek_missing(T0, OPTION, "delta", "rate missing")
        algorithm = SimpleNamespace(cycle=SimpleNamespace(position_book=SimpleNamespace(report=report)),
                                    cycle_results=[], value_history=[], portfolio_value=1.0)

        def run_backtest(config):
            manager.runner.algorithm_instance = algorithm
            return engine_result
        manager.runner.run_backtest = run_backtest
        manager._start_mlflow = lambda: None
        return manager

    def test_manager_writes_the_report_and_links_it_in_the_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self._manager(tmp, {"success": True, "misbuffet_result": "ok"}).run()
            path = os.path.join(tmp, REPORT_FILE)
            assert out["summary"]["data_report"] == path and os.path.exists(path)
            assert "root cause: rate missing" in open(path, encoding="utf-8").read()

    def test_manager_writes_the_report_when_the_run_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(tmp, {"success": True, "misbuffet_result": "❌ Backtest failed: TWS down"})
            with pytest.raises(RuntimeError):
                manager.run()
            assert os.path.exists(os.path.join(tmp, REPORT_FILE))


# ---- the report is rewritten after every bar ----------------------------------------------------

class TestReportEveryBar:

    def _algorithm(self, tmp, step):
        from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.backtesting.base_project_algorithm import (
            Algorithm, PortfolioGateway,
        )
        algo = Algorithm()
        algo.initialized = True
        algo.gateway = PortfolioGateway(SimpleNamespace(_get_current_position_qty=lambda t: 0,
                                                        set_holdings=lambda targets, data=None: {},
                                                        portfolio_repo=SimpleNamespace(session=None)))
        report = DataReport(project="spx", directory=tmp)
        algo.cycle = SimpleNamespace(step=step, position_book=SimpleNamespace(report=report))
        return algo, report

    def test_each_on_data_rewrites_the_file_with_the_bars_so_far(self):
        from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.trading_cycle import (
            CycleResult,
        )
        with tempfile.TemporaryDirectory() as tmp:
            reports = []

            def step(t, data, gateway):
                reports[0].greek_missing(t, OPTION, "delta", "rate missing")
                return CycleResult(time=t)
            algo, report = self._algorithm(tmp, step)
            reports.append(report)
            path = os.path.join(tmp, REPORT_FILE)
            for day in range(3):
                algo.on_data(slice_with("SPY", 640.0, time=T0 + timedelta(days=day)))
                text = open(path, encoding="utf-8").read()
                assert f"bars {day + 1}" in text
                assert f"delta: {day + 1} bar(s)" in text

    def test_a_bar_that_raises_still_updates_the_file(self):
        def step(t, data, gateway):
            raise RuntimeError("IBKR timeout")
        with tempfile.TemporaryDirectory() as tmp:
            algo, _ = self._algorithm(tmp, step)
            algo.on_data(slice_with("SPY", 640.0))
            assert os.path.exists(os.path.join(tmp, REPORT_FILE))

    def test_no_directory_writes_nothing(self):
        assert DataReport().save() is None
