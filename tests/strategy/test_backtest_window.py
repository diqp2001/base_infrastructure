"""
A backtest has ONE strategy and its own window (start, end, starting capital); a strategy can be backtested over
many windows (file SQLite, fake runner / manager; no IBKR, no SQL Server).
"""

import copy
import importlib
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.application.services.strategy.backtest_window import BacktestWindow, apply_window, default_window
from src.application.services.strategy.experiment_worker import run_experiment
from src.application.services.strategy.project_strategy_registration import ProjectStrategyRegistrar
from src.application.services.strategy.strategy_services import StrategyServices

STM_10M = "spatio_temporal_momentum_project_10m"


def _config(project):
    return copy.deepcopy(importlib.import_module(
        f"src.application.managers.project_managers.{project}.config").get_config())


# ── the window ───────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_window_keeps_the_projects_time_of_day_and_history_lead():
    base = _config(STM_10M)                     # 2026-10-05 09:40 .. 2026-10-09 16:00, history from 2026-09-15
    w = BacktestWindow(date(2026, 8, 3), date(2026, 8, 28), 250_000)
    native = apply_window(copy.deepcopy(base), w)
    assert (native["backtest_start"], native["backtest_end"]) == ("2026-08-03 09:40:00", "2026-08-28 16:00:00")
    lead = date(2026, 10, 5) - date(2026, 9, 15)
    assert native["price_history_start"] == (date(2026, 8, 3) - lead).isoformat()       # same lead, earlier
    assert native["initial_capital"] == 250_000 and native["Portfolio"]["initial_cash"] == 250_000
    later = apply_window(copy.deepcopy(base), BacktestWindow(date(2026, 10, 12), date(2026, 10, 16), 1e6))
    assert later["price_history_start"] == base["price_history_start"]                 # never later than its own
    assert default_window(base) == BacktestWindow(date(2026, 10, 5), date(2026, 10, 9), 1_000_000)


@pytest.mark.parametrize("start,end,capital", [("2026-06-01", "2026-05-01", "1000"), ("2026-06-01", "2026-06-01", "1"),
                                               ("2026-06-01", "2026-07-01", "0"), ("June", "2026-07-01", "1"),
                                               ("2026-06-01", "2026-07-01", "lots")])
def test_a_bad_window_is_refused(start, end, capital):
    with pytest.raises(ValueError):
        BacktestWindow.parse(start, end, capital)


# ── many backtests of one strategy ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def env(tmp_path, monkeypatch):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))
    engine = create_engine(f"sqlite:///{tmp_path / 'window.db'}")
    ModelBase.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    clock = SimpleNamespace(now=datetime(2026, 11, 19, 9))

    def tick():
        clock.now += timedelta(seconds=1)
        return clock.now
    runner = SimpleNamespace(started=[], start=lambda e: runner.started.append(e.id) or 4242)
    services = StrategyServices(sessions(), runner=runner, session_factory=sessions, results_root=tmp_path / "results",
                                clock=tick, is_alive=lambda pid: False, host="h")
    services.configurations.clock = tick
    yield SimpleNamespace(services=services, factory=RepositoryFactory(sessions()), tick=tick, runner=runner,
                          sessions=sessions, engine=engine)
    engine.dispose()


def _run(env, experiment, seen):
    def manager_factory(adapter, native, database_service):
        seen.append(native)
        return SimpleNamespace(run=lambda: {"success": True, "run_id": len(seen)}, runner=None)
    s = env.services
    return run_experiment(experiment.id, s.experiment_repository, s.strategy_repository, clock=env.tick, pid=1,
                          host="h", manager_factory=manager_factory)


def test_one_strategy_is_backtested_over_several_windows(env):
    s = env.services
    strategy = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    first = s.experiments.launch(strategy.id, window=BacktestWindow(date(2026, 8, 3), date(2026, 8, 28), 250_000))
    for e in s.experiments.active():                                            # one run at a time
        e.fail(env.tick(), "done")
        s.experiment_repository.update(e)
    second = s.experiments.launch(strategy.id, window=BacktestWindow(date(2026, 9, 1), date(2026, 9, 30), 1_000_000))
    assert first.strategy_id == second.strategy_id == strategy.id               # one strategy, many backtests
    assert [e.id for e in s.experiments.list(configuration_id=strategy.id)] == [first.id, second.id]
    assert (second.backtest_start, second.backtest_end, second.initial_capital) == (
        datetime(2026, 9, 1), datetime(2026, 9, 30), 1_000_000)
    seen = []
    done = _run(env, second, seen)
    assert done.status == "succeeded", done.error
    assert (seen[0]["backtest_start"], seen[0]["backtest_end"]) == ("2026-09-01 09:40:00", "2026-09-30 16:00:00")
    assert seen[0]["initial_capital"] == 1_000_000
    assert s.configurations.get(strategy.id).version == 1                      # the strategy itself never changed


def test_the_strategys_own_dates_are_the_default(env):
    s = env.services
    strategy = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    e = s.experiments.launch(strategy.id)
    assert (e.backtest_start, e.backtest_end, e.initial_capital) == (datetime(2026, 10, 5), datetime(2026, 10, 9),
                                                                    1_000_000)


def test_the_comparison_reads_each_backtests_window(env):
    s = env.services
    strategy = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    ids = []
    for start, end in ((date(2026, 8, 3), date(2026, 8, 28)), (date(2026, 9, 1), date(2026, 9, 30))):
        e = s.experiments.launch(strategy.id, window=BacktestWindow(start, end, 1_000_000))
        done = _run(env, e, [])
        ids.append(done.id)
    out = s.experiments.compare(ids)
    assert [r["period"] for r in out["rows"]] == ["2026-08-03 .. 2026-08-28", "2026-09-01 .. 2026-09-30"]
    assert any("backtest periods" in w for w in out["warnings"])


def test_a_form_strategy_checks_its_history_on_the_window(env):
    s = env.services
    c = s.configurations.create("csm window", "cross_sectional")
    s.configurations.validate(c.id)
    e = s.experiments.launch(c.id, window=BacktestWindow(date(2026, 3, 2), date(2026, 4, 30), 500_000))
    assert e.backtest_start == datetime(2026, 3, 2)
    seen = []

    def manager_factory(adapter, native, database_service):
        seen.append(native)
        table = __import__("pandas").DataFrame({"Sharpe": [1.0]}, index=["MODEL"])
        return SimpleNamespace(run=lambda: {"report": SimpleNamespace(model_name="MODEL", period=(), n_sessions=1,
                                                                      table_performance=table)}, runner=None)
    done = run_experiment(e.id, s.experiment_repository, s.strategy_repository, clock=env.tick, pid=1, host="h",
                          manager_factory=manager_factory)
    assert done.status == "succeeded", done.error
    assert seen[0]["backtest_start"].startswith("2026-03-02") and seen[0]["initial_capital"] == 500_000
    assert seen[0]["price_history_start"] < "2026-03-02"


def test_the_launch_page_takes_the_window(env, monkeypatch):
    from src.interfaces.flask.app import FlaskApp
    strategy = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    sessions, runner = env.sessions, env.runner

    def services():
        return StrategyServices(sessions(), runner=runner, session_factory=sessions, is_alive=lambda pid: False,
                                host="h", results_root=env.services.experiments.results_root)
    app = FlaskApp().get_app()
    app.config.update(STRATEGY_SERVICES_FACTORY=services, TESTING=True)
    client = app.test_client()
    page = client.get(f"/strategies/{strategy.id}").get_data(as_text=True)
    assert 'name="backtest_start"' in page and 'value="2026-10-05"' in page
    r = client.post(f"/strategies/{strategy.id}/launch", data={"confirm": "yes", "backtest_start": "2026-07-01",
                                                               "backtest_end": "2026-07-31",
                                                               "initial_capital": "300000"})
    assert r.status_code == 302
    experiment_id = int(re.search(r"/experiments/(\d+)", r.headers["Location"]).group(1))
    e = services().experiments.get(experiment_id)
    assert (e.backtest_start, e.backtest_end, e.initial_capital) == (datetime(2026, 7, 1), datetime(2026, 7, 31),
                                                                    300_000)
    assert "2026-07-01 .. 2026-07-31" in client.get("/strategies/").get_data(as_text=True)


def test_existing_backtest_tables_get_the_window_columns(tmp_path):
    from src.infrastructure.database.strategy_universe_migration import migrate, plan
    from src.infrastructure.models import ModelBase
    engine = create_engine(f"sqlite:///{tmp_path / 'cols.db'}")
    ModelBase.metadata.create_all(engine)
    with engine.begin() as conn:
        for column in ("backtest_start", "backtest_end", "initial_capital"):
            conn.execute(text(f"ALTER TABLE strategy_experiments DROP COLUMN {column}"))
    assert any("backtest window" in s for s in plan(engine).steps)
    migrate(engine, apply=True, backup=False)
    assert {"backtest_start", "backtest_end", "initial_capital"} <= {
        c["name"] for c in inspect(engine).get_columns("strategy_experiments")}
    assert not plan(engine).pending
    engine.dispose()
