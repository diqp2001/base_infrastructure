"""P.08.13: option expiry, exercise and assignment read from broker positions and booked so the book matches the
broker (domain detection, booking legs, StartupRecovery step 4b). No broker, no database."""

from datetime import date, datetime
from types import SimpleNamespace

from src.application.services.misbuffet.algorithm.option_lifecycle_booker import OptionLifecycleBooker
from src.application.services.misbuffet.algorithm.startup_recovery import RecoveryReport, StartupRecovery
from src.domain.entities.finance.option_lifecycle import (
    ASSIGNED, EXERCISED, EXPIRED, OptionContract, book_after, lifecycle_events,
)

CALL = "SPY   261120C00450000"          # SPY call, strike 450, expiry 2026-11-20
PUT = "SPY   261120P00400000"
TODAY = date(2026, 11, 23)


def test_occ_symbols_are_parsed_and_stocks_are_not():
    c = OptionContract.parse(CALL)
    assert (c.underlying, c.expiry, c.right, c.strike) == ("SPY", date(2026, 11, 20), "C", 450.0)
    assert OptionContract.parse("SPY") is None and OptionContract.parse("") is None


def test_expiry_worthless():
    book, broker = {CALL: 2, "SPY": 10}, {"SPY": 10}
    events = lifecycle_events(book, broker, TODAY)
    assert [(e.kind, e.option_quantity, e.underlying_quantity) for e in events] == [(EXPIRED, 2, 0.0)]
    assert book_after(book, events) == broker


def test_itm_exercise_of_a_long_call():
    book, broker = {CALL: 2, "SPY": 10}, {"SPY": 210}                     # +2 x 100 shares at 450
    events = lifecycle_events(book, broker, TODAY)
    assert [(e.kind, e.underlying_quantity, e.price) for e in events] == [(EXERCISED, 200.0, 450.0)]
    assert book_after(book, events) == broker


def test_assignment_of_a_short_put_and_a_short_call():
    book, broker = {PUT: -1, CALL: -1}, {"SPY": 0}
    events = lifecycle_events(book, {"SPY": 100}, TODAY)                     # put assigned: +100 shares at 400
    assert {(e.option.right, e.kind, e.underlying_quantity) for e in events} == {("P", ASSIGNED, 100.0),
                                                                              ("C", EXPIRED, 0.0)}
    assert book_after(book, events) == {"SPY": 100}
    call_assigned = lifecycle_events({CALL: -1}, {"SPY": -100}, TODAY)
    assert (call_assigned[0].kind, call_assigned[0].underlying_quantity) == (ASSIGNED, -100.0)
    assert lifecycle_events(book, broker, TODAY)[0].kind == EXPIRED


def test_not_yet_expired_or_still_held_options_are_left_alone():
    assert lifecycle_events({CALL: 2}, {}, date(2026, 11, 20)) == []        # expiry day itself: not yet
    assert lifecycle_events({CALL: 2}, {CALL.replace(" ", ""): 2}, TODAY) == []
    # an underlying move too small for the exercise: expired, the rest stays a mismatch for the operator
    assert lifecycle_events({CALL: 2}, {"SPY": 150}, TODAY)[0].kind == EXPIRED


class FakeTradeManager:
    def __init__(self, fail_on=None):
        self.booked, self.orders, self.fail_on = [], [], fail_on
        self.order_repo = SimpleNamespace(_create_or_get=self._order)

    def _order(self, **kw):
        self.orders.append(kw)
        return SimpleNamespace(id=len(self.orders))

    def _resolve_holding_id(self, symbol, portfolio_id, when):
        return 7

    def _resolve_account_id(self, when):
        return 1

    def book_execution(self, **kw):
        if kw["ticker"] == self.fail_on:
            return False
        self.booked.append((kw["ticker"], kw["signed_qty"], kw["price"]))
        return True

    def _book_atomically(self, book):
        before = list(self.booked)
        if book():
            return True
        self.booked = before                                                 # rolled back
        return False


def test_the_booker_closes_the_option_at_zero_and_moves_the_underlying_at_the_strike():
    tm = FakeTradeManager()
    booker = OptionLifecycleBooker(tm, portfolio_id=lambda: 3, cash_portfolio_id=lambda: 4)
    events = booker.apply({CALL: 2, "SPY": 10}, {"SPY": 210}, TODAY)
    assert [e.kind for e in events] == [EXERCISED]
    assert tm.booked == [(CALL, -2, 0.0), ("SPY", 200.0, 450.0)]
    assert tm.orders[0]["external_order_id"] == "ibkr:LIFECYCLE:exercised:SPY261120C00450000:2026-11-20:0"
    assert (tm.orders[1]["side"], tm.orders[1]["quantity"]) == ("BUY", 200.0)


def test_an_event_that_cannot_be_booked_is_rolled_back_alone():
    tm = FakeTradeManager(fail_on="SPY")
    booker = OptionLifecycleBooker(tm, portfolio_id=lambda: 3, cash_portfolio_id=lambda: 4)
    assert booker.apply({CALL: 2}, {"SPY": 200}, TODAY) == []
    assert tm.booked == []


def test_startup_recovery_books_the_lifecycle_before_reconciling_positions():
    book = {CALL: 2, "SPY": 10}
    reconciler = SimpleNamespace(
        snapshot_provider=lambda: SimpleNamespace(complete=True, positions={"SPY": 210}),
        strategy_qty=lambda t: book.get(t, 0), managed_tickers=lambda: list(book))
    booked = []
    lifecycle = SimpleNamespace(apply=lambda b, broker, today: booked.append((b, broker, today))
                                or lifecycle_events(b, broker, today))
    recovery = StartupRecovery(client=SimpleNamespace(), ledger=None, discrepancies=None, reconciler=reconciler,
                               clock=lambda: datetime(2026, 11, 23, 14, 20), option_lifecycle=lifecycle)
    report = RecoveryReport(ok=False, started_at=datetime(2026, 11, 23, 14, 20))
    recovery._book_option_lifecycle(report)
    assert booked == [(book, {"SPY": 210}, TODAY)]
    assert report.lifecycle == [f"{CALL} +2 exercised: SPY +200 @ 450"]
    assert "options: " in report.summary()
