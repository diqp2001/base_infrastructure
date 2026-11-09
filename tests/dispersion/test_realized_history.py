"""Dispersion screener: the 6-month realized payoff history (basket of ATM constituent calls - ATM ETF call, held to
the screen's expiry). Pure domain + the service and job on fake prices; no broker, no database."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from src.application.services.dispersion.realized_dispersion_service import RealizedDispersionService
from src.domain.entities.finance.dispersion.option_data import Underlying
from src.domain.entities.finance.dispersion.realized_payoff import (
    HoldingsSnapshot, Observation, expiry_for, observe, rolling_stats, shares_from_weights, third_fridays,
    weights_at,
)
from src.domain.entities.finance.dispersion.etf_holdings import ConstituentWeights
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort

CONFIG = DispersionScreenConfig()
START = date(2026, 6, 1)                    # a Monday; the screen's rule picks the 2026-07-17 monthly (46 DTE)
EXPIRY = date(2026, 7, 17)
LATER = date(2026, 11, 6)


def bdays(a, b):
    return [a + timedelta(days=i) for i in range((b - a).days + 1) if (a + timedelta(days=i)).weekday() < 5]


def path(start_price, moves=None, a=date(2026, 4, 1), b=LATER):
    """Business-day closes at start_price, then moves {day: price} from that day on."""
    out, price = {}, start_price
    for d in bdays(a, b):
        price = (moves or {}).get(d, price)
        out[d] = price
    return out


def snapshot(weights, etf=100.0, prices=None, as_of=START, pit=True):
    prices = prices or {s: 100.0 for s in weights}
    return HoldingsSnapshot(as_of, shares_from_weights(weights, etf, prices), point_in_time=pit)


def obs(etf_end, a_end, b_end, as_of=LATER):
    etf = path(100.0, {EXPIRY: etf_end})
    stocks = {"A": path(100.0, {EXPIRY: a_end}), "B": path(100.0, {EXPIRY: b_end})}
    return observe(START, etf, stocks, snapshot({"A": 0.5, "B": 0.5}), CONFIG, as_of)


def test_basket_payoff_above_the_etf_payoff_is_positive():                         # 1
    o = obs(100.0, 120.0, 80.0)                     # dispersion: A +20, B -20, the ETF flat
    assert o.expiry == EXPIRY and o.settled == EXPIRY
    assert o.etf_payoff == 0.0 and o.basket_payoff == pytest.approx(0.5 * 100 * 20)   # 0.5 A call x 100 x 20
    assert o.dispersion_payoff == pytest.approx(1000.0) and o.normalized == pytest.approx(1000.0 / (100 * 100))


def test_basket_payoff_below_the_etf_payoff_is_negative():                         # 2
    o = obs(110.0, 105.0, 105.0)                    # the ETF beat its constituents (tracking difference)
    assert o.etf_payoff == pytest.approx(1000.0) and o.basket_payoff == pytest.approx(500.0)
    assert o.dispersion_payoff == pytest.approx(-500.0) and o.payoff_return == pytest.approx(-0.5)


def test_equal_payoffs_give_zero():                                               # 3
    o = obs(110.0, 110.0, 110.0)                    # every name +10 %: the basket of calls = the ETF call
    assert o.dispersion_payoff == pytest.approx(0.0, abs=1e-9)
    stats = rolling_stats([o], LATER)
    assert stats.positive_rate == 0.0              # zero is not positive


def test_zero_etf_payoff_never_divides_by_zero():                                 # 4
    o = obs(95.0, 120.0, 70.0)
    assert o.etf_payoff == 0.0 and o.payoff_return is None and o.normalized is not None
    assert rolling_stats([o], LATER).return_mean is None


def made(initiated, settled, diff, etf_payoff=10.0, problem=None):
    return Observation(initiated, settled, settled, etf_strike=100.0, etf_settle=100.0, etf_payoff=etf_payoff,
                       basket_payoff=etf_payoff + diff, problem=problem)


def test_the_window_is_six_calendar_months():                                     # 5
    as_of = date(2026, 11, 6)
    old = made(date(2026, 5, 6), date(2026, 6, 19), 100.0)                   # exactly 6 months before: out
    inside = made(date(2026, 5, 7), date(2026, 6, 19), -40.0)
    stats = rolling_stats([old, inside], as_of)
    assert stats.window_start == date(2026, 5, 6) and stats.n == 1 and stats.cumulative == pytest.approx(-40.0)


def test_unexpired_trades_are_excluded():                                         # 6
    as_of = date(2026, 11, 6)
    done = made(date(2026, 8, 3), date(2026, 9, 18), 25.0)
    open_ = Observation(date(2026, 10, 30), date(2026, 12, 18), problem="not expired")
    settled_later = made(date(2026, 10, 1), date(2026, 11, 20), 999.0)        # computed later: not known at as_of
    stats = rolling_stats([done, open_, settled_later], as_of)
    assert stats.n == 1 and stats.n_open == 2 and stats.mean == pytest.approx(25.0)


def test_the_screens_dte_rule_is_used():                                         # 7
    assert expiry_for(date(2026, 11, 6), CONFIG) == date(2026, 12, 18)          # 42 DTE: what the screen picked
    assert (expiry_for(START, CONFIG) - START).days == 46
    longer = DispersionScreenConfig(target_dte=60, min_dte=45, max_dte=90)
    assert expiry_for(date(2026, 11, 6), longer) == date(2027, 1, 15)
    assert third_fridays(date(2026, 1, 1), date(2026, 3, 31)) == [date(2026, 1, 16), date(2026, 2, 20),
                                                                 date(2026, 3, 20)]


def test_weights_follow_the_share_counts_and_sum_to_one():                       # 8
    snap = snapshot({"A": 0.6, "B": 0.4}, etf=50.0, prices={"A": 30.0, "B": 10.0})
    assert snap.shares == pytest.approx({"A": 1.0, "B": 2.0})                     # shares per ETF share
    w = weights_at(snap, {"A": 60.0, "B": 10.0})                                # A doubled: 60 / (60 + 20)
    assert sum(w.values()) == pytest.approx(1.0) and w["A"] == pytest.approx(0.75)


def test_a_missing_close_makes_the_observation_incomplete_not_zero():            # 9
    etf, a, b = path(100.0), path(100.0), path(100.0)
    del b[EXPIRY]
    o = observe(START, etf, {"A": a, "B": b}, snapshot({"A": 0.5, "B": 0.5}), CONFIG, LATER)
    assert not o.complete and o.problem == f"no B close on {EXPIRY} (expiry)" and o.dispersion_payoff is None
    del a[START]
    assert observe(START, etf, {"A": a, "B": b}, snapshot({"A": 0.5, "B": 0.5}), CONFIG, LATER).problem == \
        f"no A close on {START}"
    stats = rolling_stats([o, made(date(2026, 8, 3), date(2026, 9, 18), 5.0)], LATER)
    assert stats.n == 1 and stats.n_incomplete == 1 and stats.mean == pytest.approx(5.0)


def test_no_price_after_the_date_is_used():                                      # 10
    etf = path(100.0)
    stocks = {"A": path(100.0, {EXPIRY: 130.0}), "B": path(100.0)}
    before = observe(START, etf, stocks, snapshot({"A": 0.5, "B": 0.5}), CONFIG, as_of=EXPIRY - timedelta(days=1))
    assert before.problem == "not expired" and before.basket_payoff is None     # the expiry close is in the future
    spiked = {k: dict(v) for k, v in stocks.items()}
    spiked["A"][LATER] = 1_000.0                                                # a later price changes nothing
    a1 = observe(START, etf, stocks, snapshot({"A": 0.5, "B": 0.5}), CONFIG, EXPIRY)
    a2 = observe(START, etf, spiked, snapshot({"A": 0.5, "B": 0.5}), CONFIG, EXPIRY)
    assert a1.dispersion_payoff == a2.dispersion_payoff == pytest.approx(0.5 * 100 * 30)


class FakePrices(PriceHistoryPort):
    def __init__(self, closes):
        self.closes, self.asked = closes, []

    def daily_closes(self, underlying, start, end):
        self.asked.append((underlying.symbol, start, end))
        return {d: c for d, c in self.closes.get(underlying.symbol, {}).items() if start <= d <= end}


def resolver(missing=()):
    return lambda symbols, day: {s: None if s in missing else Underlying(s, 1, "STK", "USD") for s in symbols}


def holdings(as_of, w):
    return ConstituentWeights("ETF", as_of, w, 1.0, [], "test")


def test_the_service_backcasts_todays_holdings_and_flags_it():
    as_of = LATER
    closes = {"ETF": path(100.0), "A": path(100.0, {date(2026, 9, 18): 120.0}), "B": path(100.0)}
    service = RealizedDispersionService(FakePrices(closes), resolver(), CONFIG)
    h = service.history("ETF", [holdings(date(2026, 11, 5), {"A": 0.5, "B": 0.5})], as_of)
    assert h.reasons == [] and "back-cast" in h.membership
    assert all(o.point_in_time == (o.initiated >= date(2026, 11, 5)) for o in h.observations)
    assert h.stats.n > 0 and h.stats.positive_rate > 0 and h.series and h.series[-1][1] == pytest.approx(h.stats.cumulative)
    gone = RealizedDispersionService(FakePrices(closes), resolver(missing=["B"]), CONFIG)
    assert gone.history("ETF", [holdings(date(2026, 11, 5), {"A": 0.5, "B": 0.5})], as_of).reasons == \
        ["B: not a US-listed share at the broker"]


def test_a_snapshot_is_used_from_its_own_date_on():
    closes = {"ETF": path(100.0), "A": path(100.0), "B": path(100.0), "C": path(100.0)}
    service = RealizedDispersionService(FakePrices(closes), resolver(), CONFIG)
    h = service.history("ETF", [holdings(date(2026, 6, 1), {"A": 0.5, "B": 0.5}),
                                holdings(date(2026, 8, 3), {"A": 0.5, "C": 0.5})], LATER)
    july = next(o for o in h.observations if o.initiated == date(2026, 7, 1))
    september = next(o for o in h.observations if o.initiated == date(2026, 9, 1))
    assert july.holdings_as_of == date(2026, 6, 1) and july.point_in_time
    assert september.holdings_as_of == date(2026, 8, 3)


def test_the_history_job_leaves_the_current_screen_untouched(tmp_path):         # 11
    from src.application.managers.project_managers.etf_dispersion_screener_project import realized_history
    from src.application.managers.project_managers.etf_dispersion_screener_project.project_manager import (
        write_candidates,
    )
    from src.application.services.dispersion.dispersion_screening_service import DispersionScreeningService
    from tests.dispersion.test_dispersion_screening_service import DAY, NOW, SPOTS, FakeMarket, weights
    day = tmp_path / DAY.isoformat()
    day.mkdir()
    (day / "universe.json").write_text(json.dumps({"etfs": [{
        "ticker": "ETF", "name": "Test ETF", "status": "eligible", "holdings_as_of": DAY.isoformat(),
        "weights": {"A": 0.5, "B": 0.5}, "equity_share": 1.0, "holdings_source": "test"}]}), encoding="utf-8")
    market = FakeMarket(SPOTS, {"ETF": (5.0, 5.1, 0.5), "A": (1.2, 1.25, 0.5), "B": (4.8, 5.0, 0.5)})
    screen = DispersionScreeningService(market, DispersionScreenConfig(), now=lambda: NOW)
    write_candidates(str(day), screen.screen([("ETF", "Test ETF", weights(A=0.5, B=0.5))], DAY))
    before = (day / "candidates.json").read_bytes()
    closes = {"ETF": path(100.0, b=DAY), "A": path(100.0, {date(2026, 8, 3): 115.0}, b=DAY), "B": path(100.0, b=DAY)}
    after_close = datetime(2026, 11, 5, 22, 0, tzinfo=timezone.utc)
    summary = realized_history.run(DAY.isoformat(), prices=FakePrices(closes), resolver=resolver(),
                                   config={"results_dir": str(tmp_path)}, now=lambda: after_close)
    assert (day / "candidates.json").read_bytes() == before                     # the screen's results unchanged
    stats = summary["etfs"]["ETF"]["stats"]
    assert summary["as_of"] == DAY.isoformat() and stats["n"] > 0 and stats["mean"] > 0
    saved = json.loads((day / "history" / "ETF.json").read_text(encoding="utf-8"))
    assert saved["series"] and saved["observations"][0]["initiated"] > "2026-05-05"
    assert realized_history.read_status(str(tmp_path), DAY.isoformat())["state"] == "done"
    before_close = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)            # 14:00 New York: today's bar partial
    assert realized_history.last_completed_session(DAY, before_close) == DAY - timedelta(days=1)


def test_the_pages_show_the_6m_columns_chart_and_start_one_job(tmp_path, monkeypatch):
    from flask import Flask
    from src.application.managers.project_managers.etf_dispersion_screener_project import realized_history
    from src.interfaces.flask.web.controllers import dispersion_controller
    test_the_history_job_leaves_the_current_screen_untouched(tmp_path)          # screen + history files
    from tests.dispersion.test_dispersion_screening_service import DAY
    day = DAY.isoformat()
    monkeypatch.setattr(dispersion_controller, "RESULTS_DIR", str(tmp_path))
    launched = []
    monkeypatch.setattr(dispersion_controller, "_launch", lambda log, module, *args: launched.append((module, args)))
    app = Flask(__name__, template_folder="../../src/interfaces/flask/web/templates")
    app.register_blueprint(dispersion_controller.dispersion_bp)
    client = app.test_client()
    page = client.get(f"/dispersion/?date={day}")
    stats = json.loads((tmp_path / day / "history" / "summary.json").read_text(encoding="utf-8"))["etfs"]["ETF"]["stats"]
    assert page.status_code == 200 and b"6M avg payoff diff" in page.data
    assert "{:+,.2f}".format(stats["mean"]).encode() in page.data
    detail = client.get(f"/dispersion/etf/ETF?date={day}")
    assert detail.status_code == 200 and b"data:image/png;base64," in detail.data and b"back-cast" in detail.data
    assert client.post("/dispersion/history/run", data={"date": day}).status_code == 302
    client.post("/dispersion/history/run", data={"date": day})                  # starting: no second job
    assert launched == [(dispersion_controller.HISTORY_MODULE, (day,))]
    assert realized_history.read_status(str(tmp_path), day)["state"] == "starting"
    # a maturities job is refused while the history job runs (one job at a time on the shared gateway)
    client.post("/dispersion/etf/ETF/maturities/run", data={"date": day})
    assert len(launched) == 1


# --- call-payoff replication (owner spec 2026-11-09): sum_i w_i max(r_i, 0) - max(r_ETF, 0) ---------------------

def three(etf_end=110.0, ends=None, as_of=LATER, weights=None):
    """The owner's example: ETF 100 -> 110; A 50 % 100 -> 120, B 30 % 100 -> 90, C 20 % 100 -> 115."""
    ends = ends or {"A": 120.0, "B": 90.0, "C": 115.0}
    etf = path(100.0, {EXPIRY: etf_end})
    stocks = {s: path(100.0, {EXPIRY: e}) for s, e in ends.items()}
    return observe(START, etf, stocks, snapshot(weights or {"A": 0.5, "B": 0.3, "C": 0.2}), CONFIG, as_of)


def test_owner_example_gives_exactly_plus_three_percent():                       # 15 (5, 6, 8)
    o = three()
    assert o.etf_call_return == pytest.approx(0.10)
    assert o.basket_call_return == pytest.approx(0.5 * 0.20 + 0.3 * 0.0 + 0.2 * 0.15)    # 13 %
    assert o.replication_difference == pytest.approx(0.03)                      # 13 % - 10 %, not 10 % - 13 %


def test_etf_call_payoff_is_the_positive_part_of_its_return():                   # 1, 2
    assert three(etf_end=110.0).etf_call_return == pytest.approx(0.10)
    assert three(etf_end=95.0).etf_call_return == 0.0
    assert three(etf_end=80.0).etf_call_return == 0.0


def test_constituent_call_payoff_is_the_positive_part_of_its_return():            # 3, 4
    up = three(ends={"A": 110.0, "B": 100.0, "C": 100.0}, weights={"A": 1.0 - 2e-9, "B": 1e-9, "C": 1e-9})
    assert up.basket_call_return == pytest.approx(0.10)
    down = three(ends={"A": 90.0, "B": 100.0, "C": 100.0}, weights={"A": 1.0 - 2e-9, "B": 1e-9, "C": 1e-9})
    assert down.basket_call_return == 0.0


def test_it_is_a_basket_of_calls_not_a_call_on_the_basket():                     # 7
    from src.domain.entities.finance.dispersion.realized_payoff import basket_call_payoff
    w, start, end = {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, {"A": 120.0, "B": 80.0}
    call_on_basket = max(sum(w[s] * (end[s] - start[s]) / start[s] for s in w), 0.0)
    assert call_on_basket == 0.0 and basket_call_payoff(w, start, end) == pytest.approx(0.10)
    o = three()
    assert o.basket_call_return != pytest.approx(max(0.5 * 0.2 + 0.3 * -0.1 + 0.2 * 0.15, 0.0))   # 10 %, not 13 %


def test_it_equals_the_normalized_dollar_payoff_of_the_screens_trade():
    for o in (three(), three(etf_end=90.0), obs(100.0, 120.0, 80.0), obs(110.0, 105.0, 105.0)):
        assert o.replication_difference == pytest.approx(o.normalized)


def test_replication_rolling_stats_window_and_completion():                       # 9, 10, 13
    as_of = date(2026, 11, 6)
    old = made(date(2026, 5, 6), date(2026, 6, 19), 100.0)                       # exactly 6 months before: out
    old.etf_return, old.basket_call_return = 0.0, 0.50
    inside = made(date(2026, 5, 7), date(2026, 6, 19), -40.0)
    inside.etf_return, inside.basket_call_return = 0.10, 0.06                    # -4 %
    second = made(date(2026, 8, 3), date(2026, 9, 18), 5.0)
    second.etf_return, second.basket_call_return = -0.05, 0.02                   # +2 %
    settled_later = made(date(2026, 10, 1), date(2026, 11, 20), 999.0)          # final price not known at as_of
    settled_later.etf_return, settled_later.basket_call_return = 0.0, 0.9
    open_ = Observation(date(2026, 10, 30), date(2026, 12, 18), problem="not expired")
    s = rolling_stats([old, inside, second, settled_later, open_], as_of)
    assert s.window_start == date(2026, 5, 6) and s.n == 2 and s.n_open == 2
    assert s.replication_mean == pytest.approx(-0.01) and s.replication_cumulative == pytest.approx(-0.02)
    assert s.replication_median == pytest.approx(-0.01)
    assert s.etf_call_mean == pytest.approx(0.05) and s.basket_call_mean == pytest.approx(0.04)
    assert s.replication_positive_rate == 0.5 and s.replication_negative_rate == 0.5


def test_no_later_price_changes_the_replication():                                # 13
    before = three(as_of=EXPIRY - timedelta(days=1))
    assert before.problem == "not expired" and before.replication_difference is None
    etf = path(100.0, {EXPIRY: 110.0})
    stocks = {s: path(100.0, {EXPIRY: e}) for s, e in {"A": 120.0, "B": 90.0, "C": 115.0}.items()}
    spiked = {k: dict(v) for k, v in stocks.items()}
    spiked["B"][LATER] = 500.0
    snap = snapshot({"A": 0.5, "B": 0.3, "C": 0.2})
    assert observe(START, etf, spiked, snap, CONFIG, EXPIRY).replication_difference == pytest.approx(0.03)


def test_historical_weights_at_the_observation_date_are_used():                   # 11
    closes = {"ETF": path(100.0, {EXPIRY: 100.0}), "A": path(100.0, {EXPIRY: 120.0}), "B": path(100.0)}
    service = RealizedDispersionService(FakePrices(closes), resolver(), CONFIG)
    h = service.history("ETF", [holdings(date(2026, 4, 1), {"A": 0.8, "B": 0.2}),     # in force on START
                                holdings(date(2026, 11, 5), {"A": 0.2, "B": 0.8})], LATER)   # today's
    o = next(o for o in h.observations if o.initiated == START)
    assert o.holdings_as_of == date(2026, 4, 1) and o.point_in_time
    assert o.basket_call_return == pytest.approx(0.8 * 0.20)                    # not today's 0.2 x 20 %
    assert h.replication_series and h.replication_series[0][3] is not None


def test_missing_constituent_data_is_excluded_not_zero():                         # 12
    etf, a, b = path(100.0, {EXPIRY: 110.0}), path(100.0, {EXPIRY: 120.0}), path(100.0)
    del b[EXPIRY]
    o = observe(START, etf, {"A": a, "B": b}, snapshot({"A": 0.5, "B": 0.5}), CONFIG, LATER)
    assert not o.complete and o.basket_call_return is None and o.replication_difference is None
    s = rolling_stats([o], LATER)
    assert s.n == 0 and s.n_incomplete == 1 and s.replication_mean is None


def test_the_job_and_pages_carry_the_replication_and_leave_the_screen_untouched(tmp_path, monkeypatch):   # 14
    from flask import Flask
    from src.interfaces.flask.web.controllers import dispersion_controller
    from tests.dispersion.test_dispersion_screening_service import DAY
    test_the_history_job_leaves_the_current_screen_untouched(tmp_path)          # asserts candidates.json unchanged
    day = DAY.isoformat()
    saved = json.loads((tmp_path / day / "history" / "ETF.json").read_text(encoding="utf-8"))
    assert saved["stats"]["replication_mean"] is not None and saved["replication_series"]
    done = [o for o in saved["observations"] if o["replication_difference"] is not None]
    assert done and all(o["etf_call_return"] is not None and o["basket_call_return"] is not None for o in done)
    monkeypatch.setattr(dispersion_controller, "RESULTS_DIR", str(tmp_path))
    app = Flask(__name__, template_folder="../../src/interfaces/flask/web/templates")
    app.register_blueprint(dispersion_controller.dispersion_bp)
    client = app.test_client()
    page = client.get(f"/dispersion/?date={day}")
    assert b"6M Avg Replication Diff." in page.data and b"6M avg payoff diff" in page.data
    assert ("%+.2f%%" % (saved["stats"]["replication_mean"] * 100)).encode() in page.data
    detail = client.get(f"/dispersion/etf/ETF?date={day}")
    assert b"call-payoff replication" in detail.data and detail.data.count(b"data:image/png;base64,") == 2
