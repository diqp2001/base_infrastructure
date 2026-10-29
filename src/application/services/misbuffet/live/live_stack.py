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
    prices: StreamingPriceProvider
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


def stock_contract(symbol: str):
    from ibapi.contract import Contract
    c = Contract()
    c.symbol, c.secType, c.exchange, c.currency = symbol, "STK", "SMART", "USD"
    return c


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_live_stack(broker, portfolio_manager, repository_factory, config: LiveStackConfig,
                     multiplier_provider: Optional[Callable[[str], float]] = None, logger=None) -> LiveStack:
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
    if config.allow_delayed_prices and kind != "paper":
        raise PermissionError("delayed prices may size orders on a PAPER account only")

    if config.allow_delayed_prices:
        client.request_market_data_type(DELAYED_FROZEN)
    streaming = StreamingMarketDataService(client)
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
                + (" — DELAYED prices allowed (paper)" if config.allow_delayed_prices else ""))
    return LiveStack(config, mode, client, streaming, prices, ledger, reconciler, recovery, controls, throttle, gate)
