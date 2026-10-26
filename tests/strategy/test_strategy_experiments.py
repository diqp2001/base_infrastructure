"""Strategy experiments, phase 2: launch, worker lifecycle, recovery, provenance; universe membership over time
(in-memory SQLite, temp dirs, a fake project manager; no IBKR, no SQL Server, no real process)."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.application.services.strategy.experiment_service import ExperimentConflict, JobRunner
from src.application.services.strategy.experiment_worker import portfolio_name, run_experiment, summarise
from src.application.services.strategy.strategy_services import StrategyServices


class FakeRunner:
    def __init__(self):
        self.started = []

    def start(self, experiment):
        self.started.append(experiment.id)
        return 4242


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 26, 9, 0)

    def __call__(self):
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def env(tmp_path, monkeypatch):
    from src.infrastructure.models import ModelBase
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))        # job records stay out of .monitor/
    engine = create_engine(f"sqlite:///{tmp_path / 'strategy.db'}")
    ModelBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    clock = Clock()
    alive = set()
    runner = FakeRunner()
    services = StrategyServices(factory(), runner=runner, session_factory=factory, results_root=tmp_path / "results",
                                clock=clock, is_alive=lambda pid: pid in alive, host="test-host")
    services.configurations.clock = clock
    yield SimpleNamespace(services=services, clock=clock, alive=alive, runner=runner, tmp=tmp_path)
    services.session.close()
    engine.dispose()


def _configuration(services, name="csm exp", **sections):
    c = services.configurations.create(name, "cross_sectional", sections or None)
    return c


class FakeManager:
    """Stands for a project manager: returns a report-like result and an algorithm with cycle results."""

    def __init__(self, native, fail=None):
        self.native = native
        self.fail = fail
        decisions = [SimpleNamespace(session=pd.Timestamp("2026-06-01"), eligible=["JPM", "BAC"], artifact_id=7,
                                     retrained=True),
                     SimpleNamespace(session=pd.Timestamp("2026-06-02"), eligible=["JPM"], artifact_id=None,
                                     retrained=False)]
        cycle = SimpleNamespace(ticker_to_entity={"JPM": 1, "BAC": 2}, universe_id=3)
        self.runner = SimpleNamespace(algorithm_instance=SimpleNamespace(cycle=cycle, cycle_results=decisions))

    def run(self):
        if self.fail:
            raise RuntimeError(self.fail)
        table = pd.DataFrame({"Sharpe": [1.2, 0.4], "E[Return]": [0.1, 0.05]}, index=["MODEL", "Long Only (EW)"])
        report = SimpleNamespace(model_name="MODEL", period=("2026-06-01", "2026-06-02"), n_sessions=2,
                                 table_performance=table, coverage_summary=pd.DataFrame(
                                     {"Value": {"Coverage % — backtest": 99.5}}))
        return {"report": report, "retrainings": [("2026-06-01", 7)]}


def test_launch_locks_the_configuration_and_starts_one_worker(env):
    s = env.services
    c = _configuration(s)
    e = s.experiments.launch(c.id)
    assert (e.status, e.pid, e.project_key, e.configuration_hash) == ("queued", 4242, "cross_sectional",
                                                                      s.configurations.get(c.id).content_hash)
    assert s.configurations.get(c.id).status == "locked"
    assert e.results_dir.endswith(f"experiment_{e.id}") and e.log_path.endswith("worker.log")
    assert env.runner.started == [e.id]
    env.alive.add(4242)
    with pytest.raises(ExperimentConflict):                                    # one run at a time (IBKR client)
        s.experiments.launch(_configuration(s, "other").id)
    with pytest.raises(ValueError):
        s.experiments.launch(c.id, kind="live")                                # never from this interface


def test_an_invalid_configuration_is_never_launched(env):
    s = env.services
    c = _configuration(s, evaluation={"price_history_start": "2026-05-01"})
    from src.application.services.strategy.configuration_service import ConfigurationInvalid
    with pytest.raises(ConfigurationInvalid):
        s.experiments.launch(c.id)
    assert s.experiments.list() == [] and env.runner.started == []


def test_a_dead_or_never_started_worker_is_marked_interrupted(env):
    s = env.services
    e = s.experiments.launch(_configuration(s).id)
    env.clock.now += timedelta(minutes=10)                                     # worker never reported in
    s.experiments.recover()
    assert s.experiments.get(e.id).status == "interrupted"
    e2 = s.experiments.launch(_configuration(s, "second").id)
    run = s.experiment_repository.get_by_id(e2.id)
    run.start(999, "test-host", env.clock())
    s.experiment_repository.update(run)
    env.alive.add(999)
    s.experiments.recover()
    assert s.experiments.get(e2.id).status == "running"                        # alive: untouched
    env.alive.discard(999)
    s.experiments.recover()
    got = s.experiments.get(e2.id)
    assert got.status == "interrupted" and "no longer running" in got.error


def test_the_worker_runs_the_project_and_records_results_and_provenance(env):
    s = env.services
    c = _configuration(s)
    e = s.experiments.launch(c.id)
    seen = {}

    def manager_factory(adapter, native, database_service):
        seen["native"] = native
        return FakeManager(native)

    done = run_experiment(e.id, s.experiment_repository, s.configuration_repository, clock=env.clock, pid=777,
                          host="test-host", manager_factory=manager_factory)
    assert done.status == "succeeded" and done.pid == 777
    assert seen["native"]["results_dir"] == e.results_dir                      # its own folder
    assert seen["native"]["Portfolio"]["name"] == portfolio_name("Cross_Sectional_Momentum_Portfolio", e.id)
    assert done.summary["metrics"]["Sharpe"] == 1.2 and done.summary["benchmarks"]["Long Only (EW)"]["Sharpe"] == 0.4
    assert done.summary["coverage"]["Coverage % — backtest"] == 99.5
    p = done.provenance
    assert p["artifacts"] == [7] and p["retrainings"] == [["2026-06-01", 7]]
    assert p["universe"]["tickers"] == ["JPM", "BAC"] and p["universe"]["universe_id"] == 3
    assert p["eligible_per_decision"]["2026-06-02 00:00:00"] == ["JPM"]
    assert p["configuration"] == {"name": "csm exp", "version": 1}


def test_a_failing_run_is_recorded_as_failed_with_its_error(env):
    s = env.services
    e = s.experiments.launch(_configuration(s).id)
    done = run_experiment(e.id, s.experiment_repository, s.configuration_repository, clock=env.clock,
                          manager_factory=lambda a, n, d: FakeManager(n, fail="TWS is not connected"))
    assert done.status == "failed" and "TWS is not connected" in done.error


def test_a_configuration_changed_after_launch_is_not_run(env):
    s = env.services
    c = _configuration(s)
    e = s.experiments.launch(c.id)
    row = s.experiment_repository.get_by_id(e.id)
    row.configuration_hash = "0" * 64                                          # what was launched is not this
    s.experiment_repository.update(row)
    done = run_experiment(e.id, s.experiment_repository, s.configuration_repository, clock=env.clock,
                          manager_factory=lambda a, n, d: FakeManager(n))
    assert done.status == "failed" and "changed after the experiment was launched" in done.error


def test_the_worker_command_runs_the_worker_module():
    e = SimpleNamespace(id=12)
    assert JobRunner(python="py").command(e) == ["py", "-m", "src.application.services.strategy.experiment_worker",
                                                 "12"]


def test_summarise_reads_the_stm_report_table_too():
    table = pd.DataFrame({"Sharpe": [0.9]}, index=["TFT"])
    out = summarise(SimpleNamespace(model_name="TFT", period=("a", "b"), n_sessions=5, table_raw=table))
    assert out["metrics"] == {"Sharpe": 0.9} and out["decisions"] == 5


# ── universe membership over time ────────────────────────────────────────────────────────────────────────────────

def test_a_member_that_leaves_the_list_is_ended_and_one_that_returns_starts_again():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
        STMUniverseConfig,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
        STMUniverseService,
    )
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from unittest.mock import patch
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=None):
        factory = RepositoryFactory(Session(engine))
    service = STMUniverseService(factory, STMUniverseConfig(name="u", tickers=None))
    service.ensure_universe({"CADE": 1, "JPM": 2}, start_date=date(2024, 1, 2), today=date(2026, 10, 1))
    service.ensure_universe({"HWC": 3, "JPM": 2}, start_date=date(2024, 1, 2), today=date(2026, 10, 22))
    assert service.active_entity_ids(date(2026, 1, 5)) == [1, 2, 3]      # history kept: CADE was a member then
    assert service.active_entity_ids(date(2026, 10, 26)) == [2, 3]       # CADE ended 2026-10-22
    service.ensure_universe({"CADE": 1, "JPM": 2, "HWC": 3}, start_date=date(2024, 1, 2), today=date(2026, 11, 2))
    assert service.active_entity_ids(date(2026, 10, 26)) == [2, 3]       # not a member between 10-22 and 11-02
    assert service.active_entity_ids(date(2026, 11, 3)) == [1, 2, 3]
    service.ensure_universe({"CADE": 1, "JPM": 2, "HWC": 3}, start_date=date(2024, 1, 2), today=date(2026, 11, 9))
    rows = factory.universe_constituent_local_repo.get_by_universe(
        factory.investment_universe_local_repo.get_by_name("u").id)
    assert len(rows) == 4                                                # registering again changes nothing
    factory.session.close()
    engine.dispose()
