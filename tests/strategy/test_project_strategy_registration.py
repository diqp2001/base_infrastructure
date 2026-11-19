"""
Every project under project_managers registers its Strategy (and the Strategy's Universe) when it runs
(file SQLite only; no IBKR, no SQL Server, no engine run).
"""

import importlib
import inspect
import logging
import pathlib
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.strategy.project_strategy_registration import (
    RUN_KEYS,
    ProjectStrategyRegistrar,
    project_key_of,
    register_project_strategy,
    strategy_sections,
    universe_request,
)
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "src" / "application" / "managers" / "project_managers"
PACKAGE = "src.application.managers.project_managers"
PROJECTS = sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and (p / "__init__.py").exists()
                  and p.name != "__pycache__")
CONFIGURED = [p for p in PROJECTS if (PROJECTS_DIR / p / "config.py").exists()
              and "def get_config" in (PROJECTS_DIR / p / "config.py").read_text(encoding="utf-8")]


@pytest.fixture
def factory(tmp_path):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    engine = create_engine(f"sqlite:///{tmp_path / 'projects.db'}")
    ModelBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield RepositoryFactory(session)
    session.close()
    engine.dispose()


def _config(project):
    module = importlib.import_module(f"{PACKAGE}.{project}.config")
    return module.get_config()


# ── every project is wired ───────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("project", PROJECTS)
def test_every_project_registers_its_strategy_when_it_runs(project):
    """Runs go through BaseBacktestRunner (registration built in) or call the registrar themselves; base_project is
    the template whose subclasses supply a BaseBacktestRunner."""
    from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner
    if project == "base_project":
        source = (PROJECTS_DIR / project / "project_manager.py").read_text(encoding="utf-8")
        assert "BaseBacktestRunner as BacktestRunner" in source
        return
    runners, registers = [], False
    for path in (PROJECTS_DIR / project).rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        registers = registers or "register_with_database" in text or "_register_strategy" in text
        if "Runner" in text and path.parent.name == "backtesting":
            module = importlib.import_module(
                ".".join(path.relative_to(ROOT).with_suffix("").parts))
            runners += [c for _, c in inspect.getmembers(module, inspect.isclass)
                        if c.__module__ == module.__name__ and c.__name__.endswith("Runner")]
    assert registers or any(issubclass(c, BaseBacktestRunner) for c in runners), project
    for runner in runners:
        assert project_key_of(f"{runner.__module__}") == project


@pytest.mark.parametrize("project", CONFIGURED)
def test_each_projects_config_defines_a_strategy(project, factory):
    config = _config(project)
    sections = strategy_sections(config)
    assert not (set(config) & RUN_KEYS & {k for s in sections.values() for k in s}), "run keys leaked"
    flat = repr(sections)
    for secret in ("DUR314497", "U11494855", "client_id", "7497"):
        assert secret not in flat, f"deployment setting {secret} in the strategy"
    strategy = ProjectStrategyRegistrar(factory).ensure(project, config)
    assert (strategy.name, strategy.strategy_type, strategy.version, strategy.status) == (project, project, 1,
                                                                                         "locked")
    again = factory.strategy_local_repo.get_by_id(strategy.id)
    assert again.sections == strategy.sections and again.content_hash == strategy.content_hash
    if universe_request(config):
        assert strategy.universe_id is not None
        assert strategy.section("universe")["instruments"] == universe_request(config)
    # running again with the same config reuses it
    assert ProjectStrategyRegistrar(factory).ensure(project, _config(project)).id == strategy.id


def test_the_live_projects_deployment_is_not_part_of_its_strategy(factory):
    config = _config("spatio_temporal_momentum_project_10m_live")
    strategy = ProjectStrategyRegistrar(factory).ensure("spatio_temporal_momentum_project_10m_live", config)
    assert "live" not in repr(strategy.sections.keys()) and "supervisor" not in repr(strategy.sections)
    assert (strategy.bar_size, strategy.bar_frequency, strategy.model_type, strategy.retrain_every_days,
            strategy.prediction_horizon) == ("10 mins", "10m", "tft", 2, 1)
    assert strategy.training_window == config["training_window"]


def test_run_settings_never_make_a_new_version(factory):
    config = _config("stm_monthly_decile_project")
    first = ProjectStrategyRegistrar(factory).ensure("stm_monthly_decile_project", config)
    rerun = {**config, "backtest_start": "2001-01-01", "backtest_end": "2002-01-01", "initial_capital": 1,
             "results_dir": "elsewhere", "run_name": "x",
             "Portfolio": {**config["Portfolio"], "name": "other_book_run7", "initial_cash": 5}}
    assert ProjectStrategyRegistrar(factory).ensure("stm_monthly_decile_project", rerun).id == first.id


def test_a_changed_config_is_a_new_version_and_a_new_universe_only_when_instruments_change(factory):
    project = "spatio_temporal_momentum_project_10m"
    config = _config(project)
    v1 = ProjectStrategyRegistrar(factory).ensure(project, config)
    v2 = ProjectStrategyRegistrar(factory).ensure(project, {**config, "retrain_every_days": 5})
    assert (v2.version, v2.parent_id, v2.retrain_every_days, v2.universe_id) == (2, v1.id, 5, v1.universe_id)
    fewer = {**config, "universe": {CompanyShare: ["JPM", "BAC"]}}
    v3 = ProjectStrategyRegistrar(factory).ensure(project, fewer)
    assert v3.version == 3 and v3.universe_id != v1.universe_id
    universes = factory.universe_local_repo
    assert [universes.get_by_id(s.universe_id).version for s in (v1, v3)] == [1, 2]
    assert factory.strategy_local_repo.get_by_id(v1.id).status == "locked"        # v1 still what it was


def test_the_universe_fills_in_as_the_instruments_are_stored(factory):
    project = "stm_monthly_decile_project"
    config = {**_config(project), "universe": {CompanyShare: ["JPM", "GS", "BAC"]}}
    strategy = ProjectStrategyRegistrar(factory).ensure(project, config)
    universe = factory.universe_local_repo.get_by_id(strategy.universe_id)
    assert universe.financial_asset_ids() == []                       # nothing stored yet
    ids = {}
    for symbol in ("JPM", "GS"):                                       # the run creates two of them
        ids[symbol] = factory.company_share_local_repo.add(CompanyShare(
            id=None, symbol=symbol, exchange_id=1, company_id=1, currency_id=1, start_date=date(2020, 1, 1))).id
    ProjectStrategyRegistrar(factory).sync_universe(strategy)
    universe = factory.universe_local_repo.get_by_id(strategy.universe_id)
    assert sorted(universe.financial_asset_ids()) == sorted(ids.values())
    ProjectStrategyRegistrar(factory).sync_universe(strategy)          # idempotent
    assert len(factory.universe_local_repo.get_by_id(strategy.universe_id).financial_assets) == 2


def test_a_run_launched_from_strategies_uses_its_own_strategy(factory):
    from src.domain.entities.strategy.strategy import Strategy
    from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
    configured = factory.strategy_local_repo.add(Strategy("csm baseline", "cross_sectional"))
    experiment = factory.strategy_experiment_local_repo.add(StrategyExperiment(
        strategy_id=configured.id, strategy_hash=configured.content_hash, strategy_type="cross_sectional"))
    config = {**_config("cross_sectionnal_project"), "strategy_experiment_id": experiment.id}
    assert ProjectStrategyRegistrar(factory).ensure("cross_sectionnal_project", config).id == configured.id
    assert factory.strategy_local_repo.get_versions("cross_sectionnal_project") == []


def test_the_runner_hook_registers_and_never_fails_a_run(factory, caplog):
    from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.backtest_runner import (
        BacktestRunner,
    )
    runner = object.__new__(BacktestRunner)
    runner.logger, runner.registered_strategy = logging.getLogger("test"), None
    runner._registry_factory = lambda: factory
    strategy = runner._ensure_strategy(_config("stm_monthly_decile_project"))
    assert strategy is not None and strategy.name == "stm_monthly_decile_project"
    runner._sync_strategy_universe()

    def broken():
        raise RuntimeError("database down")
    runner._registry_factory = broken
    with caplog.at_level(logging.WARNING):
        assert runner._ensure_strategy({"project_name": "x"}) is None
    assert "database down" in caplog.text
    assert register_project_strategy(factory, "some_project", {"register_strategy": False}) is None
