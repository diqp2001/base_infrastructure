"""ETF option dispersion factors: ETFShareRealizedDispersionFactor and ETFShareImpliedDispersionFactor (their formulas,
weight normalization and coverage, names), resolved end to end through FactorValueResolutionService on the SQLite
factor world (an ETF holding AAPL / MSFT): per-constituent inputs, point-in-time weights, the values stored in
factor_values; and the load job (in-memory SQLite, temp folders)."""

import math
from datetime import date, datetime

import pytest

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_dispersion_factor import (
    dispersion_factor_name, normalize_weights,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_implied_dispersion_factor import (
    ETFShareImpliedDispersionFactor, atm_option_series_name,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_realized_dispersion_factor import (
    ETFShareRealizedDispersionFactor, option_payoff,
)

W3 = {"A": 0.5, "B": 0.3, "C": 0.2}
LEGS = {"A": [100.0, 120.0], "B": [100.0, 90.0], "C": [100.0, 115.0]}


def realized(right, measure="dispersion", months=1, etf=(100.0, 110.0), legs=LEGS, weights=W3):
    return ETFShareRealizedDispersionFactor(dispersion_factor_name("realized", right, measure, months)).calculate(
        {"etf_close": list(etf), "constituent_close": legs, "weights": weights})


def implied(measure="dispersion", etf=(0.05, 30.0), legs=None, weights=None, right="call"):
    legs = legs if legs is not None else {"A": (0.08, 30.0), "B": (0.03, 31.0)}
    return ETFShareImpliedDispersionFactor(dispersion_factor_name("implied", right, measure, 1)).calculate({
        "etf_premium": [etf[0]] if etf[0] is not None else [], "etf_dte": [etf[1]],
        "constituent_premium": {s: [p] for s, (p, _) in legs.items() if p is not None},
        "constituent_dte": {s: [d] for s, (_, d) in legs.items()},
        "weights": weights or {"A": 0.6, "B": 0.4}})


# ---- realized: sum_i w_i payoff_i - payoff_ETF ----------------------------------------------------------------------

def test_atm_call_and_put_payoffs_per_unit_of_price():
    assert option_payoff("call", 100.0, 110.0) == pytest.approx(0.10) and option_payoff("call", 100.0, 95.0) == 0.0
    assert option_payoff("put", 100.0, 90.0) == pytest.approx(0.10) and option_payoff("put", 100.0, 105.0) == 0.0


def test_realized_call_dispersion_owner_example():
    # ETF 100 -> 110; A 50 % +20 %, B 30 % -10 %, C 20 % +15 %: basket 13 %, ETF 10 %, dispersion +3 %
    assert realized("call", "etf") == pytest.approx(0.10) and realized("call", "basket") == pytest.approx(0.13)
    assert realized("call") == pytest.approx(0.03)
    assert realized("call", "etf_return") == pytest.approx(0.10) and realized("call", "constituents") == 3.0
    # a basket of calls, not a call on the basket: max(sum w r, 0) would be 10 %
    assert realized("call", "basket") != pytest.approx(max(0.5 * 0.2 + 0.3 * -0.1 + 0.2 * 0.15, 0.0))


def test_realized_put_dispersion_and_the_call_put_identity():
    assert realized("put", "etf") == 0.0 and realized("put", "basket") == pytest.approx(0.3 * 0.10)
    tracking = sum(W3[s] * (e / b - 1) for s, (b, e) in LEGS.items()) - 0.10           # sum w r - r_ETF
    assert realized("call") - realized("put") == pytest.approx(tracking)


def test_missing_constituent_data_is_never_a_zero():
    legs = {"A": [100.0, 120.0], "B": []}                                            # B has no window
    assert realized("call", legs=legs, weights={"A": 0.5, "B": 0.5}) is None
    assert realized("call", "weight_coverage", legs=legs, weights={"A": 0.5, "B": 0.5}) == pytest.approx(0.5)
    assert realized("call", etf=(100.0,)) is None
    assert realized("call", weights={}) is None


def test_weights_are_renormalized_over_the_available_constituents():
    w, coverage = normalize_weights({"A": 0.5, "B": 0.3, "C": 0.2}, {"A", "C"})
    assert w == pytest.approx({"A": 0.5 / 0.7, "C": 0.2 / 0.7}) and coverage == pytest.approx(0.7)
    assert normalize_weights({"A": 2.0, "B": 2.0}, {"A", "B"})[0] == pytest.approx({"A": 0.5, "B": 0.5})


# ---- implied: sum_i w_i premium_i / S_i - premium_ETF / ETF ---------------------------------------------------------

def test_implied_dispersion_is_premium_over_price():
    # ETF 5 %; A 8 % (60 %), B 3 % (40 %): basket 6 %, dispersion +1 %
    assert implied("etf") == pytest.approx(0.05) and implied("basket") == pytest.approx(0.06)
    assert implied() == pytest.approx(0.01) and implied("max_dte_gap") == 1.0 and implied("constituents") == 2.0


def test_implied_leaves_out_a_constituent_with_another_maturity_or_no_quote():
    far = {"A": (0.08, 30.0), "B": (0.03, 60.0)}                                       # B expires a month later
    assert implied(legs=far) is None and implied("weight_coverage", legs=far) == pytest.approx(0.6)
    no_quote = {"A": (0.08, 30.0), "B": (None, 30.0)}
    assert implied(legs=no_quote) is None and implied(etf=(None, 30.0)) is None


def test_the_two_factors_are_separate_and_names_carry_their_parameters():
    assert dispersion_factor_name("realized", "put", "weight_coverage", 6) == "realized_put_weight_coverage_6m"
    r = ETFShareRealizedDispersionFactor("realized_put_basket_2m")
    assert (r.right, r.measure, r.months, r.lookback) == ("put", "basket", 2, 43)
    assert r.related_as_of(date(2026, 11, 6)) == date(2026, 9, 6)                    # the holding period's start
    i = ETFShareImpliedDispersionFactor("implied_call_dispersion_3m")
    assert i.related_as_of(datetime(2026, 11, 6, 15, 0)) == date(2026, 11, 6)
    assert [d.name_in for d in i.calculate_dependencies][0] == [atm_option_series_name("call", "premium", 3)]
    # neither decodes the other's names: a foreign / odd name has no parameters and no value
    for odd in (ETFShareRealizedDispersionFactor("implied_call_dispersion_1m"),
                ETFShareImpliedDispersionFactor("realized_call_dispersion_1m"),
                ETFShareImpliedDispersionFactor("implied_call_etf_return_1m")):
        assert odd.months is None and odd.calculate_dependencies == [] and odd.calculate({}) is None


# ---- end to end: FactorValueResolutionService on the SQLite factor world --------------------------------------------

@pytest.fixture(scope="module")
def world():
    from tests.component.factor_context.factor_world import FactorWorld
    w = FactorWorld()
    w.etf()
    return w


def expected_realized(world, right, months, weights, measure="dispersion"):
    n = 21 * months + 1
    legs = {t: [world.closes[t][-n], world.closes[t][-1]] for t in weights}
    return realized(right, measure, months, (world.etf_closes[-n], world.etf_closes[-1]), legs, weights)


@pytest.mark.parametrize("right,months", [("call", 1), ("put", 1), ("call", 3), ("put", 6)])
def test_the_service_computes_the_realized_dispersion(world, right, months):
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    value, deps = world.resolve(ETFShareRealizedDispersionFactor, world.etf(),
                                name=dispersion_factor_name("realized", right, "dispersion", months))
    assert set(deps["constituent_close"]) == {"AAPL", "MSFT"}                         # attributed per constituent
    assert deps["weights"] == {"AAPL": 0.6, "MSFT": 0.4}
    assert len(deps["etf_close"]) == 2 and all(len(v) == 2 for v in deps["constituent_close"].values())
    assert value == pytest.approx(expected_realized(world, right, months, {"AAPL": 0.6, "MSFT": 0.4}))
    stored = world.s.query(FactorValueModel).filter_by(entity_id=world.etf().id, entity_type="ETFShare").all()
    assert any(math.isclose(float(r.value), value) for r in stored)                   # in factor_values, under the ETF


def test_realized_component_measures(world):
    weights = {"AAPL": 0.6, "MSFT": 0.4}
    for measure in ("etf", "basket", "weight_coverage", "constituents", "etf_return"):
        value, _ = world.resolve(ETFShareRealizedDispersionFactor, world.etf(),
                                 name=dispersion_factor_name("realized", "call", measure, 2))
        assert value == pytest.approx(expected_realized(world, "call", 2, weights, measure)), measure


def test_the_service_computes_the_implied_dispersion_from_the_atm_series(world):
    value, deps = world.resolve(ETFShareImpliedDispersionFactor, world.etf(), name="implied_put_dispersion_1m")
    atm = world.ATM
    assert deps["etf_premium"] == [atm["TEST"][0]] and set(deps["constituent_premium"]) == {"AAPL", "MSFT"}
    assert value == pytest.approx(0.6 * atm["AAPL"][0] + 0.4 * atm["MSFT"][0] - atm["TEST"][0])


def test_weights_are_the_ones_in_force_at_the_start_of_the_holding_period(world):
    """A constituent that joined after the start of the holding period is not in that observation's basket."""
    from src.domain.entities.universe.universe_constituent import UniverseConstituent
    from tests.component.factor_context.factor_world import T
    universe = world.f.get_local_repository("InvestmentUniverse").get_by_name("TEST holdings")
    members = world.f.get_local_repository("UniverseConstituent")
    late = members.add(UniverseConstituent(universe_id=universe.id, entity_id=world.share["SPY"].id,
                                           entity_type="CompanyShare", start_date=date(2025, 12, 20), weight=0.5))
    try:
        repo = world.f.get_local_repository("ETFShare")
        assert "SPY" not in repo.get_related_weights(world.etf().id, target_date=date(2025, 12, 5))
        assert repo.get_related_weights(world.etf().id, target_date=T)["SPY"] == 0.5
        value, deps = world.resolve(ETFShareRealizedDispersionFactor, world.etf(), name="realized_put_dispersion_4m")
        assert "SPY" not in deps["weights"] and "SPY" not in deps["constituent_close"]
        assert value == pytest.approx(expected_realized(world, "put", 4, {"AAPL": 0.6, "MSFT": 0.4}))
    finally:
        members.delete(late.id)


# ---- the load job: closes, ATM series, holdings and values in the factor value table -------------------------------

def _job_folders(tmp_path, as_of, job, weights):
    import json as _json
    from datetime import timedelta
    results, cache = tmp_path / "results", tmp_path / "prices"
    (results / as_of.isoformat()).mkdir(parents=True)
    cache.mkdir()
    (results / as_of.isoformat() / "universe.json").write_text(_json.dumps({"etfs": [{
        "ticker": "ETFX", "status": "eligible", "holdings_as_of": "2026-11-05", "weights": weights,
        "equity_share": 1.0, "holdings_source": "test"}]}), encoding="utf-8")
    start = job.history_start(as_of)
    days = [start + timedelta(days=i) for i in range((as_of - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5]
    paths = {"ETFX": lambda i: 100.0 + 0.05 * i, "AAA": lambda i: 50.0 + 3.0 * math.sin(i / 9.0),
             "BBB": lambda i: 80.0 - 2.0 * math.sin(i / 7.0)}
    for symbol, f in paths.items():
        (cache / f"{symbol}.json").write_text(_json.dumps({
            "symbol": symbol, "start": start.isoformat(), "fetched_for": as_of.isoformat(),
            "closes": {d.isoformat(): f(i) for i, d in enumerate(days)}}), encoding="utf-8")
    return results, cache, days


def test_the_load_job_stores_inputs_holdings_and_both_dispersion_factors(tmp_path):
    from src.application.managers.project_managers.etf_dispersion_screener_project import dispersion_factors as job
    from src.infrastructure.models.factor.factor import (
        ETFShareImpliedDispersionFactorModel, ETFShareRealizedDispersionFactorModel,
    )
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from tests.dispersion.test_maturities import FakeMarket
    from tests.misbuffet.sqlite_portfolio import SqlitePortfolio
    as_of = date(2026, 11, 6)
    results, cache, days = _job_folders(tmp_path, as_of, job, {"AAA": 0.5, "BBB": 0.5})
    config = {"results_dir": str(results), "price_history_dir": str(cache), "ibkr": {}}
    # the quotes step on a fake market (its quotes are stamped at NOW, Thursday 10:00 New York): an ATM call / put
    # per underlying and maturity
    spots = {"ETFX": 100.0, "AAA": 50.0, "BBB": 80.0}
    quotes = {"ETFX": (2.0, 2.2, 0.2), "AAA": (1.5, 1.7, 0.3), "BBB": (2.4, 2.6, 0.3)}
    from tests.dispersion.test_dispersion_screening_service import NOW
    now = NOW.astimezone(job.NEW_YORK)
    path = job.fetch_atm_options(as_of.isoformat(), None, config, FakeMarket(spots, quotes), now=lambda: now)
    p = SqlitePortfolio(cash=0.0, shares=("AAA", "BBB"))
    out = job.load(as_of.isoformat(), ["ETFX"], measures=("dispersion", "weight_coverage"), every=10,
                   factory=p.factory, config=config)[0]
    assert "skipped" not in out, out
    assert out["closes_stored"] == 3 * len(days) and "back-cast" in out["membership"]
    assert out["implied_times"] == 1 and out["realized_values"] > 0, out
    etf = p.factory.get_local_repository("ETFShare").get_by_symbol("ETFX")
    assert p.factory.get_local_repository("ETFShare").get_related_weights(etf.id, target_date=date(2026, 6, 1)) == \
        {"AAA": 0.5, "BBB": 0.5}                                                       # back-cast holdings in force
    for model, kind in ((ETFShareRealizedDispersionFactorModel, "realized"),
                        (ETFShareImpliedDispersionFactorModel, "implied")):
        factors = p.session.query(model).all()
        assert factors and all(f.name.startswith(kind) for f in factors)
        assert p.session.query(FactorValueModel).filter(FactorValueModel.factor_id.in_([f.id for f in factors]),
                                                        FactorValueModel.entity_id == etf.id).count() > 0
    implied_1m = p.factory.get_local_repository("ETFShareImpliedDispersionFactor").get_by_name(
        "implied_call_dispersion_1m")
    row = p.session.query(FactorValueModel).filter_by(factor_id=implied_1m.id, entity_id=etf.id).one()
    mids = {s: (b + a) / 2 / spots[s] for s, (b, a, _) in quotes.items()}
    assert float(row.value) == pytest.approx(0.5 * mids["AAA"] + 0.5 * mids["BBB"] - mids["ETFX"])
    assert row.date == datetime(2026, 11, 5, 10, 0) and path.endswith(".json")
    again = job.load(as_of.isoformat(), ["ETFX"], measures=("dispersion",), every=10, factory=p.factory,
                     config=config)
    assert again[0]["closes_stored"] == 0                                             # a rerun adds no duplicate


def test_the_load_job_skips_an_etf_without_every_price(tmp_path):
    import json as _json
    from src.application.managers.project_managers.etf_dispersion_screener_project import dispersion_factors as job
    from tests.misbuffet.sqlite_portfolio import SqlitePortfolio
    (tmp_path / "2026-11-06").mkdir()
    (tmp_path / "2026-11-06" / "universe.json").write_text(_json.dumps({"etfs": [{
        "ticker": "ETFX", "status": "eligible", "holdings_as_of": "2026-11-05", "weights": {"AAA": 1.0},
        "equity_share": 1.0, "holdings_source": "test"}]}), encoding="utf-8")
    p = SqlitePortfolio(cash=0.0, shares=("AAA",))
    out = job.load("2026-11-06", None, factory=p.factory,
                   config={"results_dir": str(tmp_path), "price_history_dir": str(tmp_path / "none")})
    assert out == [{"etf": "ETFX", "skipped": "no price history for ETFX, AAA (2)"}]
    assert p.factory.get_local_repository("ETFShare").get_by_symbol("ETFX") is None   # nothing written


def _atm_market(failing=(), unlisted=()):
    """FakeMarket whose chain lookups fail for `failing`, and whose chain strike nearest the spot is not listed for
    the expiry for `unlisted` (no quote at it; the expiry's own list does not have it)."""
    from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
    from tests.dispersion.test_dispersion_screening_service import SPOTS, FakeMarket

    class Market(FakeMarket):
        asked_listed = []

        def option_chains(self, underlying, screening_date):
            if underlying.symbol in failing:
                raise MarketDataUnavailable(f"{underlying.symbol} chain not answered")
            return super().option_chains(underlying, screening_date)

        def listed_strikes(self, chain, expiry, right, screening_date):
            self.asked_listed.append(chain.underlying)
            spot = self.spots[chain.underlying]
            return tuple(k for k in chain.strikes if chain.underlying not in unlisted or abs(k - spot) > 0.01)

        def option_quotes(self, contracts, screening_date):
            out = super().option_quotes(contracts, screening_date)
            return {k: v for k, v in out.items()
                    if not (v.contract.underlying in unlisted and abs(v.contract.strike - self.spots[
                        v.contract.underlying]) <= 0.01)}

    return Market(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})


def test_atm_options_take_the_chain_strike_and_fall_back_to_the_expiry_list_when_it_is_not_listed():
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    from src.application.services.dispersion.screen_config import DispersionScreenConfig
    from tests.dispersion.test_dispersion_screening_service import DAY, NOW, SPOTS
    market = _atm_market(unlisted={"A"})
    out = DispersionScreeningService(market, DispersionScreenConfig(), now=lambda: NOW).atm_options(
        ["ETF", "A", "B"], 30, DAY, max_atm_deviation=0.06)                    # the fake's strikes are 5 % apart
    assert market.asked_listed == ["A"]                                  # one expiry list, for A only
    assert out["ETF"].strike == SPOTS["ETF"] and out["A"].problem is None and out["A"].strike != SPOTS["A"]
    assert out["A"].mid == pytest.approx(1.225)


def test_atm_options_reports_an_unanswered_lookup_per_symbol_and_stops_when_the_source_is_down():
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    from src.application.services.dispersion.screen_config import DispersionScreenConfig
    from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
    from tests.dispersion.test_dispersion_screening_service import DAY, NOW
    out = DispersionScreeningService(_atm_market(failing={"A"}), DispersionScreenConfig(), now=lambda: NOW
                                     ).atm_options(["ETF", "A", "B"], 30, DAY)
    assert out["A"].problem.startswith("data unavailable") and out["A"].mid is None
    assert out["ETF"].mid == pytest.approx(5.05) and out["B"].problem is None
    down = DispersionScreeningService(_atm_market(failing={"ETF", "A", "B"}), DispersionScreenConfig(),
                                      now=lambda: NOW)
    with pytest.raises(MarketDataUnavailable):
        down.atm_options(["ETF", "A", "B"], 30, DAY)
