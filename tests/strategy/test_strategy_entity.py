"""
Strategy domain entity (replaces StrategyConfiguration, 2026-11-19): creation, validation of required fields, typed
definition, universe reference, update / lifecycle, persistence and retrieval, Strategy -> Universe -> members
(in-memory / file SQLite only; no IBKR, no SQL Server).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.application.services.strategy.project_adapters import ProjectRegistry, bar_frequency, strategy_definition
from src.application.services.strategy.strategy_service import StrategyService
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.strategy.strategy import Strategy, StrategyLocked, content_hash
from src.domain.entities.strategy.strategy_configuration import StrategyConfiguration
from src.domain.entities.universe.universe import Universe

REGISTRY = ProjectRegistry()


# ── domain ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_a_strategy_is_created_with_its_definition():
    s = Strategy("stm banks", "stm_paper", {"model": {"lookback": 24}}, universe_id=17, bar_frequency="10m",
                 bar_size="10 mins", model_type="tft", training_window=390, retrain_every_days=1,
                 prediction_horizon=1, description="intraday STM")
    assert (s.name, s.strategy_type, s.project_key, s.version, s.status) == ("stm banks", "stm_paper", "stm_paper",
                                                                            1, "draft")
    assert s.definition == {"universe_id": 17, "bar_frequency": "10m", "bar_size": "10 mins", "model_type": "tft",
                            "training_window": 390, "retrain_every_days": 1, "prediction_horizon": 1}
    assert s.parameters == {"model": {"lookback": 24}} and s.features == {} and s.risk == {}
    assert StrategyConfiguration is Strategy                                   # former name still imports


@pytest.mark.parametrize("kwargs", [
    dict(name="", strategy_type="p"),
    dict(name="s", strategy_type=""),
    dict(name="s", strategy_type="p", status="running"),
    dict(name="s", strategy_type="p", version=0),
    dict(name="s", strategy_type="p", sections={"nonsense": {}}),
    dict(name="s", strategy_type="p", training_window=-1),
    dict(name="s", strategy_type="p", prediction_horizon=1.5),
])
def test_required_fields_and_types_are_enforced(kwargs):
    with pytest.raises(ValueError):
        Strategy(**kwargs)


def test_the_universe_is_referenced_by_id_never_held_as_a_ticker_list():
    s = Strategy("s", "p")
    s.assign_universe(17)
    assert s.universe_id == 17 and not hasattr(s, "universe")


def test_the_hash_covers_the_definition_and_matches_the_former_configuration_hash():
    s = Strategy("s", "p", {"model": {"x": 1}})
    assert s.content_hash == content_hash("p", {"model": {"x": 1}})              # no typed fields: unchanged hash
    before = s.content_hash
    s.update(universe_id=3)
    assert s.content_hash != before
    other = Strategy("other name", "p", {"model": {"x": 1}}, universe_id=3, version=4, status="locked")
    assert other.content_hash == s.content_hash                                # name / version / status excluded


def test_updates_follow_the_lifecycle():
    s = Strategy("s", "p", {"model": {"x": 1}})
    s.mark_validated({"model": {"x": 1, "y": 2}}, datetime(2026, 11, 19), definition={"model_type": "tft",
                                                                                   "bar_size": None})
    assert (s.status, s.model_type, s.section("model")) == ("validated", "tft", {"x": 1, "y": 2})
    s.update(training_window=120)                                              # editing sends it back to draft
    assert (s.status, s.training_window, s.validated_at) == ("draft", 120, None)
    with pytest.raises(ValueError):
        s.update(unknown_field=1)
    s.mark_validated(s.sections, datetime(2026, 11, 19))
    s.lock(datetime(2026, 11, 19, 1))
    with pytest.raises(StrategyLocked):
        s.update(training_window=60)
    with pytest.raises(StrategyLocked):
        s.assign_universe(9)
    v2 = s.revise(new_version=2)
    assert (v2.version, v2.status, v2.parent_id, v2.training_window, v2.model_type) == (2, "draft", s.id, 120, "tft")


def test_the_typed_definition_is_read_from_a_projects_native_config():
    native = {"bar_size_setting": "10 mins", "model_type": "tft", "training_window": 390, "retrain_every_days": 2,
              "live": {"account": "DUR314497", "host": "127.0.0.1", "port": 7497, "client_id": 31},
              "stm": {"bar_minutes": 10, "prediction_horizon": 1, "model": {"model_type": "tft"}}}
    assert strategy_definition(native) == {"bar_size": "10 mins", "bar_frequency": "10m", "model_type": "tft",
                                           "training_window": 390, "retrain_every_days": 2, "prediction_horizon": 1}
    assert (bar_frequency("1 day"), bar_frequency("1 month"), bar_frequency("weird")) == ("1d", "1mo", None)


# ── service + persistence ────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def env(tmp_path):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    engine = create_engine(f"sqlite:///{tmp_path / 'strategy.db'}")
    ModelBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    factory = RepositoryFactory(session)
    ticks = iter(datetime(2026, 11, 19, 9, m) for m in range(60))
    service = StrategyService(factory.strategy_local_repo, REGISTRY, clock=lambda: next(ticks))
    yield type("E", (), dict(session=session, factory=factory, service=service))
    session.close()
    engine.dispose()


def test_a_strategy_is_persisted_retrieved_and_updated(env):
    s = env.service.create("csm baseline", "cross_sectional", {"model": {"n_trials": 20}})
    assert s.id is not None and s.model_type is not None                       # definition filled from the project
    again = env.factory.strategy_local_repo.get_by_id(s.id)
    assert again.to_dict() == s.to_dict()
    validated, issues = env.service.validate(s.id)
    assert validated.status == "validated" and not [i for i in issues if i.severity == "error"]
    stored = env.session.execute(text(
        "SELECT s.strategy_type, v.value, s.content_hash FROM strategies s "
        "JOIN strategy_parameter_values v ON v.strategy_id = s.id "
        "JOIN strategy_parameters p ON p.id = v.parameter_id "
        "WHERE s.id = :i AND p.section = 'definition' AND p.name = 'model_type'"), {"i": s.id}).one()
    assert stored == ("cross_sectional", validated.model_type, validated.content_hash)
    with pytest.raises(ValueError):
        env.service.create("", "cross_sectional")
    with pytest.raises(ValueError):
        env.service.create("csm baseline", "cross_sectional")                  # names are unique


def test_strategy_universe_and_members_resolve_through_the_repositories(env):
    shares = [env.factory.company_share_local_repo.add(CompanyShare(id=None, symbol=t, exchange_id=1, company_id=1,
                                                                    currency_id=1, start_date=date(2020, 1, 1)))
              for t in ("JPM", "BAC")]
    universe = Universe("stm banks")
    for share in shares:
        universe.add_financial_asset(share.id)
    universe = env.factory.universe_local_repo.add(universe)

    s = env.service.create("stm banks", "stm_paper", universe_id=universe.id)
    s = env.service.assign_universe(s.id, universe.id)
    strategy = env.factory.strategy_local_repo.get_by_id(s.id)
    assert strategy.universe_id == universe.id
    assert [x.id for x in env.factory.strategy_local_repo.get_by_universe(universe.id)] == [s.id]
    members = env.factory.universe_local_repo.get_by_id(strategy.universe_id).financial_asset_ids()
    assert [env.factory.company_share_local_repo.get_by_id(i).symbol for i in members] == ["JPM", "BAC"]

    env.service.validate(s.id)
    env.service.lock(s.id)
    with pytest.raises(StrategyLocked):
        env.service.assign_universe(s.id, None)


def test_experiments_point_at_the_strategy(env):
    from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
    s = env.service.create("exp", "cross_sectional")
    e = env.factory.strategy_experiment_local_repo.add(StrategyExperiment(
        strategy_id=s.id, strategy_hash=s.content_hash, strategy_type=s.strategy_type))
    again = env.factory.strategy_experiment_local_repo.get_by_strategy(s.id)
    assert [(x.id, x.strategy_id, x.configuration_id, x.project_key) for x in again] == [
        (e.id, s.id, s.id, "cross_sectional")]
