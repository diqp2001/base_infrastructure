"""
A designed strategy runs: it is applied onto its project's own config (model, trading / training frequency,
universe, parameters) and launched through the experiment worker; the model can be switched among the networks the
project trains (file SQLite, fake manager; no IBKR, no SQL Server, no engine run).
"""

import importlib
import pathlib
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.backtest_registry.run_identity import _jsonable
from src.application.services.strategy.experiment_worker import run_experiment
from src.application.services.strategy.model_catalog import apply_model, model_choices, stm_model_parameters
from src.application.services.strategy.project_adapters import ProjectFolderAdapter, ProjectRegistry
from src.application.services.strategy.project_strategy_registration import ProjectStrategyRegistrar
from src.application.services.strategy.strategy_project_config import apply_strategy
from src.application.services.strategy.strategy_services import StrategyServices
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

ROOT = pathlib.Path(__file__).resolve().parents[2] / "src" / "application" / "managers" / "project_managers"
PACKAGE = "src.application.managers.project_managers"
CONFIGURED = sorted(p.name for p in ROOT.iterdir() if (p / "config.py").exists()
                    and "def get_config" in (p / "config.py").read_text(encoding="utf-8"))
STM_10M = "spatio_temporal_momentum_project_10m"


def _config(project):
    import copy
    return copy.deepcopy(importlib.import_module(f"{PACKAGE}.{project}.config").get_config())


def test_choosing_a_model_never_changes_the_projects_own_config():
    module = importlib.import_module(f"{PACKAGE}.{STM_10M}.config")
    before = _jsonable(module.DEFAULT_CONFIG["stm"]["model"])
    apply_model(module.get_config(), "slp")                    # a shallow copy, as projects hand it out
    assert _jsonable(module.DEFAULT_CONFIG["stm"]["model"]) == before


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 19, 9, 0)

    def __call__(self):
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def env(tmp_path, monkeypatch):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))
    engine = create_engine(f"sqlite:///{tmp_path / 'run.db'}")
    ModelBase.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    factory = RepositoryFactory(sessions())
    for t in ("JPM", "BAC", "GS"):
        factory.company_share_local_repo.add(CompanyShare(id=None, symbol=t, exchange_id=1, company_id=1,
                                                          currency_id=1, start_date=date(2020, 1, 1)))
    clock = Clock()
    runner = SimpleNamespace(started=[], start=lambda e: runner.started.append(e.id) or 4242)
    services = StrategyServices(sessions(), runner=runner, session_factory=sessions, results_root=tmp_path / "results",
                                clock=clock, is_alive=lambda pid: False, host="test-host")
    services.configurations.clock = clock
    yield SimpleNamespace(services=services, factory=factory, clock=clock, runner=runner)
    engine.dispose()


# ── models ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_each_project_offers_the_models_its_pipeline_trains():
    assert model_choices(_config(STM_10M)) == ["tft", "conv", "lstm", "mlp", "slp"]
    assert model_choices(_config("stm_monthly_decile_project"))[0] == "tft"
    assert model_choices(_config("cross_sectionnal_project")) == ["lightgbm"]
    assert model_choices(_config("market_making_SPX_call_spread_project_v2")) == ["pricing"]


def test_switching_model_keeps_only_the_parameters_the_new_network_takes():
    config = _config(STM_10M)
    assert {"emb_dim", "n_heads"} <= set(config["stm"]["model"]["params"])
    apply_model(config, "lstm")
    assert config["model_type"] == config["stm"]["model"]["model_type"] == "lstm"
    assert set(config["stm"]["model"]["params"]) <= set(stm_model_parameters("lstm")) == {"n_units", "dropout"}
    assert config["stm"]["model"]["params"] == {"dropout": 0.1}
    apply_model(config, "slp")
    assert config["stm"]["model"]["params"] == {}
    with pytest.raises(ValueError):
        apply_model(config, "lightgbm")


def test_every_stm_network_is_built_from_the_applied_config():
    import torch

    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
        STMModelConfig,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import build_model
    for model in model_choices(_config(STM_10M)):
        config = apply_model(_config(STM_10M), model)
        m = config["stm"]["model"]
        cfg = STMModelConfig(model_type=m["model_type"], lookback=m["lookback"], encoder_length=m["encoder_length"],
                             params=m["params"])
        net = build_model(n_assets=3, n_features=4, model_cfg=cfg)
        assert net(torch.zeros(2, 3, m["lookback"], 4)).shape == (2, 3), model


@pytest.mark.parametrize("model", ["tft", "conv", "lstm", "mlp", "slp"])
def test_every_stm_network_trains_through_the_walk_forward(model, tmp_path):
    """Not only a forward pass: the Sharpe-loss walk-forward trains each network and stores usable artifacts."""
    import numpy as np

    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
        build_feature_panel,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
        SpatioTemporalMomentumModelProvider,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
        STMWalkForwardTrainer,
    )
    from tests.spatio_temporal_momentum.helpers import ASSETS, make_factory, synthetic_closes, tiny_config
    SpatioTemporalMomentumModelProvider.clear_cache()
    cfg = tiny_config(model_type=model, tmp_dir=str(tmp_path))
    factory, session, engine = make_factory()
    try:
        closes = synthetic_closes(1000)
        panel = build_feature_panel(closes, cfg.features)
        results = STMWalkForwardTrainer(cfg, factory=factory).run(panel, {a: 100 + i for i, a in enumerate(ASSETS)})
        assert results, f"{model}: no window trained"
        r = results[0]
        assert r.epochs_run > 0 and np.isfinite(r.test_preds).all() and np.isfinite(r.best_val_sharpe)
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
            load_model_file,
        )
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_training import (
            predict_last_step,
        )
        artifact = factory.model_artifact_local_repo.get_by_id(r.artifact_id)
        reloaded = predict_last_step(load_model_file(artifact.location).model, r.test, 32)
        np.testing.assert_allclose(reloaded, r.test_preds, rtol=1e-5, atol=1e-6)
    finally:
        SpatioTemporalMomentumModelProvider.clear_cache()
        session.close()
        engine.dispose()


def test_the_web_form_of_stm_strategies_offers_every_network(env):
    s = env.services
    c = s.configurations.create("stm lstm", "stm_paper", {"model": {"model_type": "lstm"}})
    c, issues = s.configurations.validate(c.id)
    assert c.status == "validated", issues
    native = s.configurations.native_config(c)
    assert native["stm"]["model"]["model_type"] == "lstm" and set(native["stm"]["model"]["params"]) <= {"n_units",
                                                                                                       "dropout"}


# ── a strategy back into its project's config ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("project", CONFIGURED)
def test_applying_a_registered_strategy_gives_its_projects_config_back(project, env):
    base = _config(project)
    strategy = ProjectStrategyRegistrar(env.factory).ensure(project, base)
    back = apply_strategy(base, strategy)
    names = lambda c: {str(getattr(k, "__name__", k)): _jsonable(v) for k, v in c.items()}   # noqa: E731
    assert names(back) == names(base)


def test_a_designed_strategy_changes_what_the_project_runs(env):
    d = env.services.design
    source = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    child = d.derive(source.id, name="banks lstm hourly")
    d.update_definition(child.id, {"model_type": "lstm", "training_window": "200", "retrain_every_days": "3",
                                   "decision_minutes": "60", "bar_frequency": "10m"})
    d.set_financial_assets(child.id, "CompanyShare: JPM, BAC, GS")
    child, issues = d.validate(child.id)
    assert child.status == "validated" and not [i for i in issues if i.severity == "error"]
    native = env.services.configurations.native_config(child)
    assert native["model_type"] == native["stm"]["model"]["model_type"] == "lstm"
    assert native["training_window"] == 200 and native["stm"]["training"]["rolling_window_rows"] == 200
    assert native["retrain_every_days"] == 3 and native["config_interval"]["custom_interval_minutes"] == 60
    assert native["stm"]["bar_minutes"] == 10
    assert native["universe"] == {CompanyShare: ["JPM", "BAC", "GS"]}
    assert native["stm"]["universe"]["tickers"] == ["JPM", "BAC", "GS"]
    assert native["stm"]["universe"]["name"].endswith(f"__strategy{child.id}")      # its own universe name
    base = _config(STM_10M)
    assert native["live"] if "live" in base else "live" not in native               # run keys: the project's own
    assert native["backtest_start"] == base["backtest_start"]


def test_an_unavailable_model_is_refused_at_validation(env):
    d = env.services.design
    source = ProjectStrategyRegistrar(env.factory).ensure("cross_sectionnal_project", _config("cross_sectionnal_project"))
    child = d.derive(source.id, name="csm with a tft")
    d.update_definition(child.id, {"model_type": "tft"})
    child, issues = d.validate(child.id)
    assert child.status == "draft" and any(i.field == "model_type" for i in issues)


# ── launching ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_which_projects_can_be_launched_from_the_web():
    registry = ProjectRegistry()
    assert registry.get(STM_10M).launchable and registry.get("stm_monthly_decile_project").launchable
    assert registry.get("cross_sectionnal_project").launchable
    assert not registry.get("spatio_temporal_momentum_project_10m_live").launchable      # live trading
    assert not registry.get("etf_dispersion_screener_project").launchable
    assert not registry.get("market_making_SPX_call_spread_project").launchable          # no config argument
    assert STM_10M not in registry.keys() and isinstance(registry.get(STM_10M), ProjectFolderAdapter)
    with pytest.raises(KeyError):
        registry.get("no_such_project")


def test_a_designed_strategy_is_launched_and_its_project_runs_it(env):
    s, d = env.services, env.services.design
    source = ProjectStrategyRegistrar(env.factory).ensure(STM_10M, _config(STM_10M))
    child = d.derive(source.id, name="banks mlp")
    d.update_definition(child.id, {"model_type": "mlp", "retrain_every_days": "2"})
    d.set_financial_assets(child.id, "JPM, BAC")
    d.validate(child.id)
    e = s.experiments.launch(child.id)
    assert e.status == "queued" and env.runner.started == [e.id]
    assert s.configurations.get(child.id).status == "locked"
    seen = {}

    def manager_factory(adapter, native, database_service):
        seen["native"], seen["adapter"] = native, adapter
        return SimpleNamespace(run=lambda: {"success": True, "run_id": 12, "run_status": "COMPLETED",
                                            "performance_metrics": {"sharpe_ratio": 0.8}}, runner=None)

    done = run_experiment(e.id, s.experiment_repository, s.strategy_repository, clock=env.clock, pid=1, host="h",
                          manager_factory=manager_factory)
    assert done.status == "succeeded", done.error
    native = seen["native"]
    assert native["model_type"] == "mlp" and native["retrain_every_days"] == 2
    assert native["universe"] == {CompanyShare: ["JPM", "BAC"]}
    assert native["strategy_experiment_id"] == e.id and native["results_dir"] == e.results_dir
    assert native["Portfolio"]["name"].endswith(f"_exp{e.id}")
    assert done.summary["run_id"] == 12 and done.summary["metrics"] == {"sharpe_ratio": 0.8}


def test_live_or_screening_projects_are_never_launched(env):
    live = ProjectStrategyRegistrar(env.factory).ensure("spatio_temporal_momentum_project_10m_live",
                                                        _config("spatio_temporal_momentum_project_10m_live"))
    with pytest.raises(ValueError, match="cannot be launched"):
        env.services.experiments.launch(live.id)
    assert env.runner.started == []
