"""ETF option dispersion strategy factors (ETFShareOptionNetPremium / ReversePremium / ImpliedCorrelation /
ScenarioPayoff): their formulas from the quote series, and the strategies step that stores the screen's results and
resolves them through the factor pipeline (in-memory SQLite only)."""

import json
from datetime import date, datetime

import pytest

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor as Strategy,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_implied_correlation_factor import (
    ETFShareOptionImpliedCorrelationFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_net_premium_factor import (
    ETFShareOptionNetPremiumFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_reverse_premium_factor import (
    ETFShareOptionReversePremiumFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor import (
    ETFShareOptionScenarioPayoffFactor,
)

ETF = {"bid": 2.0, "ask": 2.2, "iv": 0.20, "bid_iv": 0.19, "ask_iv": 0.21, "delta": 0.5, "gamma": 0.05, "vega": 0.1,
       "theta": -0.02, "underlying_price": 100.0, "strike": 100.0, "multiplier": 100.0}
LEGS = {"AAA": {"bid": 1.5, "ask": 1.7, "iv": 0.30, "bid_iv": 0.29, "ask_iv": 0.31, "delta": 0.5, "gamma": 0.08,
                "vega": 0.06, "theta": -0.02, "underlying_price": 50.0, "strike": 50.0, "multiplier": 100.0},
        "BBB": {"bid": 2.4, "ask": 2.6, "iv": 0.28, "bid_iv": 0.27, "ask_iv": 0.29, "delta": 0.5, "gamma": 0.05,
                "vega": 0.09, "theta": -0.03, "underlying_price": 80.0, "strike": 80.0, "multiplier": 100.0}}
WEIGHTS = {"AAA": 0.6, "BBB": 0.4}


class _Option:
    def __init__(self, option_type):
        self.option_type = option_type


def deps(right="call", etf=None, legs=None, weights=None):
    etf, legs = etf or ETF, legs or LEGS
    out = {"weights": dict(weights or WEIGHTS), "entity": _Option(right)}
    for field, value in etf.items():
        out[f"etf_{field}"] = [value]
    for field in ETF:
        out[f"constituent_{field}"] = {s: [q[field]] for s, q in legs.items() if q.get(field) is not None}
    return out


def legs(right="C"):
    etf = Strategy.leg("ETF", ETF, 1.0, right)
    return etf, [Strategy.leg(s, LEGS[s], WEIGHTS[s], right) for s in LEGS]


def test_the_net_premium_factor_is_the_screens_net_premium_from_the_quote_series():
    etf, constituents = legs()
    expected = Strategy.premium(etf, constituents, Strategy.replicate(etf, constituents))
    value = ETFShareOptionNetPremiumFactor("premium_net").calculate(deps())
    assert value == pytest.approx(expected.net_premium)
    # per ETF call: 100 x 2.0 sold; AAA 100 x 0.6 x 100 / 50 / 100 = 1.2 contracts at 1.7, BBB 0.5 at 2.6
    assert value == pytest.approx(200.0 - (1.2 * 100 * 1.7 + 0.5 * 100 * 2.6))
    assert ETFShareOptionNetPremiumFactor("premium_short_proceeds").calculate(deps()) == pytest.approx(200.0)
    assert ETFShareOptionNetPremiumFactor("premium_mid_net").calculate(deps()) == pytest.approx(expected.mid_net_premium)


def test_the_reverse_premium_and_implied_correlation_factors():
    etf, constituents = legs()
    reverse = Strategy.reverse_premium(etf, constituents, Strategy.replicate(etf, constituents))
    assert ETFShareOptionReversePremiumFactor("reverse_premium_net").calculate(deps()) == \
        pytest.approx(reverse.net_premium)
    assert ETFShareOptionImpliedCorrelationFactor("implied_correlation_model").calculate(deps()) == \
        pytest.approx(Strategy.implied_correlation(0.20, constituents))
    assert ETFShareOptionImpliedCorrelationFactor("implied_correlation_etf_bid").calculate(deps()) == \
        pytest.approx(Strategy.implied_correlation(0.19, constituents, vol="ask_implied_vol"))
    # a missing bid volatility blocks only the measures that read it
    no_bid_iv = {s: {**q, "bid_iv": None} for s, q in LEGS.items()}
    assert ETFShareOptionImpliedCorrelationFactor("implied_correlation_model").calculate(deps(legs=no_bid_iv)) is not None
    assert ETFShareOptionImpliedCorrelationFactor("implied_correlation_etf_ask").calculate(deps(legs=no_bid_iv)) is None


def test_a_missing_leg_or_input_gives_no_value_never_a_partial_basket():
    f = ETFShareOptionNetPremiumFactor("premium_net")
    assert f.calculate(deps(legs={"AAA": LEGS["AAA"]})) is None                    # BBB has no quote
    assert f.calculate(deps(etf={**ETF, "bid": None})) is None
    assert f.calculate({**deps(), "weights": {}}) is None
    assert f.calculate(deps(right="straddle")) is None


def test_the_scenario_payoff_uses_the_options_right():
    etf, constituents = legs("P")
    sizing = Strategy.replicate(etf, constituents)
    net = Strategy.premium(etf, constituents, sizing).net_premium
    rows = {r["key"]: r for r in Strategy.scenarios(etf, constituents, sizing, net)}
    down = rows["market_down10"]
    # puts: every underlying 10 % lower - the long puts pay 1.2 x 100 x 5 + 0.5 x 100 x 8, the short ETF put 100 x 10
    assert down["long_basket"] == pytest.approx(1.2 * 100 * 5 + 0.5 * 100 * 8)
    assert down["short_etf"] == pytest.approx(-100 * 10)
    assert rows["market_up10"]["long_basket"] == pytest.approx(0.0)
    f = ETFShareOptionScenarioPayoffFactor("scenario_market_down10_pnl")
    assert f.calculate(deps(right="put")) == pytest.approx(down["pnl"])
    assert ETFShareOptionScenarioPayoffFactor("scenario_market_up10_long_basket").calculate(deps(right="call")) > 0


def test_names_carry_the_measure_and_foreign_names_decode_to_nothing():
    assert ETFShareOptionNetPremiumFactor("premium_net_pct").measure == "net_pct"
    assert ETFShareOptionScenarioPayoffFactor("scenario_dispersion_flat_pnl").measure == "dispersion_flat_pnl"
    for odd in (ETFShareOptionNetPremiumFactor("reverse_premium_net"), ETFShareOptionReversePremiumFactor("premium_net"),
                ETFShareOptionScenarioPayoffFactor("scenario_market_up7_pnl")):
        assert odd.measure is None and odd.calculate_dependencies == [] and odd.calculate(deps()) is None
    specs = ETFShareOptionImpliedCorrelationFactor("implied_correlation_model").calculate_dependencies
    assert {s.result_key for s in specs} == {f"{side}_{f}" for side in ("etf", "constituent")
                                             for f in ("underlying_price", "strike", "multiplier", "iv")}


# ---- the strategies step: files -> base_infra rows -> factor values (in-memory SQLite) ----

def _row(right="C"):
    leg = lambda s, w: {"ticker": s, "weight": w, "status": "ok", "price": LEGS[s]["underlying_price"],
                        "expiry": "2026-12-18", "strike": LEGS[s]["strike"], "multiplier": 100.0,
                        "call_bid": LEGS[s]["bid"], "call_ask": LEGS[s]["ask"], "iv": LEGS[s]["iv"],
                        "bid_iv": LEGS[s]["bid_iv"], "ask_iv": LEGS[s]["ask_iv"], "delta": LEGS[s]["delta"],
                        "contracts": 1.0, "quote_time": "2026-11-06 15:00:05+00:00"}
    return {"etf": "ETFX", "name": "Test ETF", "status": "rejected", "expiry": "2026-12-18", "etf_spot": 100.0,
            "etf_strike": 100.0, "etf_call_bid": 2.0, "etf_call_ask": 2.2, "etf_iv": 0.20, "etf_bid_iv": 0.19,
            "etf_ask_iv": 0.21, "etf_contracts": 1.0, "notional": 10000.0, "etf_dollar_delta": -5000.0,
            "etf_quote_time": "2026-11-06 15:00:00+00:00", "right": right,
            # a constituent the screen could not use: not a leg (the weights are renormalized over the legs)
            "constituent_legs": [leg("AAA", 0.48), leg("BBB", 0.32),
                                 {"ticker": "CCC", "weight": 0.2, "status": "no ask", "contracts": None}]}


def test_the_strategies_step_stores_the_legs_quotes_and_strategy_factor_values(tmp_path):
    from src.application.managers.project_managers.etf_dispersion_screener_project import (
        dispersion_strategy_factors as job,
    )
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from tests.misbuffet.sqlite_portfolio import SqlitePortfolio
    day = tmp_path / "2026-11-06"
    (day / "puts").mkdir(parents=True)
    (day / "candidates.json").write_text(json.dumps([_row("C")]), encoding="utf-8")
    (day / "puts" / "ETFX.json").write_text(json.dumps({"etf": "ETFX", "trade": _row("P")}), encoding="utf-8")
    p = SqlitePortfolio(cash=0.0, shares=("AAA", "BBB"))
    config = {"results_dir": str(tmp_path), "price_history_dir": str(tmp_path / "prices")}
    out = job.load_strategies("2026-11-06", factory=p.factory, config=config)
    assert [o["source"] for o in out] == ["screen", "puts"] and not any("skipped" in o for o in out), out
    call = out[0]
    assert call["option"] == "ETFX  261218C00100000" and call["legs"] == 2 and call["at"] == "2026-11-06 10:00:05"
    etf, constituents = legs("C")
    sizing = Strategy.replicate(etf, constituents)
    premium = Strategy.premium(etf, constituents, sizing)
    assert call["values"]["premium_net"] == pytest.approx(premium.net_premium, abs=1e-6)
    assert call["values"]["implied_correlation_model"] == pytest.approx(
        Strategy.implied_correlation(0.20, constituents), abs=1e-6)
    assert "scenario_dispersion_up5_pnl" in call["values"] and "scenario_dispersion_up5_combined" not in call["values"]
    put_etf, put_legs = legs("P")
    put_sizing = Strategy.replicate(put_etf, put_legs)
    put_rows = {r["key"]: r for r in Strategy.scenarios(put_etf, put_legs, put_sizing,
                                                        Strategy.premium(put_etf, put_legs, put_sizing).net_premium)}
    assert out[1]["values"]["scenario_market_down10_pnl"] == pytest.approx(put_rows["market_down10"]["pnl"], abs=1e-6)
    # the legs are the ETF option's related entities on the screen's day only (point in time)
    options = p.factory.get_local_repository("ETFShareOption")
    option = options.get_by_symbol("ETFX  261218C00100000")
    weights = options.get_related_weights(option.id, target_date=date(2026, 11, 6))
    assert weights == pytest.approx({"AAA   261218C00050000": 0.6, "BBB   261218C00080000": 0.4})
    assert options.get_related_weights(option.id, target_date=date(2026, 11, 7)) == {}
    stored = p.session.query(FactorValueModel).filter_by(entity_id=option.id, entity_type="ETFShareOption").all()
    assert {r.date for r in stored} == {datetime(2026, 11, 6, 10, 0, 5)}
    again = job.load_strategies("2026-11-06", factory=p.factory, config=config)
    assert again[0]["quotes_stored"] == 0 and again[0]["legs_stored"] == 0                  # a rerun adds nothing
    assert again[0]["values"] == call["values"]
