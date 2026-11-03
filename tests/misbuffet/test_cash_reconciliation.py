"""
P.04.04 / P.06.13 — broker cash vs book cash, financing booked once a day (in-memory SQLite, fake read-only IBKR
account values; no connection, no orders).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.application.services.misbuffet.algorithm.cash_reconciler import CashReconciler
from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger
from src.application.services.misbuffet.algorithm.position_reconciler import BrokerSnapshot, PositionReconciler
from src.application.services.misbuffet.algorithm.startup_recovery import StartupRecovery
from src.domain.entities.finance.order.cash_snapshot import CashSnapshot
from src.domain.entities.finance.order.discrepancy import DiscrepancyKind
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

DAY1 = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
ACCOUNT = "DU1"


class FakeIB:
    """Account values (reqAccountSummary) + the empty broker lists a clean recovery reads."""

    def __init__(self, cash=1_000_000.0):
        self.cash, self.currency, self.values_complete = cash, "USD", True
        self.account_values_snapshot = {}
        self.order_listeners, self.connection_listeners, self.open_orders_snapshot = [], [], []
        self.positions = {}

    def is_connected(self):
        return True

    def request_account_values_snapshot(self, timeout=10.0, ledger=None):
        assert ledger == "USD"                          # the books' currency ledger, not the base-currency total
        values = {"TotalCashValue": ("992805.13", "CAD")}  # base currency CAD, like the paper account: ignored
        if self.currency is not None:
            values["$LEDGER-CashBalance"] = (str(self.cash), self.currency)
        self.account_values_snapshot = {ACCOUNT: values}
        return self.values_complete

    def request_open_orders_snapshot(self, timeout=10.0):
        return True

    def request_executions_snapshot(self, timeout=10.0):
        return True


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def env():
    book = SqlitePortfolio(cash=25_000.0, shares=("JPM",))
    ib, clock, recorded = FakeIB(), Clock(DAY1), []
    cash = CashReconciler(ib, ACCOUNT, book.factory.cash_snapshot_local_repo, book.tm,
                          portfolio_id=lambda: book.portfolio.id, threshold=250.0, clock=clock)
    env = SimpleNamespace(book=book, ib=ib, clock=clock, cash=cash, recorded=recorded,
                          snapshots=book.factory.cash_snapshot_local_repo)
    env.check = lambda: cash.check(lambda kind, key, detail, blocking: recorded.append((kind, key, blocking)))
    yield env
    book.close()


def next_day(env, days=1):
    env.clock.t = env.clock.t + timedelta(days=days)


def test_the_first_snapshot_is_a_baseline_and_a_day_is_compared_once(env):
    first = env.check()
    assert first.status == "baseline" and first.snapshot.is_baseline
    assert (first.snapshot.broker_cash, first.snapshot.book_cash) == (1_000_000.0, 25_000.0)
    env.ib.cash += 500.0                                                     # later the same day: not compared again
    again = env.check()
    assert again.status == "skipped" and len(env.snapshots.get_recent(ACCOUNT)) == 1
    assert env.book.cash() == 25_000.0


def test_fills_and_commissions_on_both_sides_match(env):
    env.check()
    next_day(env)
    env.book.tm.book_commission(1.25, env.book.portfolio.id, env.clock.t.replace(tzinfo=None))   # books -1.25
    env.ib.cash -= 1.25                                                                          # broker -1.25
    result = env.check()
    assert result.status == "matched" and result.snapshot.difference == 0.0 and result.snapshot.booked == 0.0
    assert env.recorded == []


@pytest.mark.parametrize("financing", [12.34, -3.21])                       # interest credited / borrow fee charged
def test_the_difference_is_booked_once_as_financing(env, financing):
    env.check()
    next_day(env)
    env.book.tm.book_commission(1.0, env.book.portfolio.id, env.clock.t.replace(tzinfo=None))
    env.ib.cash += -1.0 + financing
    result = env.check()
    assert result.status == "booked" and result.snapshot.booked == pytest.approx(financing)
    assert env.book.cash() == pytest.approx(25_000.0 - 1.0 + financing)
    assert result.snapshot.book_cash == pytest.approx(env.book.cash())
    fin = [t for t in env.book.transactions() if t.transaction_id.startswith("FIN_TXN_")]
    assert [t.transaction_id for t in fin] == [result.snapshot.transaction_ref]
    orders = [o for o in env.book.orders() if o.id == fin[0].order_id]
    assert orders[0].external_order_id.startswith("FIN_") and orders[0].side.value == ("BUY" if financing > 0 else "SELL")
    assert float(orders[0].quantity) == pytest.approx(abs(financing))
    next_day(env)                                                            # nothing new: the books now agree
    assert env.check().status == "matched" and env.book.cash() == pytest.approx(25_000.0 - 1.0 + financing)


def test_a_difference_above_the_threshold_is_a_cash_drift_not_booked(env):
    env.check()
    next_day(env)
    env.ib.cash += 10_000.0                                                  # a deposit
    result = env.check()
    assert result.status == "drift" and result.snapshot.unexplained == 10_000.0 and result.snapshot.booked == 0.0
    assert env.recorded == [(DiscrepancyKind.CASH_DRIFT, f"{ACCOUNT} 2026-11-03", False)]
    assert env.book.cash() == 25_000.0
    next_day(env)                                                            # compared from the drift snapshot on
    assert env.check().status == "matched"


@pytest.mark.parametrize("break_it,word", [
    (lambda ib: setattr(ib, "values_complete", False), "incomplete"),
    (lambda ib: setattr(ib, "currency", "EUR"), "EUR"),
    (lambda ib: setattr(ib, "currency", None), "no USD cash balance"),
])
def test_unreadable_or_foreign_currency_broker_cash_stores_nothing(env, break_it, word):
    break_it(env.ib)
    result = env.check()
    assert result.status == "failed" and word in result.message and env.snapshots.get_latest(ACCOUNT) is None


def test_a_failed_booking_stores_neither_the_entry_nor_the_snapshot(env):
    env.check()
    next_day(env)
    env.ib.cash += 20.0
    with patch.object(env.book.tm, "book_cash_adjustment", return_value=None):
        result = env.check()
    assert result.status == "failed" and "rolled back" in result.message
    assert len(env.snapshots.get_recent(ACCOUNT)) == 1 and env.book.cash() == 25_000.0
    assert env.check().status == "booked"                                    # retried by the next recovery


def test_a_new_strategy_portfolio_starts_a_new_baseline(env):
    env.snapshots.add(CashSnapshot(account=ACCOUNT, portfolio_id=999, taken_at=datetime(2026, 11, 1, 14, 0),
                                   broker_cash=5.0, book_cash=5.0))
    assert env.check().status == "baseline"


def test_the_recovery_compares_cash_only_after_a_successful_run(env):
    ledger = OrderLedger(env.book.factory, clock=env.clock)
    ledger.attach(env.ib)
    reconciler = PositionReconciler(
        strategy_qty=env.book.qty, managed_tickers=lambda: {"JPM"},
        snapshot_provider=lambda: BrokerSnapshot(positions=dict(env.ib.positions), open_orders=[],
                                                 taken_at=datetime.now(timezone.utc)))
    recovery = StartupRecovery(env.ib, ledger, env.book.factory.trading_discrepancy_local_repo,
                               reconciler=reconciler, clock=env.clock, cash_reconciler=env.cash)
    env.ib.positions = {"JPM": 5}                                            # the books hold none: blocked
    report = recovery.run()
    assert not report.ok and report.cash is None and env.snapshots.get_latest(ACCOUNT) is None
    env.ib.positions = {}
    report = recovery.run()
    assert report.ok and report.cash.startswith("cash baseline") and "cash baseline" in report.summary()
    next_day(env)
    env.ib.cash += 40.0
    report = recovery.run()
    assert report.ok and report.cash.startswith("cash booked")
    env.ib.cash += 1_000.0
    next_day(env)
    report = recovery.run()                                                  # a drift never blocks trading
    assert report.ok and [d.kind for d in report.new_discrepancies] == [DiscrepancyKind.CASH_DRIFT]
    assert recovery.trading_allowed()


def test_a_drift_booked_by_hand_moves_the_baseline_so_it_is_not_booked_back(env):
    env.check()
    next_day(env)
    env.ib.cash += 600.0                                                     # a dividend posting above the threshold
    assert env.check().status == "drift"
    with pytest.raises(ValueError):
        env.cash.book_by_hand(600.0, " ")
    snap = env.cash.book_by_hand(600.0, "JPM dividend 2026-11-03, statement checked")
    assert snap.is_baseline and snap.booked == 600.0 and snap.transaction_ref.startswith("FIN_TXN_")
    assert env.book.cash() == pytest.approx(25_600.0) and snap.book_cash == pytest.approx(25_600.0)
    next_day(env)
    assert env.check().status == "matched" and env.book.cash() == pytest.approx(25_600.0)


def test_ops_cash_book_books_and_reports(env, monkeypatch):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config, ops
    monkeypatch.setitem(config.LIVE, "account", ACCOUNT)
    lines = []
    assert ops.main(["cash-book", "-12.5", "fee"], factory=env.book.factory, out=lines.append) == 1
    assert "no cash snapshot" in lines[-1]                                   # nothing to adjust before a baseline
    env.check()
    assert ops.main(["cash-book", "-12.5", "fee"], factory=env.book.factory, out=lines.append) == 0
    assert env.book.cash() == pytest.approx(25_000.0 - 12.5) and "-12.50 USD booked" in lines[-1]
    ops.main(["status"], factory=env.book.factory, out=lines.append)
    assert any(line.strip().startswith("cash ") and "by hand: fee" in line for line in lines)
