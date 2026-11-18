"""Generic research / backtest registry (2026-11-18): run identity, lifecycle and PARTIAL runs, run -> portfolios,
model registry (one model, many runs and universes), research series and metrics, comparability, the read-only API
and pages, and the BaseBacktestRunner integration. In memory (SQLite): no IBKR, no SQL Server."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import text

from src.application.services.backtest_registry.backtest_run_service import BacktestRunService
from src.application.services.backtest_registry.model_registry_service import ModelRegistryService
from src.application.services.backtest_registry.research_query_service import ResearchQueryService
from src.application.services.backtest_registry.research_result_service import ResearchResultService
from src.application.services.backtest_registry.run_identity import GitState
from src.domain.entities.backtest.backtest_run import (CANCELLED, COMPLETED, FAILED, PARTIAL, PENDING, RUNNING,
                                                       BacktestRun, months_between)
from src.domain.entities.backtest.run_comparison import compare_runs
from tests.spatio_temporal_momentum.helpers import make_factory

T0 = datetime(2026, 11, 18, 9, 0)


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def world():
    factory, session, engine = make_factory()
    clock = Clock()
    service = BacktestRunService(factory, clock=clock, git=lambda: GitState(commit="abc123", dirty=False),
                                 branch=lambda: "main")
    yield SimpleNamespace(factory=factory, session=session, service=service, clock=clock,
                          results=ResearchResultService(factory), models=ModelRegistryService(factory),
                          query=ResearchQueryService(factory))
    session.close()
    engine.dispose()


def config(**over):
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    base = {"project_name": "stm_monthly_deciles", "universe": {CompanyShare: ["AAPL", "MSFT"]},
            "initial_capital": 1_000_000, "backtest_start": "2021-01-04", "backtest_end": "2026-10-30",
            "Portfolio": {"name": "P", "initial_cash": 1_000_000, "password": "never stored"},
            "deciles": {"research_price_series": "ADJUSTED_LAST"}}
    base.update(over)
    return base


def register(world, cfg=None, start=datetime(2021, 1, 4, 16), end=datetime(2026, 10, 30, 16), **describe):
    run = world.service.register((cfg or config())["project_name"], cfg or config(), requested_start=start,
                                 requested_end=end, describe=describe)
    return world.service.start(run)


def walk(world, run, until, start=datetime(2021, 1, 4, 16)):
    tracker = world.service.tracker(run, flush_seconds=0)
    for day in pd.bdate_range(start, until):
        tracker.bar(day.to_pydatetime().replace(hour=16))
    tracker.flush()
    return tracker.run


# ---------------------------------------------------------------- identity and configuration
def test_every_run_gets_its_own_identity(world):
    a, b = register(world), register(world)
    assert a.id != b.id and a.run_uid != b.run_uid
    assert a.project_name == b.project_name == "stm_monthly_deciles"
    assert {r.id for r in world.factory.backtest_run_local_repo.find(project_name="stm_monthly_deciles")} == {a.id,
                                                                                                             b.id}


def test_the_whole_configuration_and_the_commit_are_stored(world):
    run = register(world)
    stored = world.factory.backtest_run_local_repo.get_by_id(run.id)
    assert stored.config_snapshot["universe"] == {"CompanyShare": ["AAPL", "MSFT"]}
    assert stored.config_snapshot["deciles"]["research_price_series"] == "ADJUSTED_LAST"
    assert stored.config_snapshot["Portfolio"]["password"] == "***"            # credentials never stored
    assert stored.code_commit == "abc123" and stored.code_branch == "main" and stored.code_dirty is False
    assert len(stored.config_hash) == 64 and stored.starting_capital == 1_000_000
    assert stored.universe_description == "CompanyShare: 2 names" and stored.months_planned == 69


# ---------------------------------------------------------------- status
def test_pending_running_completed(world):
    run = world.service.register("p", config(), requested_start=datetime(2021, 1, 4, 16),
                                 requested_end=datetime(2021, 3, 31, 16))
    assert run.status == PENDING
    run = world.service.start(run)
    assert run.status == RUNNING and run.started_at == T0
    run = walk(world, run, datetime(2021, 3, 31))
    run = world.service.finish(run)
    assert run.status == COMPLETED and run.months_completed == run.months_planned == 2
    assert world.factory.backtest_run_local_repo.get_by_id(run.id).status == COMPLETED


def test_an_early_stop_is_partial_never_completed(world):
    run = walk(world, register(world), datetime(2022, 12, 9))              # the 2026-11-17 decile run
    run = world.service.finish(run)                                         # the engine returned normally
    assert run.status == PARTIAL
    assert (run.months_completed, run.months_planned) == (23, 69) and run.progress_label() == "23 / 69 months"
    assert "stopped after 23 of 69 months" in run.error
    assert run.actual_start.date().isoformat() == "2021-01-04" and run.actual_end.date().isoformat() == "2022-12-09"


def test_failures_and_cancellation(world):
    no_bar = world.service.finish(register(world), error="RuntimeError: setup failed")
    assert no_bar.status == FAILED and "setup failed" in no_bar.error
    some = world.service.finish(walk(world, register(world), datetime(2021, 6, 30)), error="boom")
    assert some.status == PARTIAL and some.months_completed == 5
    cancelled = world.service.finish(walk(world, register(world), datetime(2021, 2, 26)), cancelled=True)
    assert cancelled.status == CANCELLED
    again = world.service.finish(cancelled)                                 # a finished run is never re-finished
    assert again.status == CANCELLED


def test_a_run_whose_worker_is_gone_is_closed(world):
    run = walk(world, register(world), datetime(2021, 4, 30))
    world.clock.t = T0 + timedelta(hours=2)
    closed = world.service.recover(alive=lambda pid: False)
    assert [r.id for r in closed] == [run.id]
    stored = world.factory.backtest_run_local_repo.get_by_id(run.id)
    assert stored.status == PARTIAL and "worker gone" in stored.error


def test_months_between():
    assert months_between("2021-01-04", "2022-12-09") == 23 and months_between("2021-01-04", "2026-10-30") == 69
    assert months_between("2021-01-04", "2020-01-01") == 0


# ---------------------------------------------------------------- portfolios
def add_portfolio(world, pid, name):
    world.session.execute(text("INSERT INTO portfolios (id, name, start_date) VALUES (:i, :n, '2021-01-01')"),
                          {"i": pid, "n": name})


def hold(world, container, asset, kind):
    world.session.execute(text("INSERT INTO holdings (holding_type, asset_id, container_id, start_date) "
                               "VALUES (:k, :a, :c, '2021-01-04')"), {"k": kind, "a": asset, "c": container})
    world.session.commit()


def test_a_run_owns_several_portfolios_and_never_another_runs(world):
    for pid, name in ((10, "P_run1"), (11, "P_run1_cash"), (12, "P_run1_CS"), (20, "P_run2")):
        add_portfolio(world, pid, name)
    hold(world, 10, 11, "CurrencyPortfolioPortfolioHoldings")
    hold(world, 10, 12, "CompanySharePortfolioPortfolioHoldings")
    hold(world, 12, 99, "CompanySharePortfolioHoldings")                   # a share: not a portfolio
    a, b = register(world), register(world)
    assert world.service.register_portfolio_tree(a, 10) == [10, 11, 12]
    world.service.register_portfolio(b, 20)
    links = world.factory.backtest_run_portfolio_local_repo
    assert {(p.portfolio_id, p.role) for p in links.get_by_run(a.id)} == {(10, "main"), (11, "sub"), (12, "sub")}
    assert [p.portfolio_id for p in links.get_by_run(b.id)] == [20]
    with pytest.raises(ValueError):
        world.service.register_portfolio(b, 10)                             # portfolio 10 belongs to run a


# ---------------------------------------------------------------- model registry
def test_models_are_reusable_across_runs_and_universes(world):
    a = world.models.register_model("stm_A", "tft", configuration={"features": ["r1", "r3"],
                                                                  "hyperparameters": {"hidden_dim": 16},
                                                                  "training_frequency": "monthly"})
    b = world.models.register_model("stm_B", "tft", configuration={"features": ["r1", "r3", "fund_roe"]})
    assert a.id != b.id and world.models.register_model("stm_A", "tft", configuration=a.configuration).id == a.id
    us = register(world, universe_description="US equities")
    ca = register(world, universe_description="Canadian equities")
    world.service.link_model(us, a.id, role="A (traded)")
    world.service.link_model(ca, a.id)
    world.service.link_model(us, b.id, role="B")
    described = world.models.describe(a.id)
    assert {r["universe"] for r in described["runs"]} == {"US equities", "Canadian equities"}
    assert [f["name"] for f in described["features"]] == ["r1", "r3"]
    assert described["hyperparameters"] == {"hidden_dim": 16} and described["training_frequency"] == "monthly"
    assert described["algorithm"] == "tft" and described["status"] == "registered"
    listed = {m["name"]: m["runs"] for m in world.models.list_models()}
    assert listed["stm_A"] == 2 and listed["stm_B"] == 1


# ---------------------------------------------------------------- research results
def test_arbitrary_named_series_and_metrics(world):
    run = register(world)
    idx = pd.to_datetime(["2021-01-29", "2021-02-26", "2021-03-31"])
    frame = pd.DataFrame({"D1": [0.01, -0.02, 0.0], "D10": [0.03, 0.01, float("nan")]}, index=idx)
    assert world.results.publish_frame(run.id, frame, group="A/gross", prefix="A/gross/") == 6
    world.results.publish_series(run.id, "unused_premium", pd.Series([120.0, 80.0], index=idx[:2]), group="disp")
    world.results.publish_frame(run.id, frame.iloc[:2], group="A/gross", prefix="A/gross/")    # republish replaces
    series = {s["name"]: s for s in world.query.series(run.id)["series"]}
    assert set(series) == {"A/gross/D1", "A/gross/D10", "unused_premium"}
    assert [p["value"] for p in series["A/gross/D10"]["points"]] == [0.03, 0.01]
    world.results.publish_metrics(run.id, {"D10-D1.sharpe_ratio": 0.8, "note": "text ignored"}, scope="A/gross")
    world.results.publish_metrics(run.id, {"D10-D1.sharpe_ratio": 0.9}, scope="A/gross")
    assert world.query.metrics(run.id) == {"A/gross": {"D10-D1.sharpe_ratio": 0.9}}


def portfolio_values(world, portfolio_id, values, start="2021-01-04"):
    from src.infrastructure.models.factor.factor import FactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = world.session.query(FactorModel).filter(FactorModel.factor_type == "portfolio_value_factor").first()
    if factor is None:
        world.session.execute(text("INSERT INTO factors (name, \"group\", subgroup, frequency, data_type, source, "
                                   "definition, factor_type) VALUES ('Portfolio Value', 'value', 'daily', '1d', "
                                   "'numeric', 'calculated', 'v', 'portfolio_value_factor')"))
        world.session.commit()
        factor = world.session.query(FactorModel).filter(FactorModel.factor_type == "portfolio_value_factor").first()
    for d, v in zip(pd.bdate_range(start, periods=len(values)), values):
        world.session.add(FactorValueModel(factor_id=factor.id, entity_id=portfolio_id, entity_type="PortfolioModel",
                                           date=d.to_pydatetime().replace(hour=16), value=str(v)))
    world.session.commit()


def test_engine_metrics_come_from_the_portfolio_value_curve(world):
    add_portfolio(world, 30, "P_run")
    run = register(world)
    world.service.register_portfolio(run, 30)
    portfolio_values(world, 30, [100.0, 110.0, 99.0, 108.9])
    from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics
    m = world.results.engine_metrics(run.id, calculate_performance_metrics, starting_capital=100.0)
    assert m["cumulative_return"] == pytest.approx(0.089) and m["max_drawdown"] == pytest.approx(-0.1)
    assert world.query.metrics(run.id)["engine"]["final_value"] == pytest.approx(108.9)
    curve = world.query.equity(run.id)["portfolios"][0]["points"]
    assert [p["value"] for p in curve] == [100.0, 110.0, 99.0, 108.9]


# ---------------------------------------------------------------- comparison
def test_comparison_reports_differences_and_warnings(world):
    a = world.service.finish(walk(world, register(world, universe_description="US equities", price_source="TRADES"),
                                  datetime(2026, 10, 30)))
    b = world.service.finish(walk(world, register(world, config(initial_capital=500_000),
                                                  universe_description="Canadian equities",
                                                  price_source="ADJUSTED_LAST"), datetime(2022, 12, 9)))
    result = compare_runs([a, b])
    fields = {d.field for d in result.differences}
    assert {"universe_description", "price_source", "starting_capital"} <= fields
    assert any("Universes differ" in w for w in result.warnings)
    assert any("Price sources differ" in w for w in result.warnings)
    assert any(f"Run {b.id} is PARTIAL (23 / 69 months)" in w for w in result.warnings)
    assert "initial_capital" in {d.field for d in result.config_differences}
    assert not result.comparable
    same = compare_runs([a, world.service.finish(walk(world, register(world, universe_description="US equities",
                                                                      price_source="TRADES"),
                                                      datetime(2026, 10, 30)))])
    assert same.comparable and same.warnings == []
    with pytest.raises(ValueError):
        compare_runs([a])


def test_compare_through_the_query_service(world):
    add_portfolio(world, 40, "A")
    add_portfolio(world, 41, "B")
    a, b = register(world, universe_description="US equities"), register(world, universe_description="Europe")
    world.service.register_portfolio(a, 40)
    world.service.register_portfolio(b, 41)
    portfolio_values(world, 40, [100.0, 101.0, 102.0])
    portfolio_values(world, 41, [50.0, 49.0, 51.0])
    from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics
    for run in (a, b):
        world.results.engine_metrics(run.id, calculate_performance_metrics)
    out = world.query.compare([a.id, b.id])
    assert out["equity"][0]["points"][0]["value"] == 1.0 and out["equity"][1]["points"][-1]["value"] == 1.02
    names = [m["name"] for m in out["metrics"]]
    assert names[:2] == ["cumulative_return", "annualized_return"]
    assert any("Universes differ" in w for w in out["warnings"])
    with pytest.raises(LookupError):
        world.query.compare([a.id, 999])


# ---------------------------------------------------------------- API and pages
@pytest.fixture
def client(world):
    from src.interfaces.flask.research_app import create_app
    app = create_app(services_factory=lambda: ResearchQueryService(world.factory))
    app.config["TESTING"] = True
    return app.test_client()


def test_api_and_pages(world, client):
    add_portfolio(world, 50, "P_run")
    model = world.models.register_model("stm_A", "tft", configuration={"features": ["r1"]})
    a = walk(world, register(world, universe_description="US equities"), datetime(2022, 12, 9))
    a = world.service.finish(a)
    world.service.register_portfolio(a, 50)
    world.service.link_model(a, model.id, role="A")
    portfolio_values(world, 50, [100.0, 101.0])
    world.results.publish_series(a.id, "A/gross/D10-D1", {"2021-01-29": 0.01, "2021-02-26": -0.005}, group="A/gross")
    b = world.service.finish(walk(world, register(world, universe_description="Canada"), datetime(2026, 10, 30)))

    runs = client.get("/api/backtests").get_json()
    assert {r["id"] for r in runs} == {a.id, b.id}
    partial = next(r for r in runs if r["id"] == a.id)
    assert partial["status"] == "PARTIAL" and partial["months_completed"] == 23 and partial["months_planned"] == 69
    assert client.get("/api/backtests?status=PARTIAL").get_json()[0]["id"] == a.id
    assert [r["id"] for r in client.get(f"/api/backtests?model_id={model.id}").get_json()] == [a.id]
    detail = client.get(f"/api/backtests/{a.id}").get_json()
    assert detail["portfolios"][0]["portfolio_id"] == 50 and detail["models"][0]["name"] == "stm_A"
    assert client.get(f"/api/backtests/{a.id}/equity").get_json()["portfolios"][0]["points"][1]["value"] == 101.0
    assert client.get(f"/api/backtests/{a.id}/series").get_json()["series"][0]["name"] == "A/gross/D10-D1"
    assert client.get(f"/api/backtests/{a.id}/metrics").status_code == 200
    cmp = client.get(f"/api/backtests/compare?run_ids={a.id},{b.id}").get_json()
    assert any("PARTIAL" in w for w in cmp["warnings"]) and any("Universes differ" in w for w in cmp["warnings"])
    assert client.get(f"/api/backtests/compare?run_ids={a.id}").status_code == 400
    assert client.get("/api/backtests/999").status_code == 404
    assert client.get("/api/models").get_json()[0]["name"] == "stm_A"
    assert client.get(f"/api/models/{model.id}/runs").get_json()[0]["universe"] == "US equities"
    assert client.get(f"/api/models/{model.id}/artifacts").get_json() == []

    for url in ("/research/", "/research/?status=PARTIAL", f"/research/runs/{a.id}",
                f"/research/compare?run_ids={a.id},{b.id}", "/research/compare", "/research/models",
                f"/research/models/{model.id}"):
        page = client.get(url)
        assert page.status_code == 200, url
    run_page = client.get(f"/research/runs/{a.id}").get_data(as_text=True)
    assert "PARTIAL" in run_page and "23 / 69 months" in run_page and "A/gross/D10-D1" in run_page
    compare_page = client.get(f"/research/compare?run_ids={a.id},{b.id}").get_data(as_text=True)
    assert "Universes differ" in compare_page
    assert client.post("/api/backtests").status_code == 405                # read only


def test_the_web_session_refuses_writes():
    from sqlalchemy import create_engine
    from src.application.services.backtest_registry.read_access import query_service_factory
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import (
        ReadOnlyViolation,
        guard_read_only,
    )
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    service = query_service_factory(guard_read_only(engine))()
    assert service.list_runs() == []
    with pytest.raises(Exception) as excinfo:
        service.factory.backtest_run_local_repo.add(BacktestRun(project_name="x"))
    assert isinstance(excinfo.value, ReadOnlyViolation) or "read-only" in str(excinfo.value)


# ---------------------------------------------------------------- BaseBacktestRunner integration
class _Runner:
    """BaseBacktestRunner's registry hooks on an in-memory database (no Misbuffet engine launch)."""

    def __new__(cls, session):
        from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

        class Runner(BaseBacktestRunner):
            def setup_components(self, config):
                return True

            def create_algorithm_instance(self):
                return None

            def describe_run(self, config):
                return {"universe_description": "test universe", "price_source": "TRADES"}
        return Runner(SimpleNamespace(session=session))


def test_the_runner_registers_tracks_and_closes_the_run(world, monkeypatch):
    from src.application.services.backtest_registry import run_identity
    monkeypatch.setattr(run_identity, "git_state", lambda *a, **k: GitState(commit="def456", dirty=True))
    add_portfolio(world, 60, "P_run")
    runner = _Runner(world.session)
    cfg = runner._register_run(config(), datetime(2021, 1, 4, 16), datetime(2021, 3, 31, 16))
    assert runner.run is not None and runner.run.status == RUNNING
    assert cfg["Portfolio"]["name"] == f"P_run{runner.run.id}"                # its own book
    assert config()["Portfolio"]["name"] == "P"                              # the caller's config is untouched
    seen = []
    algorithm = SimpleNamespace(on_data=lambda data: seen.append(data.time),
                                _current_portfolio_entity=SimpleNamespace(id=60, name="P_run"),
                                cycle_results=[])
    runner.algorithm_instance = algorithm
    runner._track_bars(algorithm)
    for day in pd.bdate_range("2021-01-04", "2021-02-26"):
        algorithm.on_data(SimpleNamespace(time=day.to_pydatetime().replace(hour=16)))
    assert len(seen) == 40
    runner._finish_run()
    stored = world.factory.backtest_run_local_repo.get_by_id(runner.run.id)
    assert stored.status == PARTIAL and stored.months_completed == 1 and stored.months_planned == 2
    assert stored.code_commit == "def456" and stored.code_dirty is True
    assert stored.universe_description == "test universe" and stored.price_source == "TRADES"
    assert [p.portfolio_id for p in world.factory.backtest_run_portfolio_local_repo.get_by_run(stored.id)] == [60]
    second = _Runner(world.session)
    cfg2 = second._register_run(config(), datetime(2021, 1, 4, 16), datetime(2021, 3, 31, 16))
    assert second.run.id != runner.run.id and cfg2["Portfolio"]["name"] != cfg["Portfolio"]["name"]


def test_the_registry_can_be_turned_off_and_never_breaks_a_backtest(world):
    runner = _Runner(world.session)
    cfg = runner._register_run(config(run_registry={"enabled": False}), datetime(2021, 1, 4), datetime(2021, 3, 31))
    assert runner.run is None and cfg["Portfolio"]["name"] == "P"
    broken = _Runner(SimpleNamespace(get_bind=None))                         # no usable database
    cfg = broken._register_run(config(), datetime(2021, 1, 4), datetime(2021, 3, 31))
    assert broken.run is None and cfg["Portfolio"]["name"] == "P"
    broken._finish_run()                                                      # nothing to do, no error
