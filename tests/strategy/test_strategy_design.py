"""
/strategies design: see every strategy, create a new one from another, change its trading / training frequency,
model, financial-asset universe, factor universe and parameters (file SQLite; no IBKR, no SQL Server).
"""

import re
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.strategy.project_strategy_registration import ProjectStrategyRegistrar
from src.application.services.strategy.strategy_design_service import parse_instruments
from src.application.services.strategy.strategy_services import StrategyServices
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.strategy.strategy import StrategyLocked
from src.infrastructure.models.factor.factor import CompanyShareFactorModel


@pytest.fixture
def env(tmp_path, monkeypatch):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from src.interfaces.flask.app import FlaskApp
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))
    engine = create_engine(f"sqlite:///{tmp_path / 'design.db'}")
    ModelBase.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    seed = sessions()
    factory = RepositoryFactory(seed)
    shares = {t: factory.company_share_local_repo.add(CompanyShare(id=None, symbol=t, exchange_id=1, company_id=1,
                                                                   currency_id=1, start_date=date(2020, 1, 1))).id
              for t in ("JPM", "BAC", "GS", "MS")}
    factors = {}
    for name in ("close", "volume", "roe"):
        row = CompanyShareFactorModel(name=name, group="price" if name != "roe" else "fundamental",
                                      subgroup="TRADES", frequency="1d", data_type="numeric", source="ibkr",
                                      definition=name, factor_type="company_share_factor")
        seed.add(row)
        seed.commit()
        factors[name] = row.id
    project = "stm_monthly_decile_project"
    from src.application.managers.project_managers.stm_monthly_decile_project.config import get_config
    registered = ProjectStrategyRegistrar(factory).ensure(
        project, {**get_config(), "universe": {CompanyShare: ["JPM", "BAC", "GS"]}})
    seed.close()

    def services():
        return StrategyServices(sessions(), session_factory=sessions, results_root=tmp_path / "results",
                                is_alive=lambda pid: False, host="design-test")

    app = FlaskApp().get_app()
    app.config.update(STRATEGY_SERVICES_FACTORY=services, TESTING=True)
    yield SimpleNamespace(client=app.test_client(), services=services, shares=shares, factors=factors,
                          registered=registered)
    engine.dispose()


def _post(env, url, **data):
    return env.client.post(url, data=data)


# ── service ──────────────────────────────────────────────────────────────────────────────────────────────────────

def test_instruments_text_is_parsed_by_asset_type():
    assert parse_instruments("CompanyShare: JPM, BAC\nETFShare: DIA\nGS\n\nCompanyShare: JPM") == {
        "CompanyShare": ["JPM", "BAC", "GS"], "ETFShare": ["DIA"]}     # order kept (model asset order)
    assert parse_instruments("AAPL  281215C00260000") == {"CompanyShare": ["AAPL  281215C00260000"]}


def test_a_new_strategy_is_derived_from_another_with_its_own_universe(env):
    d = env.services().design
    source = d.get(env.registered.id)
    child = d.derive(source.id, name="deciles banks")
    assert (child.name, child.version, child.parent_id, child.status) == ("deciles banks", 1, source.id, "draft")
    assert child.universe_id != source.universe_id
    assert sorted(d.universe_of(child).financial_asset_ids()) == sorted(d.universe_of(source).financial_asset_ids())
    assert child.model_type == source.model_type and child.sections == source.sections
    next_version = d.derive(source.id)
    assert (next_version.name, next_version.version) == (source.name, source.version + 1)
    with pytest.raises(ValueError):
        d.derive(source.id, name="deciles banks")                              # names are unique


def test_trading_training_universe_and_factors_change_on_the_draft_only(env):
    d = env.services().design
    source_assets = sorted(d.universe_of(d.get(env.registered.id)).financial_asset_ids())
    child = d.derive(env.registered.id, name="weekly variant")
    child = d.update_definition(child.id, {"bar_frequency": "1w", "bar_size": "1 week", "training_window": "60",
                                           "retrain_every_days": "7", "prediction_horizon": "", "model_type": "mlp"})
    assert (child.bar_frequency, child.bar_size, child.training_window, child.retrain_every_days,
            child.prediction_horizon, child.model_type) == ("1w", "1 week", 60, 7, None, "mlp")
    child, unknown = d.set_financial_assets(child.id, "CompanyShare: JPM, MS, ZZZZ")
    assert unknown == {"CompanyShare": ["ZZZZ"]}
    assert sorted(d.universe_of(child).financial_asset_ids()) == sorted([env.shares["JPM"], env.shares["MS"]])
    assert child.section("universe")["instruments"] == {"CompanyShare": ["JPM", "MS", "ZZZZ"]}
    child = d.set_factors(child.id, [env.factors["close"], env.factors["roe"], env.factors["close"]])
    assert d.universe_of(child).factor_ids() == [env.factors["close"], env.factors["roe"]]
    child = d.set_section(child.id, "risk", '{"split_guard": {"tolerance": 0.05}}')
    assert child.risk == {"split_guard": {"tolerance": 0.05}}
    with pytest.raises(ValueError):
        d.set_section(child.id, "risk", "[1, 2]")
    with pytest.raises(ValueError):
        d.update_definition(child.id, {"training_window": "sixty"})
    # the source (locked, used by runs) never moved
    source = d.get(env.registered.id)
    assert source.status == "locked" and sorted(d.universe_of(source).financial_asset_ids()) == source_assets
    with pytest.raises(StrategyLocked):
        d.update_definition(source.id, {"training_window": "1"})
    validated, issues = d.validate(child.id)
    assert validated.status == "validated" and issues == []


def test_a_shared_universe_is_copied_before_it_changes(env):
    d = env.services().design
    a = d.derive(env.registered.id, name="a")
    b = d.derive(a.id, name="b")
    b.assign_universe(a.universe_id)                                          # both point at one universe
    d.strategies.update(b)
    before = d.universe_of(a).financial_asset_ids()
    b, _ = d.set_financial_assets(b.id, "GS")
    assert b.universe_id != a.universe_id
    assert d.universe_of(a).financial_asset_ids() == before
    assert d.universe_of(b).financial_asset_ids() == [env.shares["GS"]]


# ── pages ────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_dashboard_lists_every_strategy_with_its_definition(env):
    page = env.client.get("/strategies/").get_data(as_text=True)
    assert "stm_monthly_decile_project" in page and "Create from" in page and "Training window" in page
    view = env.client.get(f"/strategies/{env.registered.id}").get_data(as_text=True)
    assert "Create a new strategy from this one" in view and "Financial assets" in view
    assert "Launch backtest" in view and "Tick the confirmation" not in view   # launchable project


def test_create_from_another_strategy_and_design_it_through_the_pages(env):
    r = _post(env, f"/strategies/{env.registered.id}/derive", name="banks deciles 10m", description="intraday")
    assert r.status_code == 302
    cid = int(re.search(r"/strategies/(\d+)/design", r.headers["Location"]).group(1))
    page = env.client.get(f"/strategies/{cid}/design").get_data(as_text=True)
    assert "Trading, model and training" in page and "Factor universe" in page and "JPM" in page
    assert _post(env, f"/strategies/{cid}/design", part="definition", bar_frequency="10m", bar_size="10 mins",
                 model_type="tft", training_window="390", retrain_every_days="1", prediction_horizon="1",
                 description="intraday").status_code == 302
    assert _post(env, f"/strategies/{cid}/design", part="assets", instruments="CompanyShare: BAC, MS").status_code == 302
    env.client.post(f"/strategies/{cid}/design", data={"part": "factors",
                                                       "factor_id": [str(env.factors["volume"])]})
    _post(env, f"/strategies/{cid}/design", part="section", section="portfolio", json='{"long_short_gross": 1.0}')
    r = _post(env, f"/strategies/{cid}/design", part="validate")
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/strategies/{cid}")

    d = env.services().design
    c = d.get(cid)
    assert (c.bar_frequency, c.training_window, c.status, c.portfolio_construction) == (
        "10m", 390, "validated", {"long_short_gross": 1.0})
    assert sorted(d.universe_of(c).financial_asset_ids()) == sorted([env.shares["BAC"], env.shares["MS"]])
    assert d.universe_of(c).factor_ids() == [env.factors["volume"]]
    view = env.client.get(f"/strategies/{cid}").get_data(as_text=True)
    assert "10m" in view and "volume" in view


def test_a_locked_strategy_is_not_designed_in_place(env):
    r = env.client.get(f"/strategies/{env.registered.id}/design")
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/strategies/{env.registered.id}")
    r = _post(env, f"/strategies/{env.registered.id}/design", part="definition", training_window="5")
    assert r.status_code == 302
    assert env.services().design.get(env.registered.id).training_window != 5
