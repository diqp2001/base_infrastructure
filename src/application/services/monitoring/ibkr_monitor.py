"""
Read-only IBKR monitoring: one background API connection, cached snapshots for the dashboard.

ReadOnlyIBKRClient is a dedicated ibapi client (it does NOT reuse IBTWSClient, which has
order methods). Every method that can submit, modify or cancel orders, exercise options,
bind orders or change account configuration raises ``IBKRReadOnlyViolation``.

The monitor only sends: reqCurrentTime (heartbeat), reqAccountSummary / cancelAccountSummary,
reqAccountUpdates (portfolio values), reqPositions / cancelPositions, reqAllOpenOrders.
Browser requests never talk to IBKR: they read the snapshot kept here.
"""

import itertools
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from src.application.services.monitoring.redaction import redact_text
from src.application.services.monitoring.status import (
    DEGRADED, DISCONNECTED, ERROR, HEALTHY, UNKNOWN, iso, utcnow,
)

logger = logging.getLogger("monitoring.ibkr")

SUMMARY_TAGS = ("AccountType,NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,"
                "EquityWithLoanValue,GrossPositionValue,AvailableFunds,ExcessLiquidity,Cushion,"
                "FullInitMarginReq,FullMaintMarginReq,Leverage")
LEDGER_TAGS = "$LEDGER:ALL"
# error codes that are informational ("market data farm connection is OK", ...)
INFO_CODES = {2104, 2106, 2107, 2108, 2119, 2158, 2100, 2150}
CONNECTIVITY_CODES = {502, 504, 1100, 1101, 1102, 1300, 2110, 507, 326}
FORBIDDEN_METHODS = (
    "placeOrder", "cancelOrder", "reqGlobalCancel", "exerciseOptions", "reqAutoOpenOrders",
    "replaceFA", "requestFA", "reqIds",
)


class IBKRReadOnlyViolation(PermissionError):
    """An order / configuration method was called on the read-only monitoring client."""


def _forbidden(name: str) -> Callable:
    def method(self, *args, **kwargs):
        raise IBKRReadOnlyViolation(f"{name} is not allowed on the read-only monitoring client")
    method.__name__ = name
    return method


def _num(value: Any) -> Optional[float]:
    """Parse an IBKR numeric field; None when absent (never silently 0)."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or abs(f) >= 1.7e308:        # NaN / UNSET_DOUBLE
        return None
    return f


class ReadOnlyIBKRClient(EWrapper, EClient):
    """ibapi client that forwards callbacks to an IBKRMonitor and refuses all mutating calls."""

    def __init__(self, sink: "IBKRMonitor"):
        EWrapper.__init__(self)
        EClient.__init__(self, self)
        self.sink = sink

    # ---- callbacks -------------------------------------------------------------------------
    def nextValidId(self, orderId: int):
        self.sink._on_ready()

    def managedAccounts(self, accountsList: str):
        self.sink._on_accounts([a.strip() for a in (accountsList or "").split(",") if a.strip()])

    def currentTime(self, time_: int):
        self.sink._on_current_time(time_)

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        self.sink._on_summary(reqId, account, tag, value, currency)

    def accountSummaryEnd(self, reqId: int):
        self.sink._on_summary_end(reqId)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        self.sink._on_account_value(key, val, currency, accountName)

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost,
                        unrealizedPNL, realizedPNL, accountName):
        self.sink._on_portfolio(contract, position, marketPrice, marketValue, averageCost,
                                unrealizedPNL, realizedPNL, accountName)

    def updateAccountTime(self, timeStamp: str):
        self.sink._on_account_time(timeStamp)

    def position(self, account: str, contract, position, avgCost):
        self.sink._on_position(account, contract, position, avgCost)

    def positionEnd(self):
        self.sink._on_position_end()

    def openOrder(self, orderId, contract, order, orderState):
        self.sink._on_open_order(orderId, contract, order, orderState)

    def orderStatus(self, orderId, status, filled, remaining, *args):
        self.sink._on_order_status(orderId, status, filled, remaining)

    def openOrderEnd(self):
        self.sink._on_open_order_end()

    def error(self, reqId, errorCode, errorString, *args):
        self.sink._on_error(reqId, errorCode, errorString)

    def connectionClosed(self):
        self.sink._on_closed()


for _name in FORBIDDEN_METHODS:
    setattr(ReadOnlyIBKRClient, _name, _forbidden(_name))


def _contract_view(contract) -> Dict[str, Any]:
    return {
        "con_id": getattr(contract, "conId", None),
        "symbol": getattr(contract, "symbol", None),
        "local_symbol": getattr(contract, "localSymbol", None) or None,
        "sec_type": getattr(contract, "secType", None),
        "currency": getattr(contract, "currency", None),
        "exchange": getattr(contract, "exchange", None) or getattr(contract, "primaryExchange", None) or None,
        "expiry": getattr(contract, "lastTradeDateOrContractMonth", None) or None,
        "strike": _num(getattr(contract, "strike", None)) or None,
        "right": getattr(contract, "right", None) or None,
        "multiplier": getattr(contract, "multiplier", None) or None,
    }


class IBKRMonitor:

    def __init__(self, host: str, port: int, client_id: int, configured_mode: str,
                 account_interval: int = 30, positions_interval: int = 30, heartbeat_interval: int = 10,
                 client_factory: Optional[Callable[["IBKRMonitor"], Any]] = None, max_errors: int = 50):
        self.host, self.port, self.client_id = host, int(port), int(client_id)
        self.configured_mode = configured_mode
        self.account_interval = account_interval
        self.positions_interval = positions_interval
        self.heartbeat_interval = heartbeat_interval
        self.client_factory = client_factory or ReadOnlyIBKRClient
        self._lock = threading.RLock()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._client = None
        self._req_ids = itertools.count(9000)
        # state
        self.connected = False
        self.accounts: List[str] = []
        self.connected_since: Optional[datetime] = None
        self.last_connect_attempt: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.server_time: Optional[int] = None
        self.errors: Deque[Dict[str, Any]] = deque(maxlen=max_errors)
        self.connection_failures: Deque[Dict[str, Any]] = deque(maxlen=max_errors)
        self._summary_req: Dict[int, str] = {}            # reqId -> "summary" | "ledger"
        self._summary_stage: Dict[str, Dict] = {"summary": {}, "ledger": {}}
        self.summary: Dict[str, Dict[str, Any]] = {}      # tag -> {value, raw, currency, account}
        self.ledger: Dict[str, Dict[str, Any]] = {}       # currency -> {tag: value}
        self.summary_updated: Optional[datetime] = None
        self.account_values: Dict[str, Dict[str, Any]] = {}
        self.account_time: Optional[str] = None
        self.portfolio: Dict[Any, Dict[str, Any]] = {}    # con_id -> market data from updatePortfolio
        self.portfolio_updated: Optional[datetime] = None
        self._positions_stage: Dict[Any, Dict[str, Any]] = {}
        self.positions: Dict[Any, Dict[str, Any]] = {}
        self.positions_updated: Optional[datetime] = None
        self._orders_stage: Dict[int, Dict[str, Any]] = {}
        self.orders: Dict[int, Dict[str, Any]] = {}
        self.orders_updated: Optional[datetime] = None
        self._order_status: Dict[int, Dict[str, Any]] = {}
        self._subscribed_account: Optional[str] = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="ibkr-monitor", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._disconnect()

    @property
    def thread_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _connect(self) -> bool:
        self.last_connect_attempt = utcnow()
        self._ready.clear()
        client = self.client_factory(self)
        try:
            client.connect(self.host, self.port, self.client_id)
        except Exception as e:
            self._failure(f"connect failed: {e}")
            return False
        if not client.isConnected():
            self._failure(f"no API socket at {self.host}:{self.port}")
            return False
        threading.Thread(target=client.run, name="ibkr-monitor-reader", daemon=True).start()
        if not self._ready.wait(10):
            self._failure("API handshake timed out (gateway not logged in?)")
            try:
                client.disconnect()
            except Exception:
                pass
            return False
        with self._lock:
            self._client = client
            self.connected = True
            self.connected_since = utcnow()
            self.last_heartbeat = utcnow()
        logger.info("IBKR monitor connected to %s:%s (client %s)", self.host, self.port, self.client_id)
        return True

    def _disconnect(self) -> None:
        with self._lock:
            client, self._client = self._client, None
            self.connected = False
            self._subscribed_account = None
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass

    def _failure(self, message: str) -> None:
        entry = {"ts": iso(utcnow()), "message": redact_text(message)}
        with self._lock:
            self.connection_failures.appendleft(entry)
            self.connected = False
        logger.warning("IBKR monitor: %s", entry["message"])

    def _loop(self) -> None:
        backoff = 5.0
        last = {"hb": 0.0, "account": 0.0, "positions": 0.0}
        while not self._stop.is_set():
            if not self.connected:
                if self._client is not None:       # e.g. error 1100: drop the old socket first
                    self._disconnect()
                if self._connect():
                    backoff = 5.0
                    last = {"hb": 0.0, "account": 0.0, "positions": 0.0}
                else:
                    self._stop.wait(backoff)
                    backoff = min(backoff * 2, 120.0)
                    continue
            now = time.monotonic()
            client = self._client
            try:
                if client is None or not client.isConnected():
                    raise ConnectionError("API socket closed")
                if now - last["hb"] >= self.heartbeat_interval:
                    last["hb"] = now
                    stale = self.last_heartbeat and (utcnow() - self.last_heartbeat).total_seconds() \
                        > 3 * self.heartbeat_interval + 10
                    if stale:
                        raise ConnectionError("no heartbeat answer from IB Gateway")
                    client.reqCurrentTime()
                if now - last["account"] >= self.account_interval:
                    last["account"] = now
                    self._request_summaries(client)
                    self._ensure_account_updates(client)
                if now - last["positions"] >= self.positions_interval:
                    last["positions"] = now
                    with self._lock:
                        self._positions_stage = {}
                        self._orders_stage = {}
                    client.reqPositions()
                    client.reqAllOpenOrders()
            except IBKRReadOnlyViolation:
                raise
            except Exception as e:
                self._failure(f"connection lost: {e}")
                self._disconnect()
                continue
            self._stop.wait(1.0)

    def _request_summaries(self, client) -> None:
        """Cancel the active account-summary subscriptions, then request a fresh snapshot."""
        with self._lock:
            for req_id in list(self._summary_req):
                try:
                    client.cancelAccountSummary(req_id)
                except Exception:
                    pass
            self._summary_req.clear()
            self._summary_stage = {"summary": {}, "ledger": {}}
            sid, lid = next(self._req_ids), next(self._req_ids)
            self._summary_req[sid] = "summary"
            self._summary_req[lid] = "ledger"
        client.reqAccountSummary(sid, "All", SUMMARY_TAGS)
        client.reqAccountSummary(lid, "All", LEDGER_TAGS)

    def _ensure_account_updates(self, client) -> None:
        with self._lock:
            account = self.accounts[0] if self.accounts else None
            if not account or self._subscribed_account == account:
                return
            self._subscribed_account = account
        client.reqAccountUpdates(True, account)

    # ------------------------------------------------------------------ callbacks
    def _on_ready(self) -> None:
        self._ready.set()

    def _on_accounts(self, accounts: List[str]) -> None:
        with self._lock:
            self.accounts = accounts

    def _on_current_time(self, t: int) -> None:
        with self._lock:
            self.server_time = int(t)
            self.last_heartbeat = utcnow()

    def _on_summary(self, req_id, account, tag, value, currency) -> None:
        with self._lock:
            kind = self._summary_req.get(req_id)
            if kind == "summary":
                self._summary_stage["summary"][tag] = {"value": _num(value), "raw": value,
                                                       "currency": currency or None, "account": account}
            elif kind == "ledger" and currency:
                # $LEDGER:ALL tags arrive as "$LEDGER-CashBalance", one set per currency plus "BASE"
                name = tag.split("-", 1)[1] if tag.startswith("$LEDGER-") else tag
                self._summary_stage["ledger"].setdefault(currency, {})[name] = _num(value)

    def _on_summary_end(self, req_id) -> None:
        # reqAccountSummary is a subscription: it stays active after End (IBKR allows two), so the
        # request id is kept in _summary_req and cancelled by the next _request_summaries call.
        with self._lock:
            kind = self._summary_req.get(req_id)
            if kind == "summary":
                self.summary = dict(self._summary_stage["summary"])
                self.summary_updated = utcnow()
            elif kind == "ledger":
                self.ledger = {c: dict(v) for c, v in self._summary_stage["ledger"].items()}

    def _on_account_value(self, key, val, currency, account) -> None:
        with self._lock:
            self.account_values[f"{key}:{currency or ''}"] = {"key": key, "value": _num(val), "raw": val,
                                                               "currency": currency or None}

    def _on_portfolio(self, contract, position, market_price, market_value, average_cost,
                      unrealized, realized, account) -> None:
        item = _contract_view(contract)
        item.update(account=account, quantity=_num(position), market_price=_num(market_price),
                    market_value=_num(market_value), average_cost=_num(average_cost),
                    unrealized_pnl=_num(unrealized), realized_pnl=_num(realized))
        with self._lock:
            if item["quantity"] in (0, 0.0):
                self.portfolio.pop(item["con_id"], None)
            else:
                self.portfolio[item["con_id"]] = item
            self.portfolio_updated = utcnow()

    def _on_account_time(self, stamp) -> None:
        with self._lock:
            self.account_time = stamp

    def _on_position(self, account, contract, position, avg_cost) -> None:
        item = _contract_view(contract)
        item.update(account=account, quantity=_num(position), average_cost=_num(avg_cost))
        with self._lock:
            if item["quantity"] not in (0, 0.0, None):
                self._positions_stage[(account, item["con_id"])] = item

    def _on_position_end(self) -> None:
        with self._lock:
            self.positions = self._positions_stage
            self._positions_stage = {}
            self.positions_updated = utcnow()

    def _on_open_order(self, order_id, contract, order, state) -> None:
        item = _contract_view(contract)
        item.update(order_id=order_id, perm_id=getattr(order, "permId", None),
                    client_id=getattr(order, "clientId", None), account=getattr(order, "account", None),
                    side=getattr(order, "action", None), order_type=getattr(order, "orderType", None),
                    quantity=_num(getattr(order, "totalQuantity", None)),
                    limit_price=_num(getattr(order, "lmtPrice", None)),
                    stop_price=_num(getattr(order, "auxPrice", None)),
                    tif=getattr(order, "tif", None), status=getattr(state, "status", None))
        with self._lock:
            self._orders_stage[item["perm_id"] or order_id] = item

    def _on_order_status(self, order_id, status, filled, remaining) -> None:
        with self._lock:
            self._order_status[order_id] = {"status": status, "filled": _num(filled),
                                            "remaining": _num(remaining), "ts": iso(utcnow())}

    def _on_open_order_end(self) -> None:
        with self._lock:
            self.orders = self._orders_stage
            self._orders_stage = {}
            self.orders_updated = utcnow()

    def _on_error(self, req_id, code, message) -> None:
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = -1
        if code in INFO_CODES:
            return
        entry = {"ts": iso(utcnow()), "code": code, "req_id": req_id,
                 "message": redact_text(str(message))[:500],
                 "kind": "connectivity" if code in CONNECTIVITY_CODES else "api"}
        with self._lock:
            self.errors.appendleft(entry)
        if code in (1100, 504):
            with self._lock:
                self.connected = False
        logger.warning("IBKR API error %s: %s", code, entry["message"])

    def _on_closed(self) -> None:
        with self._lock:
            self.connected = False
        logger.warning("IBKR monitor connection closed by the gateway")

    # ------------------------------------------------------------------ read views
    def detected_mode(self) -> Optional[str]:
        accounts = list(self.accounts)
        if not accounts:
            return None
        return "paper" if all(a.upper().startswith("D") for a in accounts) else "live"

    def connection_view(self) -> Dict[str, Any]:
        with self._lock:
            hb_age = (utcnow() - self.last_heartbeat).total_seconds() if self.last_heartbeat else None
            if self.connected and hb_age is not None and hb_age <= 3 * self.heartbeat_interval + 10:
                status = HEALTHY if self.summary_updated else DEGRADED
            elif self.connected:
                status = DEGRADED
            elif self.last_connect_attempt is None:
                status = UNKNOWN
            else:
                status = DISCONNECTED
            detected = self.detected_mode()
            return {
                "status": status,
                "connected": self.connected,
                "host": self.host, "port": self.port, "client_id": self.client_id,
                "configured_mode": self.configured_mode,
                "detected_mode": detected,
                "mode_mismatch": bool(detected and detected != self.configured_mode),
                "accounts": list(self.accounts),
                "connected_since": iso(self.connected_since),
                "last_connect_attempt": iso(self.last_connect_attempt),
                "last_heartbeat": iso(self.last_heartbeat),
                "heartbeat_age_seconds": None if hb_age is None else round(hb_age, 1),
                "server_time": (datetime.fromtimestamp(self.server_time, tz=timezone.utc).isoformat()
                                if self.server_time else None),
                "last_account_update": iso(self.summary_updated),
                "last_positions_update": iso(self.positions_updated),
                "last_orders_update": iso(self.orders_updated),
                "recent_errors": list(self.errors)[:20],
                "connection_failures": list(self.connection_failures)[:20],
                "thread_alive": self.thread_alive,
            }

    def account_view(self) -> Dict[str, Any]:
        with self._lock:
            summary = dict(self.summary)
            ledger = {c: dict(v) for c, v in self.ledger.items()}
            portfolio = list(self.portfolio.values())
            account_values = dict(self.account_values)
        base_currency = next((v["currency"] for v in summary.values() if v.get("currency")), None)

        def field(tag: str) -> Dict[str, Any]:
            item = summary.get(tag)
            if not item:
                return {"value": None, "currency": None, "available": False}
            return {"value": item["value"], "currency": item["currency"], "available": item["value"] is not None}

        def from_values(key: str) -> Dict[str, Any]:
            item = account_values.get(f"{key}:{base_currency}") or account_values.get(f"{key}:BASE")
            if not item:
                return {"value": None, "currency": base_currency, "available": False}
            return {"value": item["value"], "currency": item["currency"] or base_currency,
                    "available": item["value"] is not None}

        cash = [{"currency": c, "cash_balance": v.get("CashBalance"), "total_cash_value": v.get("TotalCashValue"),
                 "net_liquidation": v.get("NetLiquidationByCurrency"),
                 "unrealized_pnl": v.get("UnrealizedPnL"), "realized_pnl": v.get("RealizedPnL"),
                 "exchange_rate": v.get("ExchangeRate")}
                for c, v in sorted(ledger.items()) if c != "BASE"]
        exposure: Dict[str, Dict[str, float]] = {}
        for p in portfolio:
            mv, cur = p.get("market_value"), p.get("currency") or "?"
            if mv is None:
                continue
            e = exposure.setdefault(cur, {"currency": cur, "gross": 0.0, "net": 0.0, "positions": 0})
            e["gross"] += abs(mv)
            e["net"] += mv
            e["positions"] += 1
        base_ledger = ledger.get("BASE", {})
        return {
            "accounts": list(self.accounts),
            "base_currency": base_currency,
            "account_type": (summary.get("AccountType") or {}).get("raw"),
            "values": {
                "net_liquidation": field("NetLiquidation"),
                "total_cash_value": field("TotalCashValue"),
                "settled_cash": field("SettledCash"),
                "available_funds": field("AvailableFunds"),
                "excess_liquidity": field("ExcessLiquidity"),
                "buying_power": field("BuyingPower"),
                "equity_with_loan": field("EquityWithLoanValue"),
                "gross_position_value": field("GrossPositionValue"),
                "init_margin": field("FullInitMarginReq"),
                "maint_margin": field("FullMaintMarginReq"),
                "unrealized_pnl": ({"value": base_ledger.get("UnrealizedPnL"), "currency": base_currency,
                                    "available": base_ledger.get("UnrealizedPnL") is not None}
                                   if base_ledger else from_values("UnrealizedPnL")),
                "realized_pnl": ({"value": base_ledger.get("RealizedPnL"), "currency": base_currency,
                                  "available": base_ledger.get("RealizedPnL") is not None}
                                 if base_ledger else from_values("RealizedPnL")),
            },
            "cash_by_currency": cash,
            "exposure_by_currency": sorted(exposure.values(), key=lambda e: e["currency"]),
            "exposure_note": "Gross / net exposure per position currency from portfolio market values; "
                             "currencies are never combined.",
            "account_time": self.account_time,
            "updated_at": iso(self.summary_updated),
        }

    def positions_view(self) -> Dict[str, Any]:
        with self._lock:
            positions = [dict(p) for p in self.positions.values()]
            portfolio = {p["con_id"]: p for p in self.portfolio.values()}
            updated = self.positions_updated
        rows = []
        for p in positions:
            market = portfolio.get(p["con_id"], {})
            row = dict(p)
            for key in ("market_price", "market_value", "unrealized_pnl", "realized_pnl"):
                row[key] = market.get(key)
            row["market_data_available"] = bool(market)
            rows.append(row)
        rows.sort(key=lambda r: (str(r.get("sec_type")), str(r.get("symbol"))))
        return {"positions": rows, "count": len(rows), "updated_at": iso(updated),
                "market_values_updated_at": iso(self.portfolio_updated)}

    def orders_view(self) -> Dict[str, Any]:
        with self._lock:
            orders = [dict(o) for o in self.orders.values()]
            statuses = dict(self._order_status)
            updated = self.orders_updated
        for o in orders:
            st = statuses.get(o.get("order_id"), {})
            o["status"] = st.get("status") or o.get("status")
            o["filled"] = st.get("filled")
            o["remaining"] = st.get("remaining")
            o["submitted_at"] = None            # not provided by the IBKR API for open orders
        orders.sort(key=lambda o: str(o.get("symbol")))
        return {"orders": orders, "count": len(orders), "updated_at": iso(updated)}
