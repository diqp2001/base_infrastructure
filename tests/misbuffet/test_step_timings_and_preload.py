"""Per-bar timings (engine step_timings) and the backtest data preload (BacktestDataPreloadService, preloaded ranges
in the resolver). In-memory SQLite and fakes only — no IBKR, no SQL Server."""

from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from src.application.services.data.entities.factor import preloaded_coverage
from src.application.services.timing import step_timings
from tests.spatio_temporal_momentum.helpers import make_factory

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(autouse=True)
def _forget_preloaded_ranges():
    preloaded_coverage.clear()
    yield
    preloaded_coverage.clear()


# ── step timings ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_sections_add_up_and_nested_code_records_into_the_current_step(tmp_path):
    t = step_timings.StepTimings("2026-10-05 10:10:00")
    with step_timings.timed("read"):
        pass                                                                  # no current step: nothing recorded
    assert t.seconds == {}
    with step_timings.activate(t):
        with t.section("slice"):
            step_timings.count("ibkr_requests", 2)
        with t.section("cycle"):
            with step_timings.timed("read"):
                pass
            with step_timings.timed("read"):
                pass
            with step_timings.timed("train"):
                pass
    assert set(t.seconds) == {"slice", "cycle", "read", "train"} and t.counts == {"ibkr_requests": 2}
    assert step_timings.current() is None                                     # restored after the step
    csv_path = str(tmp_path / "timings.csv")
    line = step_timings.record(t, csv_path)
    step_timings.record(step_timings.StepTimings("2026-10-05 10:20:00"), csv_path)
    assert line.startswith("[timing] 2026-10-05 10:10:00  total") and "ibkr 2 req" in line
    rows = pd.read_csv(csv_path)
    assert list(rows["bar"]) == ["2026-10-05 10:10:00", "2026-10-05 10:20:00"]
    assert rows.loc[0, "ibkr_requests"] == 2 and rows.loc[1, "ibkr_requests"] == 0
    assert rows.loc[0, "total_s"] == pytest.approx(rows.loc[0, "slice_s"] + rows.loc[0, "cycle_s"], abs=1e-3)
    summary = step_timings.summarise(csv_path)
    assert summary.startswith("[timing] 2 bars, mean") and "ibkr 1.0 requests" in summary
    assert step_timings.summarise(str(tmp_path / "none.csv")) is None


def test_ibkr_history_requests_are_counted_in_the_current_step():
    from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
    broker = InteractiveBrokersBroker.__new__(InteractiveBrokersBroker)
    broker.ib_connection = None                                               # not connected: NOT_SENT, still counted
    t = step_timings.StepTimings("bar")
    with step_timings.activate(t):
        broker.request_history(SimpleNamespace(symbol="JPM"), "20261022 16:00:00 US/Eastern", "1 D", "10 mins",
                               "TRADES")
        broker.request_history(SimpleNamespace(symbol="BAC"), "20261022 16:00:00 US/Eastern", "1 D", "10 mins",
                               "TRADES")
    assert t.counts["ibkr_requests"] == 2 and "ibkr" in t.seconds


# ── preloaded ranges: the resolver serves the latest closed bar instead of asking IBKR ─────────────────────────────

def _ten_minute_series(session, starts, entity_id=1):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    f = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency="10m", data_type="numeric",
                                source="ibkr", definition="close", factor_type="company_share_factor")
    session.add(f)
    session.commit()
    for i, d in enumerate(starts):
        session.add(FactorValueModel(factor_id=f.id, entity_id=entity_id, entity_type="CompanyShare",
                                     date=pd.Timestamp(d).to_pydatetime(), value=repr(100.0 + i)))
    session.commit()
    return f.id


def test_a_missing_bar_inside_a_preloaded_range_is_served_locally_and_never_ahead():
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    factory, session, engine = make_factory()
    try:
        # 09:30 .. 10:00 stored, the 10:10 bar is missing (no trade), 10:20 stored
        fid = _ten_minute_series(session, ["2026-10-05 09:30", "2026-10-05 09:40", "2026-10-05 09:50",
                                           "2026-10-05 10:00", "2026-10-05 10:20"])
        service = FactorValueResolutionService(factory=factory)
        at_1025 = "2026-10-05 10:25:00"                                       # the 10:10 bar should have closed
        assert service._check_existing_value(fid, 1, "CompanyShare", at_1025, "local") is None   # -> IBKR today
        preloaded_coverage.register(fid, 1, datetime(2026, 9, 15), datetime(2026, 10, 9, 16))
        served = service._check_existing_value(fid, 1, "CompanyShare", at_1025, "local")
        assert served is not None and float(served.value) == 103.0            # the 10:00 bar, closed at 10:10
        # the 10:20 bar is still open at 10:25: never served
        assert pd.Timestamp(served.date) == pd.Timestamp("2026-10-05 10:00")
        # outside the registered range nothing changes
        assert service._check_existing_value(fid, 1, "CompanyShare", "2026-10-12 10:25:00", "local") is None
        assert not preloaded_coverage.covers(fid, 2, datetime(2026, 10, 5, 10, 25))      # another entity
    finally:
        session.close()
        engine.dispose()


# ── the preload service ─────────────────────────────────────────────────────────────────────────────────────────────

class _FakeImport:
    """MarketDataService stand-in: entities and an 'import' that stores the series (what IBKR would return)."""

    def __init__(self, factory, session, bars_by_symbol):
        self.entity_service = SimpleNamespace(repository_factory=factory)
        self.session = session
        self.bars_by_symbol = bars_by_symbol
        self.calls = []
        self.fid = None

    def _get_entity_by_ticker(self, ticker, entity_class):
        if ticker not in self.bars_by_symbol:
            return None
        share = entity_class.__new__(entity_class)
        share._id = 100 + sorted(self.bars_by_symbol).index(ticker)
        return share

    def _get_point_in_time_data(self, ticker, entity_class, point_in_time, bar_size_setting, duration_str,
                                what_to_show="TRADES"):
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        self.calls.append((ticker, bar_size_setting, duration_str, what_to_show))
        if self.fid is None:
            self.fid = _ten_minute_series(self.session, [], entity_id=0)
        entity_id = 100 + sorted(self.bars_by_symbol).index(ticker)
        for d in self.bars_by_symbol[ticker]:
            self.session.add(FactorValueModel(factor_id=self.fid, entity_id=entity_id, entity_type="CompanyShare",
                                              date=pd.Timestamp(d).to_pydatetime(), value="1.0"))
        self.session.commit()
        return pd.DataFrame()


def test_preload_imports_reports_coverage_and_registers_the_series():
    from src.application.services.data.backtest_preload.backtest_data_preload_service import (
        BacktestDataPreloadService,
        PreloadSeries,
    )
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    factory, session, engine = make_factory()
    try:
        full = pd.date_range("2026-10-05 09:30", "2026-10-05 15:50", freq="10min")       # 39 bars
        fake = _FakeImport(factory, session, {"JPM": list(full), "BAC": list(full[:30])})
        lines = []
        service = BacktestDataPreloadService(fake, log=lines.append)
        results = service.preload([PreloadSeries(CompanyShare, "JPM", "TRADES", "10 mins"),
                                   PreloadSeries(CompanyShare, "BAC", "TRADES", "10 mins"),
                                   PreloadSeries(CompanyShare, "ZZZ", "TRADES", "10 mins")],
                                  start="2026-10-05", end="2026-10-05 16:00")
        jpm, bac, zzz = results
        assert (jpm.expected_bars, jpm.stored_bars, jpm.coverage_pct) == (39, 39, 100.0)
        assert (bac.stored_bars, round(bac.coverage_pct, 1)) == (30, 76.9)
        assert zzz.error and not zzz.imported                                 # no entity: reported, others go on
        assert [c[0] for c in fake.calls] == ["JPM", "BAC"]
        assert fake.calls[0][1] == "10 mins" and fake.calls[0][2].endswith(" W") and fake.calls[0][3] == "TRADES"
        assert preloaded_coverage.covers(fake.fid, 100 + 1, datetime(2026, 10, 5, 12))   # JPM (sorted: BAC, JPM)
        assert lines[-1].startswith("[preload] 2/3 series loaded, 69/78 expected bars stored")
        frame = service.to_frame(results)
        assert list(frame["symbol"]) == ["JPM", "BAC", "ZZZ"] and frame.loc[2, "error"]
    finally:
        session.close()
        engine.dispose()


def test_import_duration_reaches_back_to_the_history_start():
    from src.application.services.data.backtest_preload.backtest_data_preload_service import (
        bar_minutes_of,
        import_duration,
    )
    assert import_duration("2026-09-15", "2026-10-22", "10 mins") == "6 W"
    assert import_duration("2024-11-01", "2026-10-22", "1 day") == "2 Y"
    assert (bar_minutes_of("10 mins"), bar_minutes_of("1 day")) == (10, None)


# ── the 10m algorithm logs where each bar's time went ───────────────────────────────────────────────────────────────

def test_the_10m_algorithm_records_cycle_orders_and_valuation(tmp_path):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.backtesting.base_project_algorithm import (
        TIMINGS_FILE,
        Algorithm,
    )
    algo = Algorithm.__new__(Algorithm)
    import logging
    algo.logger = logging.getLogger("test")
    algo.initialized = True
    algo.cycle_results = []
    algo.config = {"results_dir": str(tmp_path)}
    algo.portfolio_value = 1.0
    logged = []
    algo.progress_tracker = SimpleNamespace(log=logged.append, on_step=lambda *a: None)
    algo.cycle = SimpleNamespace(step=lambda t: SimpleNamespace(retrained=False, weights={"JPM": 0.1}, note="",
                                                               session=t, artifact_id=None))
    algo._unified_portfolio_manager = SimpleNamespace(set_holdings=lambda *a, **k: None)
    algo._update_portfolio_value = lambda data: None
    algo._update_performance_tracking = lambda data: None
    algo.log = lambda msg: None
    algo.step_timings = step_timings.StepTimings("2026-10-05 10:10:00")
    algo.on_data(SimpleNamespace(time=pd.Timestamp("2026-10-05 10:10")))
    assert logged and logged[0].startswith("[timing] 2026-10-05 10:10:00")
    row = pd.read_csv(tmp_path / TIMINGS_FILE).iloc[0]
    assert {"cycle_s", "orders_s", "valuation_s"} <= set(row.index)


def test_inside_a_preloaded_window_no_raw_value_is_fetched():
    from unittest.mock import MagicMock
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    factory = MagicMock()
    factory._available_repository_families = {"local": True, "ibkr": True}
    service = FactorValueResolutionService(factory=factory)
    service._create_factor_value = MagicMock()
    factor = SimpleNamespace(id=55, name="close", source="ibkr")
    entity = SimpleNamespace(id=7)
    preloaded_coverage.register(55, 7, datetime(2026, 9, 15), datetime(2026, 10, 9, 16))
    assert service._resolve_factor_without_dependencies(factor, entity, datetime(2026, 10, 5, 10, 25), "ibkr") is None
    factory.get_ibkr_repository.assert_not_called()                           # no data source was asked
    factory.factor_value_ibkr_repo.assert_not_called()


def test_the_preload_marks_every_raw_series_of_the_entity_as_loaded():
    from src.application.services.data.backtest_preload.backtest_data_preload_service import (
        BacktestDataPreloadService,
        PreloadSeries,
    )
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    factory, session, engine = make_factory()
    try:
        # another frequency and a refused type the valuation chain also reads
        others = [CompanyShareFactorModel(name="close", group="price", subgroup=sub, frequency=freq,
                                          data_type="numeric", source="ibkr", definition="close",
                                          factor_type="company_share_factor")
                  for sub, freq in (("TRADES", "5m"), ("MIDPOINT", "5m"))]
        session.add_all(others)
        session.commit()
        fake = _FakeImport(factory, session, {"JPM": list(pd.date_range("2026-10-05 09:30", periods=3, freq="10min"))})
        BacktestDataPreloadService(fake, log=lambda m: None).preload(
            [PreloadSeries(CompanyShare, "JPM", "TRADES", "10 mins")], start="2026-10-05", end="2026-10-05 16:00")
        noon = datetime(2026, 10, 5, 12)
        assert all(preloaded_coverage.covers(f.id, 100, noon) for f in others)
        assert preloaded_coverage.covers(fake.fid, 100, noon)
    finally:
        session.close()
        engine.dispose()
