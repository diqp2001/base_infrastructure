"""
Position reconciliation between the strategy's own portfolio (database) and the broker.

Why: in live trading the database view of the strategy can drift from the real account —
an order that was filled while the process was down, a partial fill, a manual trade, a crash
between "order sent" and "order recorded". Re-submitting orders from a stale view duplicates
them. ``set_holdings`` therefore only trades when the latest reconciliation is clean.

Rules (fail closed):
* every instrument the strategy manages (held in its portfolio, or targeted now) must have the
  same quantity in the database and at the broker — any difference blocks ALL trading;
* an instrument with an open (working) order at the broker, or an order this process sent that
  no later snapshot has confirmed done, is "pending": it is not traded again and not compared
  until that order is done — this prevents duplicate orders across restarts;
* a missing or stale broker snapshot blocks trading;
* positions at the broker that the strategy does not manage are reported but never traded.

The broker side is a ``snapshot_provider`` returning a ``BrokerSnapshot`` (IBKR implementation:
``IBKRSnapshotProvider``), so the reconciler is independent of the broker and unit-testable.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

# order states that are still working at the broker (IBKR orderStatus / OrderState.status)
WORKING_ORDER_STATES = {"apipending", "pendingsubmit", "pendingcancel", "presubmitted", "submitted",
                        "apicancelled_pending", "inactive_pending"}
DONE_ORDER_STATES = {"filled", "cancelled", "apicancelled", "inactive"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BrokerOrder:
    key: str                      # instrument key (see instrument_key)
    order_id: Optional[int]
    perm_id: Optional[int]
    side: Optional[str]
    quantity: Optional[float]
    remaining: Optional[float]
    status: str

    @property
    def working(self) -> bool:
        status = (self.status or "").lower()
        if status in DONE_ORDER_STATES:
            return False
        if self.remaining is not None and self.remaining <= 0 and status not in WORKING_ORDER_STATES:
            return False
        return True


@dataclass(frozen=True)
class BrokerSnapshot:
    positions: Dict[str, float]                   # instrument key -> signed quantity (all accounts / one account)
    open_orders: List[BrokerOrder]
    taken_at: datetime
    complete: bool = True                          # False when the broker did not confirm the end of the lists
    account: Optional[str] = None


@dataclass
class ReconciliationResult:
    ok: bool
    checked_at: datetime
    mismatches: List[Dict] = field(default_factory=list)     # {ticker, strategy_qty, broker_qty}
    pending_tickers: Set[str] = field(default_factory=set)   # managed tickers with working orders
    unmanaged_positions: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None

    def summary(self) -> str:
        if self.error:
            return f"reconciliation failed: {self.error}"
        parts = []
        if self.mismatches:
            parts.append("mismatches " + ", ".join(
                f"{m['ticker']} strategy={m['strategy_qty']} broker={m['broker_qty']}" for m in self.mismatches))
        if self.pending_tickers:
            parts.append("working orders on " + ", ".join(sorted(self.pending_tickers)))
        if self.unmanaged_positions:
            parts.append(f"{len(self.unmanaged_positions)} unmanaged broker position(s) ignored")
        return ("OK" if self.ok else "BLOCKED") + (": " + "; ".join(parts) if parts else "")


def instrument_key(symbol: Optional[str], local_symbol: Optional[str] = None, sec_type: Optional[str] = None) -> str:
    """Key used on both sides: share symbol for stocks, the full local symbol for derivatives.

    The strategy stores options under their OCC local symbol (e.g. ``"SPY   281215C00775000"``);
    IBKR reports ``contract.symbol == "SPY"`` for the option too, so derivatives must be matched on
    the local symbol to avoid mixing an option with its underlying.
    """
    sec = (sec_type or "").upper()
    if sec and sec not in ("STK", "ETF") and local_symbol:
        return " ".join(str(local_symbol).split())
    return " ".join(str(symbol or local_symbol or "").split())


def normalize_ticker(ticker: str) -> str:
    return " ".join(str(ticker).split())


class PositionReconciler:

    def __init__(self, strategy_qty: Callable[[str], float], managed_tickers: Callable[[], Iterable[str]],
                 snapshot_provider: Callable[[], BrokerSnapshot], max_age_seconds: float = 60.0,
                 tolerance: float = 0.0):
        """
        Args:
            strategy_qty:      ticker -> quantity the strategy's portfolio holds (database)
            managed_tickers:   tickers currently held by the strategy's portfolio
            snapshot_provider: returns a fresh BrokerSnapshot (positions + open orders)
            max_age_seconds:   a snapshot older than this is refreshed before trading
            tolerance:         allowed |strategy - broker| difference (0 = exact)
        """
        self.strategy_qty = strategy_qty
        self.managed_tickers = managed_tickers
        self.snapshot_provider = snapshot_provider
        self.max_age_seconds = max_age_seconds
        self.tolerance = tolerance
        self.last_result: Optional[ReconciliationResult] = None
        self._submitted: Dict[str, float] = {}       # ticker -> monotonic time, orders sent by this process
        self._lock = threading.Lock()

    def note_submitted(self, ticker: str) -> None:
        """Remember an order just sent: the ticker stays blocked until the next broker snapshot."""
        with self._lock:
            self._submitted[normalize_ticker(ticker)] = time.monotonic()

    def check(self, extra_tickers: Iterable[str] = ()) -> ReconciliationResult:
        """Fresh reconciliation of the managed tickers (+ the tickers about to be traded)."""
        now = _now()
        try:
            snapshot = self.snapshot_provider()
        except Exception as e:
            return self._store(ReconciliationResult(False, now, error=f"broker snapshot unavailable: {e}"))
        if snapshot is None:
            return self._store(ReconciliationResult(False, now, error="broker snapshot unavailable"))
        if not snapshot.complete:
            return self._store(ReconciliationResult(False, now, error="broker snapshot incomplete"))
        age = (now - snapshot.taken_at).total_seconds()
        if age > self.max_age_seconds:
            return self._store(ReconciliationResult(False, now, error=f"broker snapshot is {age:.0f}s old"))

        try:
            # normalized key -> ticker as the strategy stores it (OCC symbols keep their inner spaces)
            managed = {normalize_ticker(t): t for t in list(extra_tickers) + list(self.managed_tickers())}
        except Exception as e:
            return self._store(ReconciliationResult(False, now, error=f"strategy positions unavailable: {e}"))
        broker_positions: Dict[str, float] = {}
        for key, qty in snapshot.positions.items():
            k = normalize_ticker(key)
            broker_positions[k] = broker_positions.get(k, 0.0) + float(qty or 0)

        result = ReconciliationResult(True, now)
        working = {normalize_ticker(o.key) for o in snapshot.open_orders if o.working}
        result.pending_tickers = working & set(managed)
        with self._lock:
            # an order this process sent is pending until a snapshot taken after it shows no working order
            for ticker, sent in list(self._submitted.items()):
                sent_at = time.time() - (time.monotonic() - sent)
                if ticker not in working and snapshot.taken_at.timestamp() > sent_at:
                    del self._submitted[ticker]
                else:
                    result.pending_tickers.add(ticker)

        for key in sorted(managed):
            ticker = managed[key]
            try:
                ours = float(self.strategy_qty(ticker) or 0)
            except Exception as e:
                return self._store(ReconciliationResult(False, now, error=f"strategy quantity for {ticker}: {e}"))
            theirs = broker_positions.get(key, 0.0)
            # while an order is working the strategy's book legitimately leads the broker: the ticker
            # is not traded (pending) and is compared again once the order is done
            if abs(ours - theirs) > self.tolerance and key not in result.pending_tickers:
                result.mismatches.append({"ticker": ticker, "strategy_qty": ours, "broker_qty": theirs})
        result.unmanaged_positions = {k: q for k, q in broker_positions.items() if k not in managed and q}
        result.ok = not result.mismatches
        return self._store(result)

    def _store(self, result: ReconciliationResult) -> ReconciliationResult:
        self.last_result = result
        (logger.info if result.ok else logger.error)("Position reconciliation %s", result.summary())
        return result


class IBKRSnapshotProvider:
    """BrokerSnapshot from an IBTWSClient connection (reqPositions + reqAllOpenOrders)."""

    def __init__(self, ib_connection, account: Optional[str] = None, timeout: float = 10.0):
        self.ib = ib_connection
        self.account = account
        self.timeout = timeout

    def __call__(self) -> BrokerSnapshot:
        if not self.ib or not self.ib.is_connected():
            raise ConnectionError("IBKR not connected")
        positions_ok = self.ib.request_positions_snapshot(timeout=self.timeout)
        orders_ok = self.ib.request_open_orders_snapshot(timeout=self.timeout)
        if self.account is None:
            accounts = {p.get("account") for p in self.ib.positions_snapshot if p.get("account")}
            if len(accounts) > 1:
                # summing several accounts would compare the strategy with the wrong book
                raise ValueError(f"several accounts visible ({sorted(accounts)}): pass account=")
        positions: Dict[str, float] = {}
        for p in self.ib.positions_snapshot:
            if self.account and p.get("account") != self.account:
                continue
            key = instrument_key(p.get("symbol"), p.get("localSymbol"), p.get("secType"))
            positions[key] = positions.get(key, 0.0) + float(p.get("position") or 0)
        orders = []
        for o in self.ib.open_orders_snapshot:
            if self.account and o.get("account") not in (None, "", self.account):
                continue
            orders.append(BrokerOrder(
                key=instrument_key(o.get("symbol"), o.get("localSymbol"), o.get("secType")),
                order_id=o.get("orderId"), perm_id=o.get("permId"), side=o.get("action"),
                quantity=o.get("totalQuantity"), remaining=o.get("remaining"), status=str(o.get("status") or "")))
        return BrokerSnapshot(positions={k: q for k, q in positions.items() if q},
                              open_orders=orders, taken_at=_now(),
                              complete=bool(positions_ok and orders_ok), account=self.account)
