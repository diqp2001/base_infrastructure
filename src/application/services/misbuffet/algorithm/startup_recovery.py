"""
StartupRecovery — rebuild a trustworthy live state from the broker before any order is sent (P.04).

Run at start-up and again after every broker reconnection (``invalidate`` is registered on the client's
connection_listeners; ``ensure`` re-runs it lazily). All broker requests are READ-ONLY.

    1. broker lists      reqAllOpenOrders + reqExecutions (today: IBKR keeps executions of the current day only);
                         an incomplete list (no *End callback) -> INCOMPLETE_SNAPSHOT, blocking
    2. executions        reach the OrderLedger through the client's order listeners and are drained: booked once per
                         execId (replays ignored), commissions once — fills missed while the process was down are
                         booked now; unexplained ones are stored unbooked
    3. internal orders   every open ledger order (INTENT / UNKNOWN / SUBMITTED / PARTIALLY_FILLED) is matched to the
                         broker (permId, orderRef 'MB<id>', orderId):
                           working at the broker   -> kept open (INTENT / UNKNOWN become SUBMITTED)
                           not working, traded     -> FILLED (all executed) or CANCELLED (partly)
                           not working, no trace   -> REJECTED: the broker never had it (INTENT / UNKNOWN), or
                                                      CANCELLED for a SUBMITTED order (it ended without a fill today)
                         each closure is recorded (ORDER_NOT_FOUND / ORDER_CLOSED_ON_RECOVERY, not blocking)
    4. foreign activity  working broker orders and executions no internal order explains -> UNMANAGED_WORKING_ORDER /
                         EXTERNAL_EXECUTION; blocking when the instrument is one the strategy manages
    5. positions         PositionReconciler: every managed instrument's quantity must match the broker ->
                         POSITION_MISMATCH, blocking; mismatches recorded earlier and now matching are resolved
    6. verdict           trading allowed only when the broker lists were complete and no BLOCKING discrepancy is open
                         (including unresolved ones from earlier runs — the owner resolves those: ``resolve``)

Nothing is overwritten silently: every automatic change is a recorded discrepancy with its resolution.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

from src.domain.entities.finance.order.broker_order import SubmissionState, order_id_from_ref
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind

# discrepancies about one immutable broker object (an execId, a broker order, an internal order): once resolved
# they stay resolved when the broker replays the object; position / snapshot ones can happen again
ONE_TIME_KINDS = {DiscrepancyKind.EXTERNAL_EXECUTION, DiscrepancyKind.UNMANAGED_WORKING_ORDER,
                  DiscrepancyKind.ORDER_NOT_FOUND, DiscrepancyKind.ORDER_CLOSED_ON_RECOVERY}
WORKING = {"apipending", "pendingsubmit", "pendingcancel", "presubmitted", "submitted"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _key(symbol, local_symbol=None, sec_type=None) -> str:
    sec = (sec_type or "").upper()
    if sec and sec not in ("STK", "ETF") and local_symbol:
        return " ".join(str(local_symbol).split())
    return " ".join(str(symbol or local_symbol or "").split())


@dataclass
class RecoveryReport:
    ok: bool
    started_at: datetime
    finished_at: Optional[datetime] = None
    lists_complete: bool = False
    events_applied: int = 0
    orders_kept_open: List[int] = field(default_factory=list)
    orders_closed: Dict[int, str] = field(default_factory=dict)       # internal order id -> new status
    new_discrepancies: List[Discrepancy] = field(default_factory=list)
    resolved_discrepancies: List[Discrepancy] = field(default_factory=list)
    blocking: List[Discrepancy] = field(default_factory=list)          # open blocking discrepancies after the run
    error: Optional[str] = None

    def summary(self) -> str:
        if self.error:
            return f"recovery FAILED: {self.error}"
        head = "recovery OK" if self.ok else "recovery BLOCKED"
        parts = [f"{self.events_applied} broker event(s)", f"{len(self.orders_kept_open)} order(s) still working",
                 f"{len(self.orders_closed)} closed", f"{len(self.new_discrepancies)} new discrepancy(ies)"]
        if self.blocking:
            parts.append("blocking: " + "; ".join(f"{d.kind.value} {d.key}" for d in self.blocking))
        return f"{head}: " + ", ".join(parts)


class StartupRecovery:

    def __init__(self, client, ledger, discrepancies, reconciler=None,
                 managed_tickers: Optional[Callable[[], Iterable[str]]] = None, timeout: float = 10.0,
                 clock: Callable[[], datetime] = _utcnow, logger=None):
        """
        Args:
            client:          IBTWSClient-like: is_connected, request_open_orders_snapshot / open_orders_snapshot,
                             request_executions_snapshot, connection_listeners, order_listeners (ledger attached)
            ledger:          OrderLedger (attached to the client)
            discrepancies:   DiscrepancyPort (RepositoryFactory.trading_discrepancy_local_repo)
            reconciler:      PositionReconciler (positions strategy vs broker); None skips step 5
            managed_tickers: instruments the strategy manages (default: the reconciler's)
        """
        self.client = client
        self.ledger = ledger
        self.discrepancies = discrepancies
        self.reconciler = reconciler
        self.managed_tickers = managed_tickers or (reconciler.managed_tickers if reconciler is not None else None)
        self.timeout = timeout
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.last_report: Optional[RecoveryReport] = None
        self._valid = False
        self._lock = threading.Lock()
        listeners = getattr(client, "connection_listeners", None)
        if listeners is not None:
            listeners.append(self.invalidate)

    # -- gate ----------------------------------------------------------------------------------------------------
    def invalidate(self) -> None:
        """The broker connection closed: the recovered state is no longer trusted until the next run."""
        self._valid = False

    def ensure(self) -> bool:
        """Trading allowed? Runs the recovery first when it never ran or the connection dropped since."""
        if not self._valid:
            self.run()
        return self.trading_allowed()

    def trading_allowed(self) -> bool:
        if not self._valid or self.last_report is None or not self.last_report.ok:
            return False
        return not any(d.blocking for d in self.discrepancies.get_open())     # owner-resolved since? re-read

    def resolve(self, discrepancy_id: int, resolution: str) -> Discrepancy:
        """The owner resolves a discrepancy (e.g. 'manual trade, position adjusted in the books on ...')."""
        d = self.discrepancies.get_by_id(discrepancy_id)
        if d is None:
            raise LookupError(f"discrepancy {discrepancy_id} does not exist")
        d.resolve(resolution, self._now())
        d = self.discrepancies.update(d)
        self._valid = False                    # the next ensure() re-checks the broker before allowing trading
        return d

    # -- run -------------------------------------------------------------------------------------------------------
    def run(self) -> RecoveryReport:
        with self._lock:
            report = RecoveryReport(ok=False, started_at=self._now())
            try:
                self._run(report)
            except Exception as e:
                report.error = repr(e)
                report.ok = False
            report.finished_at = self._now()
            report.blocking = [d for d in self.discrepancies.get_open() if d.blocking] if report.error is None else []
            report.ok = report.error is None and report.lists_complete and not report.blocking
            self.last_report = report
            self._valid = report.error is None and report.lists_complete
            (self.logger.info if report.ok else self.logger.critical)(report.summary())
            return report

    def _run(self, report: RecoveryReport) -> None:
        if not self.client.is_connected():
            self._record(report, DiscrepancyKind.INCOMPLETE_SNAPSHOT, "broker", "broker not connected", True)
            return
        orders_ok = self.client.request_open_orders_snapshot(timeout=self.timeout)
        executions_ok = self.client.request_executions_snapshot(timeout=self.timeout)
        report.lists_complete = bool(orders_ok and executions_ok)
        if not report.lists_complete:
            missing = [n for n, ok in (("open orders", orders_ok), ("executions", executions_ok)) if not ok]
            self._record(report, DiscrepancyKind.INCOMPLETE_SNAPSHOT, "broker",
                         f"the broker did not confirm the end of: {', '.join(missing)}", True)
            return
        self._auto_resolve(report, DiscrepancyKind.INCOMPLETE_SNAPSHOT, set(), "broker lists complete on recovery",
                           only_key="broker")
        report.events_applied = self.ledger.drain()                       # executions + commissions (+ statuses)

        open_rows = [dict(r) for r in (getattr(self.client, "open_orders_snapshot", None) or [])]
        working = [r for r in open_rows if str(r.get("status") or "").lower() in WORKING
                   or (r.get("remaining") is None and str(r.get("status") or "").lower() not in
                       ("filled", "cancelled", "apicancelled", "inactive"))]
        explained_rows = set()
        managed = self._managed()

        for bo in self.ledger.open_orders():
            row = self._working_row(bo, working)
            if row is not None:
                explained_rows.add(id(row))
                if bo.submission_state in (SubmissionState.INTENT, SubmissionState.UNKNOWN):
                    self.ledger.mark_submitted(bo, row.get("orderId"), row.get("clientId"))
                if row.get("permId") and not bo.perm_id:
                    bo.perm_id = int(row["permId"])
                    self.ledger.orders.update(bo)
                report.orders_kept_open.append(bo.order_id)
                continue
            self._close(report, bo)

        for row in working:
            if id(row) in explained_rows:
                continue
            key = _key(row.get("symbol"), row.get("localSymbol"), row.get("secType"))
            self._record(report, DiscrepancyKind.UNMANAGED_WORKING_ORDER, f"{row.get('permId') or row.get('orderId')}",
                         f"working broker order {row.get('action')} {row.get('totalQuantity')} {key} "
                         f"(orderId {row.get('orderId')}, client {row.get('clientId')}, status {row.get('status')}) "
                         f"is not an order of this strategy", key in managed)

        for ex in self.ledger.executions.get_unexplained():
            self._record(report, DiscrepancyKind.EXTERNAL_EXECUTION, ex.exec_id,
                         f"execution {ex.side} {ex.quantity:g} {ex.symbol} @ {ex.price} at {ex.executed_at} "
                         f"(broker order {ex.broker_order_id}, perm {ex.perm_id}) explained by no internal order",
                         _key(ex.symbol) in managed or not managed)

        if self.reconciler is not None:
            result = self.reconciler.check()
            if result.error:
                self._record(report, DiscrepancyKind.INCOMPLETE_SNAPSHOT, "positions",
                             f"position reconciliation failed: {result.error}", True)
                return
            self._auto_resolve(report, DiscrepancyKind.INCOMPLETE_SNAPSHOT, set(), "position snapshot complete",
                               only_key="positions")
            current = set()
            for m in result.mismatches:
                current.add(m["ticker"])
                self._record(report, DiscrepancyKind.POSITION_MISMATCH, m["ticker"],
                             f"{m['ticker']}: strategy {m['strategy_qty']:g}, broker {m['broker_qty']:g}", True)
            self._auto_resolve(report, DiscrepancyKind.POSITION_MISMATCH, current,
                               "strategy and broker quantities matched on recovery")

    # -- helpers ---------------------------------------------------------------------------------------------------
    def _working_row(self, bo, rows: List[dict]) -> Optional[dict]:
        for r in rows:
            if bo.perm_id and r.get("permId") and int(r["permId"]) == int(bo.perm_id):
                return r
            if order_id_from_ref(r.get("orderRef")) == bo.order_id:
                return r
            if (bo.broker_order_id is not None and r.get("orderId") is not None
                    and int(r["orderId"]) == int(bo.broker_order_id)
                    and (bo.client_id is None or r.get("clientId") in (None, bo.client_id))):
                return r
        return None

    def _close(self, report: RecoveryReport, bo) -> None:
        executed = sum(e.quantity for e in self.ledger.executions.get_by_order_id(bo.order_id) if e.booked)
        never_had = bo.submission_state in (SubmissionState.INTENT, SubmissionState.UNKNOWN) and executed == 0
        if never_had:
            status, kind = "REJECTED", DiscrepancyKind.ORDER_NOT_FOUND
            reason = (f"{bo.submission_state.value} order not at the broker on recovery (no working order, no "
                      f"execution today): the broker never had it")
        elif executed >= bo.requested_quantity - 1e-9:
            status, kind = "FILLED", DiscrepancyKind.ORDER_CLOSED_ON_RECOVERY
            reason = f"no longer working at the broker; executions today cover {executed:g}/{bo.requested_quantity:g}"
        else:
            status, kind = "CANCELLED", DiscrepancyKind.ORDER_CLOSED_ON_RECOVERY
            reason = (f"no longer working at the broker; executions today {executed:g}/{bo.requested_quantity:g} "
                      f"(fills on earlier days are not returned by IBKR: the position check decides)")
        bo.close_on_recovery(status, executed, reason, self._now())
        self.ledger._save(bo)
        report.orders_closed[bo.order_id] = status
        d = self._record(report, kind, str(bo.order_id), f"order {bo.order_id} {bo.side} {bo.requested_quantity:g} "
                         f"{bo.symbol}: {reason}", False, order_id=bo.order_id)
        if d is not None and d.is_open:
            d.resolve(f"closed as {status} on recovery", self._now())
            self.discrepancies.update(d)

    def _record(self, report: RecoveryReport, kind: DiscrepancyKind, key: str, detail: str, blocking: bool,
                order_id: Optional[int] = None) -> Optional[Discrepancy]:
        existing = self.discrepancies.get_open_by_key(kind, key)
        if existing is not None:
            return existing                                                    # already known, still open
        if kind in ONE_TIME_KINDS:
            existing = self.discrepancies.get_latest_by_key(kind, key)
            if existing is not None:
                return existing                    # this execution / order was already reported and resolved
        d = self.discrepancies.add(Discrepancy(kind=kind, key=key, detail=detail, detected_at=self._now(),
                                               blocking=blocking, broker=self.ledger.broker, order_id=order_id))
        report.new_discrepancies.append(d)
        (self.logger.critical if blocking else self.logger.warning)(f"recovery: {kind.value} {key}: {detail}")
        return d

    def _auto_resolve(self, report: RecoveryReport, kind: DiscrepancyKind, still: set, resolution: str,
                      only_key: Optional[str] = None) -> None:
        """Resolve the open discrepancies of `kind` that this run no longer finds (`still` = keys still found)."""
        for d in self.discrepancies.get_open(kind):
            if d.key in still or (only_key is not None and d.key != only_key):
                continue
            d.resolve(f"{resolution} ({self._now():%Y-%m-%d %H:%M:%S} UTC)", self._now())
            self.discrepancies.update(d)
            report.resolved_discrepancies.append(d)

    def _managed(self) -> set:
        if self.managed_tickers is None:
            return set()
        try:
            return {" ".join(str(t).split()) for t in self.managed_tickers()}
        except Exception as e:
            self.logger.error(f"recovery: managed instruments unavailable ({e}) — every foreign activity blocks")
            return set()

    def _now(self) -> datetime:
        now = self.clock()
        return now.astimezone(timezone.utc).replace(tzinfo=None) if now.tzinfo is not None else now
