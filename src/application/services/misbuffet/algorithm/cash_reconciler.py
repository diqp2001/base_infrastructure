"""
CashReconciler — the broker's cash vs the strategy's book cash, once per day, by the start-up recovery (P.04.04 / P.06.13).

The account trades only this strategy (owner, 2026-11-02). Between two snapshots both cash amounts move by the same
fills and commissions (booked from the broker's executions); the rest is financing — short-credit interest, borrow
fees — dividends and fees, or a deposit / withdrawal / a trade the books missed:

    difference = broker cash change (IBKR TotalCashValue) - book cash change, since the previous snapshot

    first snapshot (or a new strategy portfolio)   baseline, nothing compared
    |difference| < 0.01                            matched
    |difference| <= threshold                      booked on the book cash as ONE cash-only FINANCING entry
                                                   (order / transaction refs 'FIN_...'), atomically with the snapshot
    |difference| >  threshold                      not booked: CASH_DRIFT discrepancy (not blocking) for the owner;
                                                   the next comparison starts from this snapshot

Run only after a successful recovery (complete lists, positions matched: the books are trustworthy) and at most once
per UTC day (the first recovery of the day: the session start). All broker requests are read-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from src.domain.entities.finance.order.cash_snapshot import CashSnapshot, cash_difference
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CashCheck:
    status: str                                    # baseline / matched / booked / drift / skipped / failed
    snapshot: Optional[CashSnapshot] = None
    discrepancy: Optional[Discrepancy] = None
    message: str = ""

    def summary(self) -> str:
        return f"cash {self.status}" + (f": {self.message}" if self.message else "")


class CashReconciler:

    def __init__(self, client, account: str, snapshots, trade_manager, portfolio_id: Callable[[], Optional[int]],
                 threshold: float = 250.0, currency: str = "USD", timeout: float = 10.0,
                 clock: Callable[[], datetime] = _utcnow, logger=None):
        """
        Args:
            client:        IBTWSClient-like: request_account_values_snapshot / account_values_snapshot
            snapshots:     CashSnapshotPort (RepositoryFactory.cash_snapshot_local_repo)
            trade_manager: TradeManager (cash_balance, book_cash_adjustment, _book_atomically)
            portfolio_id:  the strategy's main portfolio id (its CurrencyPortfolio holds the book cash)
            threshold:     largest difference booked automatically (base currency)
        """
        if not account:
            raise ValueError("CashReconciler needs the account id")
        self.client = client
        self.account = account
        self.snapshots = snapshots
        self.trade_manager = trade_manager
        self.portfolio_id = portfolio_id
        self.threshold = float(threshold)
        self.currency = currency
        self.timeout = timeout
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.last_check: Optional[CashCheck] = None

    def check(self, record: Callable[[DiscrepancyKind, str, str, bool], Optional[Discrepancy]]) -> CashCheck:
        """Compare and book; `record(kind, key, detail, blocking)` stores a discrepancy (StartupRecovery._record)."""
        try:
            result = self._check(record)
        except Exception as e:
            result = CashCheck("failed", message=repr(e))
        (self.logger.error if result.status in ("failed", "drift") else self.logger.info)(result.summary())
        self.last_check = result
        return result

    def _check(self, record) -> CashCheck:
        now = self._now()
        latest = self.snapshots.get_latest(self.account)
        if latest is not None and latest.taken_at.date() == now.date():
            return CashCheck("skipped", latest, message=f"already compared today ({latest.taken_at:%H:%M} UTC)")
        portfolio_id = self.portfolio_id()
        if portfolio_id is None:
            return CashCheck("failed", message="no strategy portfolio registered")
        if not self.client.request_account_values_snapshot(timeout=self.timeout):
            return CashCheck("failed", message="account values incomplete (no accountSummaryEnd)")
        raw = (self.client.account_values_snapshot.get(self.account) or {}).get("TotalCashValue")
        if raw is None:
            return CashCheck("failed", message=f"no TotalCashValue for {self.account}")
        if raw[1] != self.currency:
            return CashCheck("failed", message=f"TotalCashValue is in {raw[1]}, the books are in {self.currency}")
        broker_cash = float(raw[0])
        book_cash = self.trade_manager.cash_balance(portfolio_id)
        snap = CashSnapshot(account=self.account, portfolio_id=portfolio_id, taken_at=now, broker_cash=broker_cash,
                            book_cash=book_cash, currency=self.currency)

        if latest is None or latest.portfolio_id != portfolio_id:
            snap.note = ("baseline: first cash snapshot of the account" if latest is None
                         else f"baseline: strategy portfolio {latest.portfolio_id} -> {portfolio_id}")
            return CashCheck("baseline", self.snapshots.add(snap), message=snap.note)

        snap.broker_change, snap.book_change, diff = cash_difference(latest, broker_cash, book_cash)
        since = f"since {latest.taken_at:%Y-%m-%d %H:%M} UTC"
        if abs(diff) < 0.01:
            snap.note = f"matched {since}"
            return CashCheck("matched", self.snapshots.add(snap), message=snap.note)

        if abs(diff) > self.threshold:
            snap.unexplained = diff
            snap.note = (f"not booked: broker cash {snap.broker_change:+,.2f}, books {snap.book_change:+,.2f} {since}; "
                         f"difference {diff:+,.2f} {self.currency} above {self.threshold:,.2f}")
            stored = self.snapshots.add(snap)
            d = record(DiscrepancyKind.CASH_DRIFT, f"{self.account} {now:%Y-%m-%d}",
                       f"{self.account}: {snap.note} (deposit / withdrawal, a trade the books missed, or a large "
                       f"financing / dividend posting: book it by hand or explain it, then resolve)", False)
            return CashCheck("drift", stored, d, message=snap.note)

        def book() -> bool:
            ref = self.trade_manager.book_cash_adjustment(diff, portfolio_id, now)
            if ref is None:
                return False
            snap.booked, snap.transaction_ref = diff, ref
            snap.book_cash = round(book_cash + diff, 2)
            snap.note = (f"FINANCING {diff:+,.2f} {self.currency} booked (interest, borrow fees, dividends, fees "
                         f"{since})")
            self.snapshots.add(snap)
            return True

        if not self.trade_manager._book_atomically(book):
            return CashCheck("failed", message=f"FINANCING {diff:+,.2f} not booked: rolled back")
        return CashCheck("booked", snap, message=snap.note)

    def book_by_hand(self, amount: float, reason: str) -> CashSnapshot:
        """The owner books a difference the daily check left unbooked (CASH_DRIFT: a large dividend or interest
        posting ...): a cash-only entry, plus a baseline snapshot moved by the same amount — without it the next
        comparison would book the entry back. Database only; run while no session is running."""
        if not reason or not reason.strip():
            raise ValueError("say why the cash is booked by hand")
        amount = round(float(amount), 2)
        if amount == 0:
            raise ValueError("nothing to book")
        latest = self.snapshots.get_latest(self.account)
        if latest is None:
            raise LookupError(f"no cash snapshot for {self.account} yet: the first session start takes the baseline")
        portfolio_id = self.portfolio_id() or latest.portfolio_id
        if portfolio_id != latest.portfolio_id:
            raise LookupError(f"strategy portfolio {portfolio_id} is not the snapshot's ({latest.portfolio_id})")
        now = self._now()
        snap = CashSnapshot(account=self.account, portfolio_id=portfolio_id, taken_at=now,
                            broker_cash=latest.broker_cash, book_cash=round(latest.book_cash + amount, 2),
                            currency=latest.currency, booked=amount,
                            note=f"baseline after booking {amount:+,.2f} {latest.currency} by hand: {reason.strip()}")

        def book() -> bool:
            snap.transaction_ref = self.trade_manager.book_cash_adjustment(amount, portfolio_id, now)
            if snap.transaction_ref is None:
                return False
            self.snapshots.add(snap)
            return True

        if not self.trade_manager._book_atomically(book):
            raise RuntimeError(f"{amount:+,.2f} not booked: rolled back")
        return snap

    def _now(self) -> datetime:
        now = self.clock()
        return now.astimezone(timezone.utc).replace(tzinfo=None) if now.tzinfo is not None else now
