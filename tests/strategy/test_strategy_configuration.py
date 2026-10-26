"""Strategy configuration system, phase 1: schema validation, versioned configurations, project adapters (in-memory
SQLite only; no IBKR, no SQL Server)."""

import copy
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.strategy.configuration_service import (
    ConfigurationInvalid,
    StrategyConfigurationService,
)
from src.application.services.strategy.project_adapters import ProjectRegistry
from src.domain.entities.strategy.configuration_schema import (
    ConfigurationSchema,
    FieldSpec,
    SectionSchema,
    coerce,
    validate_sections,
)
from src.domain.entities.strategy.project_capabilities import POSITION_SIGNAL, PROBABILITY_ABOVE_MEDIAN
from src.domain.entities.strategy.strategy_configuration import (
    ConfigurationLocked,
    StrategyConfiguration,
)

PROJECTS = ("cross_sectional", "stm_reference", "stm_paper")
REGISTRY = ProjectRegistry()


# ── schema ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_form_values_are_coerced_to_their_kind_and_bounds_are_enforced():
    assert coerce(FieldSpec("n", "int", minimum=1), "40") == (40, None)
    assert coerce(FieldSpec("n", "int", minimum=1), "0")[1] == "must be >= 1"
    assert coerce(FieldSpec("x", "float"), "0.25") == (0.25, None)
    assert coerce(FieldSpec("b", "bool"), "on") == (True, None)
    assert coerce(FieldSpec("c", "choice", choices=("auc", "long_short_sharpe")), "sharpe")[1].startswith("must be")
    assert coerce(FieldSpec("t", "str_list"), "JPM, BAC,JPM") == (["JPM", "BAC"], None)
    assert coerce(FieldSpec("p", "int_pair_list"), "2,6; 4,12") == ([[2, 6], [4, 12]], None)
    assert coerce(FieldSpec("d", "datetime"), "2026-06-01 16:00") == ("2026-06-01 16:00:00", None)
    assert coerce(FieldSpec("d", "date"), "June 1")[1].startswith("must be a date")


def test_unknown_sections_and_fields_are_rejected_not_ignored():
    schema = ConfigurationSchema("p", (SectionSchema("model", (FieldSpec("n", "int", 1),)),))
    normalised, issues = validate_sections(schema, {"model": {"n": 2, "dropout": 0.1}, "risk": {"var": 1},
                                                    "nonsense": {}})
    messages = {(i.section, i.field): i.message for i in issues}
    assert messages[("model", "dropout")].startswith("not supported")
    assert messages[("risk", None)].startswith("not supported")
    assert messages[("nonsense", None)] == "unknown section"
    assert normalised == {"model": {"n": 2}}


# ── configuration lifecycle ──────────────────────────────────────────────────────────────────────────────────────

def test_the_content_hash_ignores_key_order_name_version_and_status():
    a = StrategyConfiguration("a", "p", {"model": {"x": 1, "y": 2}, "training": {"w": 3}})
    b = StrategyConfiguration("b", "p", {"training": {"w": 3}, "model": {"y": 2, "x": 1}}, version=7, status="locked")
    assert a.content_hash == b.content_hash
    assert a.content_hash != StrategyConfiguration("a", "other", a.sections).content_hash


def test_a_locked_configuration_never_changes_and_revising_it_creates_a_new_version():
    c = StrategyConfiguration("c", "p", {"model": {"x": 1}}, id=10)
    with pytest.raises(ValueError):
        c.lock(datetime(2026, 1, 1))                               # only a validated configuration can be locked
    c.mark_validated({"model": {"x": 1}}, datetime(2026, 1, 1))
    c.lock(datetime(2026, 1, 2))
    with pytest.raises(ConfigurationLocked):
        c.update({"model": {"x": 2}})
    v2 = c.revise(new_version=2)
    assert (v2.version, v2.parent_id, v2.status, v2.sections) == (2, 10, "draft", {"model": {"x": 1}})
    v2.update({"model": {"x": 2}})
    assert c.section("model") == {"x": 1}                          # the locked version is untouched
    sections = c.sections
    sections["model"]["x"] = 99                                    # a copy: no way around update()
    assert c.section("model") == {"x": 1}


def test_editing_a_validated_configuration_sends_it_back_to_draft():
    c = StrategyConfiguration("c", "p", {"model": {"x": 1}})
    c.mark_validated({"model": {"x": 1}}, datetime(2026, 1, 1))
    c.update({"model": {"x": 2}})
    assert c.status == "draft" and c.validated_at is None


# ── project adapters ─────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("key", PROJECTS)
def test_the_default_configuration_reproduces_the_projects_own_config_exactly(key):
    """Regression: a configured run with the defaults is today's run (no hidden change of behaviour)."""
    adapter = REGISTRY.get(key)
    normalised, issues = adapter.validate(adapter.default_sections())
    assert [str(i) for i in issues if i.severity == "error"] == []
    assert adapter.native_config(normalised) == adapter.module().get_config()


def test_each_project_declares_what_it_supports_and_what_it_does_not():
    caps = {c.key: c for c in REGISTRY.capabilities()}
    assert set(caps) == set(PROJECTS)
    assert caps["cross_sectional"].output_contract == PROBABILITY_ABOVE_MEDIAN
    assert caps["stm_paper"].output_contract == POSITION_SIGNAL
    assert caps["cross_sectional"].supports_rule("quantile_long_short_inverse_vol")
    assert not caps["cross_sectional"].supports_rule("vol_scaled_signal")       # a probability is not a position
    assert caps["stm_reference"].supports_rule("vol_scaled_signal")
    for c in caps.values():
        assert c.long_short and not c.long_only and c.unsupported
    with pytest.raises(KeyError):
        REGISTRY.get("cross_sectionnal_project")


def test_cross_sectional_settings_reach_the_projects_own_configuration():
    from src.application.managers.project_managers.cross_sectionnal_project import config as project
    adapter = REGISTRY.get("cross_sectional")
    s = adapter.default_sections()
    s["universe"].update(name="csm_test_universe", tickers=["JPM", "BAC", "C", "WFC", "USB", "PNC"])
    s["factors"]["exclude"] = ["return_ytd"]
    s["model"].update(n_trials=12, metric="long_short_sharpe")
    s["training"].update(retrain_every_days=7)
    s["portfolio"].update(long_short_quantile=0.3, gross_exposure=0.8)
    normalised, issues = adapter.validate(s)
    assert [i for i in issues if i.severity == "error"] == []
    native = adapter.native_config(normalised, results_dir="/tmp/exp1", portfolio_name="CSM_exp1")
    csm = project.build_csm_configuration(native)
    assert csm.universe.tickers == ["JPM", "BAC", "C", "WFC", "USB", "PNC"]
    assert csm.universe.name == "csm_test_universe"
    assert csm.features.exclude == ("return_ytd",) and "return_ytd" not in csm.features.feature_names()
    assert (csm.optimization.n_trials, csm.optimization.metric) == (12, "long_short_sharpe")
    assert (csm.training.long_short_quantile, csm.training.gross_exposure) == (0.3, 0.8)
    assert native["retrain_every_days"] == 7
    assert (native["results_dir"], native["Portfolio"]["name"]) == ("/tmp/exp1", "CSM_exp1")
    assert list(native["universe"].values())[0] == csm.universe.tickers
    assert project.get_config()["csm"]["optimization"]["n_trials"] == 40          # the project's defaults untouched


def test_a_cross_sectional_configuration_without_enough_history_is_refused():
    adapter = REGISTRY.get("cross_sectional")
    s = adapter.default_sections()
    s["evaluation"]["price_history_start"] = "2026-01-02"
    _, issues = adapter.validate(s)
    assert any(i.field == "price_history_start" and "needs" in i.message for i in issues)


def test_a_different_constituent_list_cannot_reuse_the_default_universe_name():
    adapter = REGISTRY.get("cross_sectional")
    s = adapter.default_sections()
    s["universe"]["tickers"] = s["universe"]["tickers"][:-1]
    _, issues = adapter.validate(s)
    assert any(i.field == "name" and i.severity == "error" for i in issues)


def test_stm_settings_reach_the_projects_own_configuration():
    from src.application.managers.project_managers.spatio_temporal_momentum_project import config as project
    adapter = REGISTRY.get("stm_reference")
    s = adapter.default_sections()
    s["universe"].update(name="stm_sample_3", n_per_sector=3, seed=7)
    s["factors"].update(return_horizons=[1, 5, 21], macd_combinations=[[2, 6], [8, 24]])
    s["model"].update(lookback=30, encoder_length=20, hidden_dim=16)
    s["training"].update(training_window=90, n_epochs=5)
    s["portfolio"].update(target_vol=0.10, gross_exposure_cap=0.5)
    s["evaluation"]["price_history_start"] = "2025-06-02"
    normalised, issues = adapter.validate(s)
    assert [str(i) for i in issues if i.severity == "error"] == []
    native = adapter.native_config(normalised)
    stm = project.build_stm_configuration(native)
    assert stm.universe.name == "stm_sample_3" and len(stm.universe.tickers) > len(project.STM_TICKERS)
    assert list(native["universe"].values())[0] == stm.universe.tickers
    assert stm.features.return_horizons == (1, 5, 21) and stm.features.macd_combinations == ((2, 6), (8, 24))
    assert (stm.model.lookback, stm.model.encoder_length, stm.model.params["hidden_dim"]) == (30, 20, 16)
    assert stm.training.rolling_window_rows == 90 and stm.training.n_epochs == 5
    assert stm.features.vol_target == stm.training.target_vol == 0.10
    assert native["gross_exposure_cap"] == 0.5


def test_stm_inconsistent_model_settings_are_refused():
    adapter = REGISTRY.get("stm_paper")
    s = adapter.default_sections()
    s["model"].update(lookback=10, encoder_length=10)
    s["factors"]["macd_combinations"] = [[6, 2]]
    _, issues = adapter.validate(s)
    fields = {i.field for i in issues if i.severity == "error"}
    assert {"encoder_length", "macd_combinations"} <= fields
    s = adapter.default_sections()
    s["model"]["model_type"] = "lstm"                              # forward-tested only: not offered
    _, issues = adapter.validate(s)
    assert any(i.field == "model_type" for i in issues)


# ── the run's config reaches the algorithm ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("folder", ["cross_sectionnal_project", "spatio_temporal_momentum_project",
                                    "spatio_temporal_momentum_project_full"])
def test_the_runner_hands_its_config_to_the_algorithm(folder):
    import importlib
    runner_mod = importlib.import_module(f"src.application.managers.project_managers.{folder}.backtesting.backtest_runner")
    algo_mod = importlib.import_module(
        f"src.application.managers.project_managers.{folder}.backtesting.base_project_algorithm")
    config = copy.deepcopy(importlib.import_module(
        f"src.application.managers.project_managers.{folder}.config").DEFAULT_CONFIG)
    config["Portfolio"]["name"] = "Experiment_42_Portfolio"
    runner = runner_mod.BacktestRunner.__new__(runner_mod.BacktestRunner)
    runner.project_config = config
    runner.model_trainer = MagicMock()
    algorithm = runner.create_algorithm_instance()
    assert algorithm.project_config is config
    with patch.object(algo_mod.BaseProjectAlgorithm, "initialize", lambda self: None):
        algorithm._entity_service = None
        algorithm.trainer = None
        algorithm.initialize()
    assert algorithm.config["Portfolio"]["name"] == "Experiment_42_Portfolio"
    fresh = algo_mod.Algorithm()
    with patch.object(algo_mod.BaseProjectAlgorithm, "initialize", lambda self: None):
        fresh._entity_service = None
        fresh.trainer = None
        fresh.initialize()
    assert fresh.config["Portfolio"]["name"] != "Experiment_42_Portfolio"     # no config given: project defaults


# ── persistence and the service (in-memory SQLite) ────────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.local_repo.strategy.strategy_repositories import (
        StrategyConfigurationRepository,
    )
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    ticks = iter(datetime(2026, 10, 26, 9, m) for m in range(60))
    yield StrategyConfigurationService(StrategyConfigurationRepository(session), REGISTRY, clock=lambda: next(ticks))
    session.close()
    engine.dispose()


def test_a_configuration_is_created_validated_locked_revised_and_cloned(service):
    c = service.create("csm baseline", "cross_sectional", {"model": {"n_trials": 20}})
    assert (c.id, c.version, c.status, c.section("model")["n_trials"]) == (1, 1, "draft", 20)
    with pytest.raises(ValueError):
        service.create("csm baseline", "cross_sectional")                       # names are unique
    c, issues = service.validate(c.id)
    assert c.status == "validated" and not [i for i in issues if i.severity == "error"]
    locked = service.lock(c.id)
    assert locked.status == "locked" and locked.locked_at is not None
    with pytest.raises(ConfigurationLocked):
        service.update(c.id, {"model": {"n_trials": 30}})
    v2 = service.revise(c.id)
    assert (v2.name, v2.version, v2.parent_id, v2.status) == ("csm baseline", 2, c.id, "draft")
    v2 = service.update(v2.id, {"model": {"n_trials": 30}})
    assert service.get(c.id).section("model")["n_trials"] == 20                 # v1 still what it ran with
    preview = service.preview(v2.id)
    assert preview["changes"] == [{"section": "model", "field": "n_trials", "before": 20, "after": 30}]
    clone = service.clone(c.id, "csm baseline (copy)")
    assert (clone.version, clone.parent_id, clone.content_hash) == (1, c.id, locked.content_hash)
    assert [x.version for x in service.versions("csm baseline")] == [1, 2]


def test_an_invalid_configuration_cannot_be_locked(service):
    c = service.create("too short", "cross_sectional", {"evaluation": {"price_history_start": "2026-05-01"}})
    with pytest.raises(ConfigurationInvalid) as e:
        service.lock(c.id)
    assert any(i.field == "price_history_start" for i in e.value.issues)
    assert service.get(c.id).status == "draft"


def test_the_stored_configuration_round_trips_through_the_database(service):
    c = service.create("stm", "stm_paper", {"factors": {"macd_combinations": [[2, 6], [4, 12]]}})
    again = service.get(c.id)
    assert again.sections == c.sections and again.content_hash == c.content_hash
    native = service.native_config(again)
    assert native["stm"]["features"]["macd_combinations"] == ((2, 6), (4, 12))
