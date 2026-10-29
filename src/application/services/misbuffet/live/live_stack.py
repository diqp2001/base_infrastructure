"""
build_live_stack — the ONE deployment path for paper and live trading (P.06.01): it wires everything P.02–P.05 built
around a connected InteractiveBrokersBroker, or refuses.

    stack = build_live_stack(broker, upm, repository_factory,
                             LiveStackConfig(account="DUR314497", strategy="CSM", limits=RiskLimits(...)))
    stack.subscribe(["AAPL", "MSFT"])           # streaming quotes that size orders (P.02)
    if stack.recovery.ensure(): ...             # start-up recovery (P.04); set_holdings calls it as well

Wired:
    streaming quotes          StreamingMarketDataService on the broker's client; StreamingPriceProvider
    order ledger (P.03)       OrderLedger listening to the client; UPM.attach_order_ledger
    reconciler                PositionReconciler over IBKRSnapshotProvider(account); UPM.attach_reconciler
    recovery (P.04)           StartupRecovery; UPM.attach_startup_recovery
    pre-trade gate (P.05)     controls (trading_controls) + OrderThrottle (working orders from the ledger) + limits,
                              IBKRAccountProvider; broker.attach_risk_gate

Refuses (ValueError / PermissionError) when: the broker is not connected; the account is not one the connection
manages; the account's kind (paper D… / live) differs from IBKR_ACCOUNT_MODE (default paper); delayed prices are
asked for a live account. The stack is bound to the broker's current client: after a reconnect that creates a new
client, build the stack again.

``bar_prices`` (PAPER ONLY, with paper_bar_prices): the caller's own completed-bar prices (symbol -> PriceSnapshot,
dated at the bar's close) instead of LastTradeBarPriceProvider — a strategy that has just imported its bars must
not make the gate ask IBKR again for every order and position (IBKR pacing: 60 historical requests / 10 min).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger
from src.application.services.misbuffet.algorithm.position_reconciler import IBKRSnapshotProvider
from src.application.services.misbuffet.algorithm.startup_recovery import StartupRecovery
from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import account_kind, account_mode
from src.application.services.misbuffet.brokers.pre_trade_gate import PreTradeGate
from src.application.services.misbuffet.brokers.trading_controls import (
    IBKRAccountProvider,
    LastTradeBarPriceProvider,
    OrderThrottle,
    StreamingPriceProvider,
    TradingControlsService,
)
from src.application.services.misbuffet.data.streaming_market_data import StreamingMarketDataService
from src.domain.entities.finance.order.pre_trade_risk import RiskLimits

DELAYED_FROZEN = 4                      # IBKR reqMarketDataType: delayed (frozen when closed)


@dataclass
class LiveStackConfig:
    account: str
    strategy: str
    limits: RiskLimits
    allow_delayed_prices: bool = False                  # PAPER ONLY: size orders on delayed quotes (B2)
    paper_bar_prices: bool = False                      # PAPER ONLY: size orders on the last completed TRADES bar
    max_orders: Optional[int] = 20
    order_window_seconds: float = 60.0
    duplicate_seconds: Optional[float] = 30.0
    reconcile_max_age_seconds: float = 60.0
    broker_timeout: float = 10.0
    instrument_for: Callable[[str], str] = lambda symbol: f"STK:{symbol}"


@dataclass
class LiveStack:
    config: LiveStackConfig
    mode: str
    client: object
    streaming: StreamingMarketDataService
    prices: Callable                                    # StreamingPriceProvider or LastTradeBarPriceProvider (paper)
    ledger: OrderLedger
    reconciler: object
    recovery: StartupRecovery
    controls: TradingControlsService
    throttle: OrderThrottle
    gate: PreTradeGate

    def subscribe(self, symbols: Iterable[str], contract_for: Optional[Callable[[str], object]] = None) -> None:
        for symbol in symbols:
            self.streaming.subscribe(self.config.instrument_for(symbol),
                                     (contract_for or stock_contract)(symbol))

    def shutdown(self, reason: str, cancel_working: bool = False) -> dict:
        """Controlled shutdown (P.06.06): apply the broker events received so far, optionally cancel the working
        orders (explicit; the cancels are confirmed by the broker later and resolved by the next start-up recovery),
        stop the quote subscriptions. Working orders that are not cancelled stay working at the broker: the next
        recovery finds them by permId / orderRef. Returns what is left open."""
        applied = self.ledger.drain()
        cancelled = []
        if cancel_working:
            from src.application.services.misbuffet.brokers.trading_controls import cancel_working_orders
            cancelled = cancel_working_orders(self.ledger, self.client, f"shutdown: {reason}")
            self.ledger.drain()
        for sub in list(self.streaming.subscriptions()):
            self.streaming.unsubscribe(sub.instrument)
        left = [{"order_id": b.order_id, "symbol": b.symbol, "status": b.status, "broker_order_id": b.broker_order_id,
                 "cancel_requested": b.cancel_requested_at is not None} for b in self.ledger.open_orders()]
        logging.getLogger("live_stack").warning(
            f"live stack shutdown ({reason}): {applied} event(s) applied, cancels requested {cancelled}, "
            f"{len(left)} order(s) still open, {self.ledger.pending_events()} event(s) not yet stored")
        return {"events_applied": applied, "cancel_requested": cancelled, "open_orders": left,
                "events_pending": self.ledger.pending_events()}

    def status(self) -> dict:
        """Monitoring view (P.06.02–P.06.04): connection, quotes, open orders, recovery, controls, rejections."""
        mode, reasons = self.controls.mode_for(self.config.account, self.config.strategy)
        report = self.recovery.last_report
        return {
            "account": self.config.account, "mode": self.mode, "strategy": self.config.strategy,
            "connected": bool(self.client.is_connected()),
            "trading_control": mode.value, "control_reasons": reasons,
            "recovery": report.summary() if report else "not run",
            "trading_allowed": self.recovery.trading_allowed(),
            "open_orders": [{"order_id": b.order_id, "symbol": b.symbol, "side": b.side,
                             "quantity": b.requested_quantity, "filled": b.filled_quantity, "status": b.status,
                             "submission": b.submission_state.value, "broker_order_id": b.broker_order_id}
                            for b in self.ledger.open_orders()],
            "open_discrepancies": [{"id": d.id, "kind": d.kind.value, "key": d.key, "blocking": d.blocking,
                                    "detail": d.detail} for d in self.recovery.discrepancies.get_open()],
            "ledger_anomalies": list(self.ledger.anomalies[-20:]),
            "gate_rejections": [{"symbol": s, "reasons": list(r)} for s, r in self.gate.rejections[-20:]],
            "quotes": self.streaming.status(),
        }


def _socket_alive(broker) -> bool:
    """The API socket, not the broker's own status (which stays READY after the socket dies)."""
    client = getattr(broker, "ib_connection", None)
    return client is not None and bool(client.is_connected())


class LiveConnectionGuard:
    """Called before each live step (P.04.07): a dropped IBKR connection is reconnected and the order path rebuilt.

    * data connection (historical bars; repository factory's broker): reconnected in place — the IBKR repositories
      reach the broker's current client at every call;
    * order connection: broker events already received are applied, the broker reconnects (a NEW client), and
      ``rebuild()`` builds the live stack again on it (ledger, reconciler, start-up recovery, gate): recovery runs
      again before the next order.

    check(stack) returns the stack to use: the same one, a rebuilt one, or None while the order connection is still
    down (no order this step; the next step tries again). Never raises: a failed attempt is logged and counted."""

    def __init__(self, broker, rebuild: Callable[[], "LiveStack"], data_broker=None, logger=None):
        self.broker = broker
        self.rebuild = rebuild
        self.data_broker = data_broker
        self.logger = logger or logging.getLogger("live_connection")
        self.reconnects = 0
        self.failures = 0

    def _reconnect(self, broker, what: str) -> bool:
        self.logger.critical(f"IBKR {what} connection lost: reconnecting")
        try:
            broker.disconnect()
        except Exception as e:
            self.logger.warning(f"disconnect of the dead {what} connection failed: {e!r}")
        try:
            ok = bool(broker.connect()) and _socket_alive(broker)
        except Exception as e:
            ok = False
            self.logger.error(f"IBKR {what} reconnect raised {e!r}")
        if ok:
            self.reconnects += 1
            self.logger.warning(f"IBKR {what} connection re-established")
        else:
            self.failures += 1
            self.logger.error(f"IBKR {what} reconnect failed: no order this step, next step tries again")
        return ok

    def check(self, stack: Optional["LiveStack"]) -> Optional["LiveStack"]:
        if self.data_broker is not None and self.data_broker is not self.broker and not _socket_alive(self.data_broker):
            self._reconnect(self.data_broker, "data")
        if stack is not None and _socket_alive(self.broker) and stack.client is self.broker.ib_connection:
            return stack
        if stack is not None:
            try:
                stack.ledger.drain()                 # events received before the drop are not lost
            except Exception as e:
                self.logger.warning(f"ledger drain before reconnect failed: {e!r}")
        if not _socket_alive(self.broker) and not self._reconnect(self.broker, "order"):
            return None
        try:
            new_stack = self.rebuild()
        except Exception as e:
            self.failures += 1
            self.logger.error(f"live stack rebuild after reconnect failed: {e!r}")
            return None
        self.logger.warning("live stack rebuilt on the new IBKR connection; start-up recovery re-runs before "
                            "the next order")
        return new_stack


def stock_contract(symbol: str):
    from ibapi.contract import Contract
    c = Contract()
    c.symbol, c.secType, c.exchange, c.currency = symbol, "STK", "SMART", "USD"
    return c


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_live_stack(broker, portfolio_manager, repository_factory, config: LiveStackConfig,
                     multiplier_provider: Optional[Callable[[str], float]] = None, logger=None,
                     bar_prices: Optional[Callable] = None) -> LiveStack:
    log = logger or logging.getLogger("live_stack")
    client = getattr(broker, "ib_connection", None)
    if client is None or not client.is_connected():
        raise ValueError("the broker is not connected (broker.connect() first)")
    managed = client.get_managed_accounts() if hasattr(client, "get_managed_accounts") else client.managed_accounts
    if config.account not in (managed or []):
        raise PermissionError(f"account {config.account} is not managed by this connection {managed}")
    mode = account_mode()
    kind = account_kind(config.account)
    if kind != mode:
        raise PermissionError(f"IBKR_ACCOUNT_MODE={mode} but {config.account} is a {kind} account")
    if (config.allow_delayed_prices or config.paper_bar_prices) and kind != "paper":
        raise PermissionError("delayed prices / last-trade bars may size orders on a PAPER account only")
    if bar_prices is not None and not config.paper_bar_prices:
        raise ValueError("bar_prices replaces the paper last-trade bars: set paper_bar_prices (paper accounts only)")

    if config.allow_delayed_prices:
        client.request_market_data_type(DELAYED_FROZEN)
    streaming = StreamingMarketDataService(client)
    if config.paper_bar_prices:
        prices = bar_prices or LastTradeBarPriceProvider(broker, contract_for=stock_contract)
    else:
        prices = StreamingPriceProvider(streaming, instrument_for=config.instrument_for,
                                        allow_delayed=config.allow_delayed_prices)

    ledger = OrderLedger(repository_factory, logger=log)
    ledger.attach(client)
    portfolio_manager.attach_order_ledger(ledger)
    reconciler = portfolio_manager.attach_reconciler(
        IBKRSnapshotProvider(client, account=config.account, timeout=config.broker_timeout),
        max_age_seconds=config.reconcile_max_age_seconds)
    recovery = StartupRecovery(client, ledger, repository_factory.trading_discrepancy_local_repo,
                               reconciler=reconciler, timeout=config.broker_timeout, logger=log)
    portfolio_manager.attach_startup_recovery(recovery)

    controls = TradingControlsService(repository_factory.trading_control_local_repo, logger=log)
    throttle = OrderThrottle(max_orders=config.max_orders, window_seconds=config.order_window_seconds,
                             duplicate_seconds=config.duplicate_seconds,
                             working_symbols=lambda: [b.symbol for b in ledger.open_orders()
                                                      if b.broker_order_id is not None])
    account_provider = IBKRAccountProvider(client, config.account, prices, multiplier_provider=multiplier_provider,
                                           timeout=config.broker_timeout)
    gate = PreTradeGate(config.limits, account_provider, prices, multiplier_provider=multiplier_provider,
                        clock=_utcnow, logger=log, controls=controls, account=config.account,
                        strategy=config.strategy, throttle=throttle)
    broker.attach_risk_gate(gate)
    log.warning(f"live stack ready: {mode} account {config.account}, strategy {config.strategy}"
                + (" — DELAYED prices allowed (paper)" if config.allow_delayed_prices else "")
                + (" (paper: sizing on last-trade bars)" if config.paper_bar_prices else ""))
    return LiveStack(config, mode, client, streaming, prices, ledger, reconciler, recovery, controls, throttle, gate)
