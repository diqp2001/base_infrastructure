"""Monthly model-filtered ETF dispersion (etf_dispersion_stm_project): point-in-time membership, N fixed on the full
basket before the model filter, premiums, payoffs, the STM scorer without look-ahead, the Eulerpool closes adapter
and an end-to-end synthetic backtest. In-memory data only: no API, no database, no file outside tmp_path."""

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.synthetic_demo import (
    run_synthetic_demo,
    synthetic_world,
    tiny_stm,
)
from src.application.managers.project_managers.etf_dispersion_stm_project.data.dia_universe import build_membership
from src.application.services.dispersion.dispersion_report import (
    constituent_rows,
    pnl_stats,
    trade_rows,
    write_report,
)
from src.application.services.dispersion.dispersion_trading_cycle import known_through, occ_symbol
from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    FRACTIONAL,
    WHOLE,
    DispersionPortfolioConstructionService,
)
from src.application.services.dispersion.index_membership import (
    ETF_ENTITY_TYPE,
    IndexMembership,
    MembershipChange,
    Split,
)
from src.application.services.dispersion.model_selection import ModelFilterConfig, Selection, select_constituents
from src.application.services.dispersion.modelled_option_pricing import (
    ModelledOptionPricer,
    OptionModelConfig,
    realised_vol,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import STMConstituentScorer
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    Leg,
)
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable


# ---------------------------------------------------------------- membership
def membership():
    return IndexMembership("ETF", date(2020, 1, 2), ["A", "B", "C"],
                           [MembershipChange(date(2021, 3, 1), added=("D",), removed=("C",))],
                           [Split("A", date(2021, 6, 1), 2.0)])


def test_membership_is_point_in_time_and_keeps_the_etf_in_the_universe():
    m = membership()
    assert m.members_at(date(2021, 2, 26)) == ["A", "B", "C"]
    assert m.members_at(date(2021, 3, 1)) == ["A", "B", "D"]
    assert m.all_constituents() == ["A", "B", "C", "D"]
    etf_rows = [r for r in m.constituents if r.entity_type == ETF_ENTITY_TYPE]
    assert len(etf_rows) == 1 and etf_rows[0].end_date is None
    c_row = next(r for r in m.constituents if r.entity_id == m.entity_id("C"))
    assert c_row.end_date == date(2021, 2, 28) and c_row.universe_id == m.universe.id
    with pytest.raises(ValueError):
        m.members_at(date(2019, 12, 31))
    with pytest.raises(ValueError):          # removing a non-member is a configuration error
        IndexMembership("ETF", date(2020, 1, 2), ["A"], [MembershipChange(date(2021, 1, 4), removed=("Z",))])


def test_price_weights_use_the_traded_price_before_a_split():
    m = membership()
    closes = {"ETF": 30.0, "A": 50.0, "B": 100.0, "D": 50.0}       # A split-adjusted: traded at 100 before June
    w = m.price_weights(date(2021, 5, 3), closes)
    assert w == pytest.approx({"A": 0.4, "B": 0.4, "D": 0.2})
    assert m.price_weights(date(2021, 6, 1), closes)["A"] == pytest.approx(0.25)
    assert m.replication_ratio(date(2021, 5, 3), closes) == pytest.approx(30 / 250)
    with pytest.raises(ValueError):
        m.price_weights(date(2021, 5, 3), {"A": 50.0, "B": 100.0})


def test_the_project_membership_matches_the_published_djia_changes():
    m = build_membership()
    assert len(m.members_at(date(2020, 9, 18))) == 30
    assert "WBA" in m.members_at(date(2024, 2, 23)) and "AMZN" in m.members_at(date(2024, 2, 26))
    late = m.members_at(date(2026, 10, 16))
    assert {"NVDA", "SHW", "GOOGL"} <= set(late) and not {"INTC", "DOW", "VZ", "WBA"} & set(late)
    assert all(len(m.members_at(d)) == 30 for d in (date(2023, 1, 3), date(2025, 1, 3), date(2026, 7, 1)))


# ---------------------------------------------------------------- construction
def leg(symbol, spot, price, weight=1.0, strike=None):
    return Leg(symbol, spot, strike if strike is not None else spot, 100.0, price, price, weight)


def spec_example():
    """30 equal-share members (price-weighted), sum of prices = 18 x ETF price -> one ETF call replicates 1/18
    contract of each: N = 18 and one call per member. Calls: ETF 10.00; the 10 'good' members 11.50, the rest 3.25
    -> full basket $18,000 = short premium, selected (10) $11,500."""
    prices = [300.0] * 30                                      # sum 9 000 = 18 x 500
    etf = leg("ETF", 500.0, 10.0)
    members = [f"S{i:02d}" for i in range(30)]
    legs = [leg(s, p, 11.5 if i < 10 else 3.25, weight=p / sum(prices)) for i, (s, p) in enumerate(zip(members, prices))]
    return etf, legs, members


def test_n_short_etf_calls_is_fixed_on_the_full_basket_before_the_filter():
    etf, legs, members = spec_example()
    svc = DispersionPortfolioConstructionService(WHOLE)
    assert svc.baseline_short_contracts(etf, legs) == 18
    picked = Selection(selected=members[:10], rejected={s: "low score" for s in members[10:]})
    t = svc.construct(date(2024, 1, 19), date(2024, 2, 16), etf, legs, picked)
    assert t.etf_contracts == t.original.etf_contracts == t.filtered.etf_contracts == 18
    assert all(q == 1.0 for q in t.original.positions.values()) and len(t.original.positions) == 30
    assert sorted(t.filtered.positions) == members[:10]
    assert t.short_premium == pytest.approx(18_000)
    assert t.full_basket_premium == pytest.approx(18_000)
    assert t.original.net_initial_premium == pytest.approx(0.0)
    assert t.selected_basket_premium == pytest.approx(11_500)
    assert t.unused_premium == t.net_initial_premium == pytest.approx(6_500)
    # filtering everything away still sells the same 18 calls
    none = svc.construct(date(2024, 1, 19), date(2024, 2, 16), etf, legs, Selection([], {}))
    assert none.etf_contracts == 18 and none.selected_basket_premium == 0 and none.unused_premium == pytest.approx(18_000)


def test_whole_contracts_round_the_screener_replication_and_fractional_keeps_it():
    etf = leg("ETF", 100.0, 2.0)
    legs = [leg("A", 50.0, 1.0, weight=0.75), leg("B", 50.0, 1.0, weight=0.25)]   # 1 ETF call -> 1.5 A, 0.5 B
    frac = DispersionPortfolioConstructionService(FRACTIONAL).construct(
        date(2024, 1, 19), date(2024, 2, 16), etf, legs, Selection(["A", "B"]))
    assert frac.etf_contracts == 2 and frac.original.positions == pytest.approx({"A": 3.0, "B": 1.0})
    whole = DispersionPortfolioConstructionService(WHOLE).construct(
        date(2024, 1, 19), date(2024, 2, 16), etf, [leg("A", 50.0, 1.0, 0.7), leg("B", 50.0, 1.0, 0.3)],
        Selection(["A", "B"]))
    # 1 ETF call -> 1.4 A / 0.6 B: N = ceil(1 / 0.6) = 2 -> raw 2.8 / 1.2 -> whole 3 / 1
    assert whole.etf_contracts == 2 and whole.raw_positions == pytest.approx({"A": 2.8, "B": 1.2})
    assert whole.original.positions == {"A": 3.0, "B": 1.0}


def test_settlement_includes_the_initial_premium_and_only_selected_long_calls():
    etf, legs, members = spec_example()
    svc = DispersionPortfolioConstructionService(WHOLE)
    t = svc.construct(date(2024, 1, 19), date(2024, 2, 16), etf, legs, Selection(members[:10]))
    prices = {s: 300.0 for s in members}
    prices["S00"], prices["S29"] = 330.0, 360.0           # S00 selected (+30), S29 not selected (+60)
    etf_at_expiry = 505.0
    a = svc.settle(t, t.original, etf_at_expiry, prices)
    b = svc.settle(t, t.filtered, etf_at_expiry, prices)
    short = -18 * 100 * 5.0
    assert a.payoff.short_etf == b.payoff.short_etf == pytest.approx(short)
    assert a.payoff.long_basket == pytest.approx(100 * (30 + 60))
    assert b.payoff.long_basket == pytest.approx(100 * 30)
    assert a.pnl == pytest.approx(short + 9_000 + 0.0)
    assert b.pnl == pytest.approx(short + 3_000 + 6_500)


def test_a_missing_quote_in_the_full_basket_refuses_the_trade():
    etf, legs, members = spec_example()
    legs[3] = Leg(legs[3].symbol, 300.0, 300.0, 100.0, None, None, legs[3].weight)
    with pytest.raises(ValueError):
        DispersionPortfolioConstructionService().construct(date(2024, 1, 19), date(2024, 2, 16), etf, legs,
                                                           Selection(members))


# ---------------------------------------------------------------- model filter
def test_model_filter_criteria_apply_together_and_only_to_scored_names():
    members = ["A", "B", "C", "D", "E"]
    scores = {"A": 0.9, "B": 0.5, "C": 0.1, "D": -0.2}               # E unscored
    s = select_constituents(members, scores, ModelFilterConfig(minimum_model_score=0.0))
    assert s.selected == ["A", "B", "C", "E"] and "D" in s.rejected and s.ranks == {"A": 1, "B": 2, "C": 3, "D": 4}
    s = select_constituents(members, scores, ModelFilterConfig(minimum_model_score=None, top_n=2, unscored="reject"),
                            {"E": "fewer than 10 closes"})
    assert s.selected == ["A", "B"] and "fewer than 10 closes" in s.rejected["E"]
    s = select_constituents(members, scores, ModelFilterConfig(minimum_model_score=None, bottom_n_excluded=1))
    assert s.selected == ["A", "B", "C", "E"]
    s = select_constituents(members, scores, ModelFilterConfig(minimum_model_score=None, percentile_threshold=50))
    assert s.selected == ["A", "B", "E"]
    with pytest.raises(ValueError):
        ModelFilterConfig(minimum_probability_up=0.6)                  # the STM model gives no probability


# ---------------------------------------------------------------- modelled options
def test_modelled_atm_call_uses_past_closes_only():
    idx = pd.bdate_range("2023-01-02", periods=200)
    rng = np.random.default_rng(1)
    s = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 200))), index=idx)
    opened, expiry = idx[150].date(), idx[150].date() + pd.Timedelta(days=28).to_pytimedelta()
    pricer = ModelledOptionPricer(OptionModelConfig(vol_window=63))
    leg_a = pricer.atm_call("X", s, opened, expiry)
    shocked = s.copy()
    shocked.iloc[151:] *= 3.0
    leg_b = pricer.atm_call("X", shocked, opened, expiry)
    assert leg_a == leg_b and leg_a.bid == leg_a.ask > 0 and abs(leg_a.strike - leg_a.spot) <= 0.5
    assert leg_a.implied_vol == pytest.approx(realised_vol(s, idx[150], 63))
    assert pricer.atm_call("X", s, idx[30].date(), expiry) is None                 # not enough history
    assert pricer.atm_call("X", s.drop(idx[150]), opened, expiry) is None           # no close that day


# ---------------------------------------------------------------- data source
class FakeClient:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, []

    def get(self, path, **params):
        self.calls.append((path, params))
        if self.error:
            raise self.error
        return self.payload


def test_eulerpool_closes_are_keyed_by_the_utc_day_and_errors_are_not_empty_data():
    from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolNotFound, EulerpoolUnavailable
    from src.infrastructure.repositories.eulerpool_repo.prices.eulerpool_price_history import EulerpoolPriceHistory
    t = [int(datetime(2000, 1, 3, 0, 0, tzinfo=timezone.utc).timestamp()),
         int(datetime(2026, 11, 13, 14, 30, tzinfo=timezone.utc).timestamp()),
         int(datetime(2026, 11, 14, 14, 30, tzinfo=timezone.utc).timestamp())]
    client = FakeClient({"t": t, "o": [1, 1, 1], "h": [1, 1, 1], "l": [1, 1, 1], "c": [48.58, 300.5, None],
                         "v": [1, 1, 1]})
    src = EulerpoolPriceHistory(client)
    out = src.daily_closes(src.underlying("JPM"), date(1999, 1, 1), date(2026, 12, 31))
    assert out == {date(2000, 1, 3): 48.58, date(2026, 11, 13): 300.5}
    path, params = client.calls[0]
    assert path == "charting/ohlcv/JPM" and params["resolution"] == "D" and params["from"] < params["to"]
    assert EulerpoolPriceHistory(FakeClient(error=EulerpoolNotFound("404"))).daily_closes(
        src.underlying("ZZZ"), date(2020, 1, 1), date(2020, 2, 1)) == {}
    with pytest.raises(MarketDataUnavailable):
        EulerpoolPriceHistory(FakeClient(error=EulerpoolUnavailable("down"))).daily_closes(
            src.underlying("JPM"), date(2020, 1, 1), date(2020, 2, 1))


# ---------------------------------------------------------------- STM scorer and trading cycle
def test_scores_never_use_closes_after_the_decision_date():
    closes, m = synthetic_world()
    as_of = closes.index[450]
    a = STMConstituentScorer(tiny_stm()).score(closes, ["A", "B", "C"], as_of)
    shocked = closes.copy()
    shocked.iloc[451:] *= 0.5
    b = STMConstituentScorer(tiny_stm()).score(shocked, ["A", "B", "C"], as_of)
    assert a.scores and a.scores == pytest.approx(b.scores)
    assert all(-1.0 <= v <= 1.0 for v in a.scores.values()) and a.retrained


def test_scorer_retrains_on_schedule_and_when_the_members_change():
    closes, _ = synthetic_world()
    scorer = STMConstituentScorer(tiny_stm(), retrain_every=3)
    first = scorer.score(closes, ["A", "B", "C"], closes.index[450])
    second = scorer.score(closes, ["A", "B", "C"], closes.index[470])
    assert first.retrained and not second.retrained and second.trained_at == first.trained_at
    third = scorer.score(closes, ["A", "B", "D"], closes.index[490])
    assert third.retrained and sorted(third.model_assets) == ["A", "B", "D"]
    short = scorer.score(closes, ["A", "B", "C"], closes.index[150])          # 150 closes < rolling window 200
    assert not short.scores and set(short.unscored) == {"A", "B", "C"}


def test_the_engine_cycle_settles_and_rolls_monthly_from_known_closes_only(tmp_path):
    logs = []
    results, cycle, closes = run_synthetic_demo(log=logs.append)
    m = cycle.membership
    settled = [x for x in cycle.months if x.complete]
    assert len(settled) >= 12
    for r in settled:
        t = r.trade
        assert r.opened < r.expiry and 20 <= (r.expiry - r.opened).days <= 60
        assert r.settled_on <= r.expiry and (r.expiry - r.settled_on).days <= 4
        assert set(t.original.positions) == set(m.members_at(r.opened))          # point-in-time full basket
        assert set(t.filtered.positions) <= set(t.original.positions)
        assert t.filtered.etf_contracts == t.original.etf_contracts                # same N
        assert t.short_premium == pytest.approx(t.etf_contracts * 100 * t.etf.bid)
        assert t.unused_premium == pytest.approx(t.full_basket_premium - t.selected_basket_premium
                                                 + t.original.net_initial_premium)
        assert r.filtered.payoff.short_etf == pytest.approx(r.original.payoff.short_etf)
    # consecutive trades roll: each opens at the close the previous one settled at
    assert all(b.opened == a.settled_on for a, b in zip(settled, settled[1:]))
    assert any("D" in r.trade.original.positions for r in settled) and any(
        "C" in r.trade.original.positions for r in settled)

    # every step sees only closes dated before its day; the trade of a roll day is opened at the next step
    for r in results:
        if r.session is not None:
            assert r.session <= known_through(r.time) < r.time.date()
    opens = [r for r in results if r.opened is not None]
    assert all(r.time.date() > r.opened.opened for r in opens)
    # orders: N short ETF calls, the TRADED strategy's (B) whole constituent contracts; zero at settlement
    first = opens[0]
    t = first.opened.trade
    etf_symbol = first.opened.option_symbols[m.etf]
    assert first.targets[etf_symbol] == -t.etf_contracts
    assert {s: q for s, q in first.targets.items() if s != etf_symbol} == {
        first.opened.option_symbols[u]: int(q) for u, q in t.filtered.positions.items()}
    closing = next(r for r in results if r.settled is first.opened)
    assert set(closing.targets) >= set(first.targets) and all(closing.targets[s] == 0 for s in first.targets)
    # the engine's price of a leg: modelled while open, intrinsic once settled
    assert cycle.option_price(etf_symbol) == pytest.approx(
        max(closes.loc[pd.Timestamp(first.opened.settled_on), m.etf] - t.etf.strike, 0.0))
    assert cycle.option_price("NOT A LEG") is None and not cycle.is_leg("NOT A LEG")
    assert etf_symbol == occ_symbol(m.etf, t.expiry, t.etf.strike)

    trades = trade_rows(cycle.months)
    assert {"short_premium", "full_basket_premium", "selected_basket_premium", "unused_premium",
            "net_initial_premium_filtered", "original_pnl", "filtered_pnl", "incremental_pnl", "n_selected",
            "pct_selected", "mean_model_score"} <= set(trades.columns)
    rows = constituent_rows(cycle.months)
    assert set(rows["selected"]) <= {True, False} and rows["reason"].notna().all()
    s = write_report(cycle.months, str(tmp_path), {"test": True})
    assert s["trades_settled"] == len(settled)
    assert set(s["original"]) >= {"sharpe_annualised", "max_drawdown", "win_rate", "median_pnl"}
    assert s["incremental"]["total_pnl"] == pytest.approx(s["model_filtered"]["total_pnl"] - s["original"]["total_pnl"])
    assert (tmp_path / "trades.csv").exists() and (tmp_path / "constituents.csv").exists()


def test_the_cycle_can_trade_the_original_strategy():
    results, cycle, _ = run_synthetic_demo(end=date(2020, 8, 31), traded="original")
    first = next(r for r in results if r.opened is not None)
    assert len(first.targets) == 1 + len(first.opened.trade.original.positions)


def test_the_algorithm_prices_the_cycle_legs_and_leaves_the_rest_to_the_engine():
    from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.base_project_algorithm import (
        Algorithm,
    )

    class Cycle:
        def is_leg(self, s):
            return s == "LEG"

        def option_price(self, s):
            return 4.2

    algo = Algorithm()
    algo.cycle = Cycle()
    assert algo._resolve_asset_price("LEG") == 4.2


def test_price_sources_prefer_the_first_cache_and_record_the_one_used(tmp_path):
    import json
    from src.application.managers.project_managers.etf_dispersion_stm_project.data.price_ingestion import (
        CacheFileReader,
        PreferredPrices,
    )
    from src.infrastructure.repositories.eulerpool_repo.prices.eulerpool_price_history import EulerpoolPriceHistory
    underlying = EulerpoolPriceHistory.underlying
    for source, symbol, close in (("ibkr", "A", 10.0), ("eulerpool", "A", 99.0), ("eulerpool", "B", 20.0)):
        (tmp_path / source).mkdir(exist_ok=True)
        (tmp_path / source / f"{symbol}.json").write_text(json.dumps(
            {"symbol": symbol, "start": "2020-01-01", "fetched_for": "2020-01-31", "closes": {"2020-01-02": close}}))
    prices = PreferredPrices([(n, CacheFileReader(str(tmp_path / n))) for n in ("ibkr", "eulerpool")])
    window = (date(2019, 1, 1), date(2030, 1, 1))          # a cache file is read whatever window it was fetched for
    assert prices.daily_closes(underlying("A"), *window) == {date(2020, 1, 2): 10.0}
    assert prices.daily_closes(underlying("B"), *window) == {date(2020, 1, 2): 20.0}
    assert prices.daily_closes(underlying("C"), *window) == {}
    assert prices.served == {"A": "ibkr", "B": "eulerpool", "C": "none"}


def test_pnl_stats():
    s = pnl_stats([100.0, -50.0, 30.0, -80.0])
    assert s["total_pnl"] == pytest.approx(0.0) and s["max_drawdown"] == pytest.approx(-100.0)
    assert s["win_rate"] == pytest.approx(0.5) and s["median_pnl"] == pytest.approx(-10.0)


def test_status_page_shows_the_run_progress_read_only(tmp_path):
    from src.application.services.dispersion.dispersion_progress import RunStatus, read_status
    from src.interfaces.flask.dispersion_stm_app import create_app
    client = create_app(str(tmp_path)).test_client()
    assert b"No run yet" in client.get("/dispersion-stm/").data
    run = tmp_path / "run1"
    run.mkdir()
    pd.DataFrame([{"opened": "2024-01-19", "expiry": "2024-02-16", "original_pnl": -1200.0,
                   "filtered_pnl": 800.0, "incremental_pnl": 2000.0}]).to_csv(run / "trades.csv", index=False)
    st = RunStatus(str(tmp_path), "backtest")
    st.update(run_folder=str(run), months_done=3, months_total=10, settled=1, cumulative_pnl_original=-1200.0,
              cumulative_pnl_filtered=800.0, last_month="2024-01-19")
    st.log("[DISP-STM] 2024-01-19 -> 2024-02-16: N=18")
    page = client.get("/dispersion-stm/").data.decode()
    assert "3 / 10 months" in page and "2,000" in page and "N=18" in page and "2024-02-16" in page
    assert client.get("/dispersion-stm/status.json").get_json()["months_done"] == 3 == read_status(str(tmp_path))["months_done"]
    assert client.post("/dispersion-stm/").status_code == 405
