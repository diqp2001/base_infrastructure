"""
Every strategy parameter is picked, never typed (parameter_choices): dropdowns for single values, checkbox lists for
lists, the current value always offered, anything not offered refused; and the designer / project form pages that use
them.
"""

import json
import re

import pytest
from werkzeug.datastructures import MultiDict

from src.application.services.strategy.parameter_choices import (
    apply_choices,
    field_tree,
    float_choices,
    int_choices,
)

SECTION = {
    "deciles": {"n_deciles": 10, "weighting": "equal_weight", "transaction_cost_bps": 5.0,
                "use_eulerpool_fundamentals": True, "fundamentals": ["fund_roe_ttm_1q"],
                "retrain_every_rebalances": 1},
    "Portfolio": {"class": "<class 'Portfolio'>", "currency_code": "USD"},
}


def _fields(tree):
    out = {}
    for f in tree:
        if f["kind"] == "group":
            out.update(_fields(f["children"]))
        else:
            out[tuple(json.loads(f["name"]))] = f
    return out


def test_choices_always_hold_the_current_value():
    assert 10 in int_choices(10) and 120 in int_choices(120) and 7 in int_choices(7) and 37 in int_choices(37)
    assert 5.0 in float_choices(5.0) and 0.15 in float_choices(0.15) and 0.0 in float_choices(0.0)
    assert all(0.1 <= v <= 250 for v in float_choices(5.0) if v)


def test_every_value_is_a_dropdown_or_a_checkbox_list():
    fields = _fields(field_tree("portfolio", SECTION, locked={"retrain_every_rebalances": "set above"}))
    assert fields[("portfolio", "deciles", "n_deciles")]["kind"] == "select"
    weighting = fields[("portfolio", "deciles", "weighting")]
    assert [json.loads(v) for v, _ in weighting["options"]][:2] == ["equal_weight", "market_cap_weight"]
    assert fields[("portfolio", "deciles", "use_eulerpool_fundamentals")]["selected"] == ["true"]
    fundamentals = fields[("portfolio", "deciles", "fundamentals")]
    assert fundamentals["kind"] == "multi" and len(fundamentals["options"]) > 20      # the fundamentals catalog
    assert fields[("portfolio", "deciles", "retrain_every_rebalances")]["kind"] == "fixed"
    assert fields[("portfolio", "Portfolio", "class")]["kind"] == "fixed"           # objects are never edited


def test_posted_choices_are_written_and_anything_else_refused():
    name = lambda *p: json.dumps(["portfolio", *p])                                   # noqa: E731
    form = MultiDict([(name("deciles", "n_deciles"), "5"), (name("deciles", "weighting"), '"market_cap_weight"'),
                      (name("deciles", "use_eulerpool_fundamentals"), "false"),
                      ("present:" + name("deciles", "fundamentals"), "1"),
                      (name("deciles", "fundamentals"), '"fund_roa_ttm_1q"'),
                      (name("deciles", "fundamentals"), '"fund_roe_ttm_1q"')])
    out = apply_choices("portfolio", SECTION, form)
    d = out["deciles"]
    assert (d["n_deciles"], d["weighting"], d["use_eulerpool_fundamentals"]) == (5, "market_cap_weight", False)
    assert set(d["fundamentals"]) == {"fund_roa_ttm_1q", "fund_roe_ttm_1q"}
    assert d["transaction_cost_bps"] == 5.0 and SECTION["deciles"]["n_deciles"] == 10   # untouched / not mutated
    with pytest.raises(ValueError, match="not one of its choices"):
        apply_choices("portfolio", SECTION, MultiDict([(name("deciles", "n_deciles"), "7.5")]))
    with pytest.raises(ValueError, match="not among its choices"):
        apply_choices("portfolio", SECTION, MultiDict([("present:" + name("deciles", "fundamentals"), "1"),
                                                       (name("deciles", "fundamentals"), '"made_up"')]))
    cleared = apply_choices("portfolio", SECTION, MultiDict([("present:" + name("deciles", "fundamentals"), "1")]))
    assert cleared["deciles"]["fundamentals"] == []


def test_the_designer_has_no_typed_parameter(web_decile):
    client, design, sid, services = web_decile
    page = client.get(design).get_data(as_text=True)
    typed = re.findall(r'<(?:input|textarea)[^>]*class="form-control[^"]*"[^>]*>', page)
    names = ('name="description"', 'id="factor-filter"', 'name="factor_universe_name"')   # names and search only
    assert all(any(n in t for n in names) for t in typed), typed
    assert 'name="instruments"' not in page and 'name="asset"' in page
    # tick two assets; pick a weighting from the dropdown
    r = client.post(design, data=MultiDict([("part", "assets"), ("asset", "CompanyShare:AAPL"),
                                            ("asset", "CompanyShare:MSFT")]))
    assert r.status_code == 302
    assert services().configurations.get(sid).section("universe")["instruments"] == {"CompanyShare": ["AAPL", "MSFT"]}
    name = json.dumps(["portfolio", "deciles", "weighting"])
    client.post(design, data={"part": "params", "section": "portfolio", name: '"volatility_weight"'})
    assert services().configurations.get(sid).section("portfolio")["deciles"]["weighting"] == "volatility_weight"


@pytest.fixture
def web_decile(web):
    r = web.client.post("/strategies/new", data={"name": "deciles picks", "project_key": "stm_monthly_decile_project"})
    design = r.headers["Location"]
    return web.client, design, int(design.split("/")[-2]), web.services


@pytest.fixture
def web(tmp_path, monkeypatch):
    from tests.strategy.test_strategy_web import web as base_web
    yield from base_web.__wrapped__(tmp_path, monkeypatch)


def test_the_project_form_posts_ticked_lists(web):
    r = web.client.post("/strategies/new", data={"name": "csm picks", "project_key": "cross_sectional"})
    cid = int(r.headers["Location"].split("/")[-2])
    page = web.client.get(f"/strategies/{cid}/edit").get_data(as_text=True)
    assert 'type="checkbox" name="universe.tickers"' in page
    assert not re.search(r'<input class="form-control"[^>]*name="model\.', page)        # numbers are dropdowns


def test_a_universe_mixes_asset_types_and_factors_are_filtered_by_entity(web_decile):
    client, design, sid, services = web_decile
    page = client.get(design).get_data(as_text=True)
    assert 'name="horizon_unit"' in page and "tick sector" in page and "tick universe" in page
    assert 'data-facet="entity"' in page and "Save ticked as universe" in page
    r = client.post(design, data=MultiDict([("part", "assets"), ("asset", "CompanyShare:AAPL"),
                                            ("asset", "CompanyShareOption:AAPL  261218C00250000")]))
    assert r.status_code == 302
    instruments = services().configurations.get(sid).section("universe")["instruments"]
    assert instruments == {"CompanyShare": ["AAPL"], "CompanyShareOption": ["AAPL  261218C00250000"]}
    # the launch config holds both asset types
    s = services()
    strategy = s.configurations.get(sid)
    config = s.registry.get(strategy.strategy_type).native_config_for(strategy, strategy.sections)
    assert sorted(k.__name__ for k in config["universe"]) == ["CompanyShare", "CompanyShareOption"]


def test_the_prediction_horizon_is_picked_in_periods_and_stored_in_rows(web_decile):
    client, design, sid, services = web_decile
    # weekly rebalancing (one row = one week): a 1-month horizon = 21 / 5 trading days -> 4 rows
    client.post(design, data={"part": "definition", "trading_unit": "weeks", "trading_count": "1",
                              "horizon_unit": "months", "horizon_count": "1"})
    assert services().configurations.get(sid).prediction_horizon == 4
    html = client.post(design, data={"part": "definition", "horizon_unit": "days", "horizon_count": "2"},
                       follow_redirects=True).get_data(as_text=True)
    assert "shorter than one row" in html


def test_factor_entities_and_factor_universes():
    from src.application.services.strategy.strategy_design_service import factor_entity
    assert factor_entity("company_share_option_factor") == "CompanyShareOption"
    assert factor_entity("company_share_spatio_temporal_feature_factor") == "CompanyShare"
    assert factor_entity("etf_share_implied_dispersion_factor") == "ETFShare"
    assert factor_entity("company_share_portfolio_holding_value_factor") == "CompanySharePortfolioHolding"
    assert factor_entity("index_factor") == "Index" and factor_entity("weird") == "Other"


def test_the_ticked_factors_can_be_saved_as_a_factor_universe(web_decile):
    client, design, sid, services = web_decile
    from src.domain.entities.factor.factor import Factor  # noqa: F401  (models registered)
    s = services()
    session = s.session
    from sqlalchemy import text
    session.execute(text(
        "INSERT INTO factors (id, name, \"group\", subgroup, frequency, data_type, source, definition, factor_type) "
        "VALUES (901, 'ret_1', 'price', 'TRADES', '1d', 'numeric', 'ibkr', '-', 'company_share_factor'), "
        "(902, 'iv', 'option', 'greeks', '1d', 'numeric', 'ibkr', '-', 'company_share_option_factor')"))
    session.commit()
    r = client.post(design, data=MultiDict([("part", "factor_universe"), ("factor_universe_name", "my factors"),
                                            ("factor_id", "901"), ("factor_id", "902")]))
    assert r.status_code == 302
    page = client.get(design).get_data(as_text=True)
    assert "my factors v1 (2 factors)" in page
    html = client.post(design, data={"part": "factor_universe", "factor_universe_name": ""},
                       follow_redirects=True).get_data(as_text=True)
    assert "needs a name" in html
