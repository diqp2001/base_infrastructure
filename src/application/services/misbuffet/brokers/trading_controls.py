"""
Trading controls and the providers that feed the pre-trade gate (P.05).

TradingControlsService   kill switch / reduce-only / enable per scope (table trading_controls, append-only).
                         An unreadable control store counts as DISABLED (fail closed).
OrderThrottle            order-rate limit (N orders per window) and duplicate protection (the same symbol and signed
                         quantity again within a few seconds, or while an order on the symbol is still working).
StreamingPriceProvider   PriceSnapshot from the streaming quotes (P.02): only an EXECUTABLE quote (live, entitled,
                         fresh, valid two-sided) can size an order; otherwise the reason refuses it.
IBKRAccountProvider      AccountSnapshot from IBKR account values (NetLiquidation, TotalCashValue, BuyingPower) and the
                         positions snapshot, exposures valued with the price provider (a missing price fails closed).
cancel_working_orders    explicit emergency action: cancel every working order of the ledger at the broker (the status
                         changes only when the broker confirms, D4). It is never called automatically.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, Iterable, List, Optional, Tuple

from src.domain.entities.finance.order.pre_trade_risk import AccountSnapshot, PriceSnapshot
from src.domain.entities.finance.order.trading_control import (
    GLOBAL_TARGET,
    ControlMode,
    ControlScope,
    TradingControl,
    effective_mode,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TradingControlsService:

    def __init__(self, repository, clock: Callable[[], datetime] = _utcnow, logger=None):
        self.repo = repository
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def set(self, scope: ControlScope, target: str, mode: ControlMode, reason: str, changed_by: str) -> TradingControl:
        now = self.clock()
        now = now.astimezone(timezone.utc).replace(tzinfo=None) if now.tzinfo else now
        control = self.repo.add(TradingControl(scope, target or GLOBAL_TARGET, mode, reason, changed_by, now))
        (self.logger.critical if mode is not ControlMode.ENABLED else self.logger.warning)(
            f"trading control: {scope.value} {control.target} -> {mode.value} ({reason}; {changed_by})")
        return control

    def kill(self, reason: str, changed_by: str) -> TradingControl:
        """Kill switch: no new order at all, every account and strategy."""
        return self.set(ControlScope.GLOBAL, GLOBAL_TARGET, ControlMode.DISABLED, reason, changed_by)

    def mode_for(self, account: Optional[str], strategy: Optional[str]) -> Tuple[ControlMode, List[str]]:
        try:
            return effective_mode(self.repo.get_all(), account, strategy)
        except Exception as e:
            return ControlMode.DISABLED, [f"trading controls unreadable ({e!r}): fail closed"]

    def history(self) -> List[TradingControl]:
        return self.repo.get_all()


class OrderThrottle:

    def __init__(self, max_orders: Optional[int] = None, window_seconds: float = 60.0,
                 duplicate_seconds: Optional[float] = 30.0,
                 working_symbols: Optional[Callable[[], Iterable[str]]] = None,
                 clock: Callable[[], float] = time.monotonic):
        self.max_orders = max_orders
        self.window_seconds = window_seconds
        self.duplicate_seconds = duplicate_seconds
        self.working_symbols = working_symbols
        self.clock = clock
        self._sent: Deque[Tuple[float, str, float]] = deque()

    def refusal(self, symbol: str, quantity: float) -> Optional[str]:
        now = self.clock()
        while self._sent and now - self._sent[0][0] > max(self.window_seconds, self.duplicate_seconds or 0):
            self._sent.popleft()
        if self.max_orders is not None:
            recent = sum(1 for t, _, _ in self._sent if now - t <= self.window_seconds)
            if recent >= self.max_orders:
                return f"order rate: {recent} orders in the last {self.window_seconds:.0f}s (max {self.max_orders})"
        if self.duplicate_seconds is not None:
            for t, s, q in self._sent:
                if s == symbol and q == quantity and now - t <= self.duplicate_seconds:
                    return f"duplicate: the same order {symbol} {quantity:+g} {now - t:.0f}s ago"
        if self.working_symbols is not None:
            try:
                working = {" ".join(str(w).split()) for w in self.working_symbols()}
            except Exception as e:
                return f"working orders unavailable ({e!r}): fail closed"
            if " ".join(symbol.split()) in working:
                return f"an order on {symbol} is still working"
        return None

    def record(self, symbol: str, quantity: float) -> None:
        self._sent.append((self.clock(), symbol, quantity))


class StreamingPriceProvider:
    """symbol -> PriceSnapshot from StreamingMarketDataService; never sizes an order with non-executable data."""

    def __init__(self, service, instrument_for: Callable[[str], str] = lambda s: f"STK:{s}",
                 clock: Callable[[], datetime] = _utcnow):
        self.service = service
        self.instrument_for = instrument_for
        self.clock = clock

    def __call__(self, symbol: str) -> Optional[PriceSnapshot]:
        instrument = self.instrument_for(symbol)
        now = self.clock()
        assessment = self.service.assess(instrument, now)
        obs = self.service.observation(instrument)
        if not assessment.executable or obs is None:
            reason = "; ".join(assessment.reasons) or assessment.usability.value
            return PriceSnapshot(None, None, unusable_reason=f"{assessment.usability.value}: {reason}")
        price = max(obs.bid, obs.ask)                     # the more expensive side: conservative for every limit
        as_of = obs.quote_time or obs.received_at
        return PriceSnapshot(price, as_of)


class IBKRAccountProvider:
    """AccountSnapshot of ONE account from IBTWSClient snapshots (account values + positions)."""

    def __init__(self, client, account: str, price_provider: Callable[[str], Optional[PriceSnapshot]],
                 multiplier_provider: Optional[Callable[[str], float]] = None,
                 key_for: Optional[Callable[[dict], str]] = None, timeout: float = 10.0):
        if not account:
            raise ValueError("IBKRAccountProvider needs the account id (several accounts may be visible)")
        self.client = client
        self.account = account
        self.price_provider = price_provider
        self.multiplier_provider = multiplier_provider
        self.key_for = key_for or (lambda p: p.get("symbol") if (p.get("secType") or "STK") in ("STK", "ETF")
                                   else " ".join(str(p.get("localSymbol") or "").split()))
        self.timeout = timeout

    def __call__(self) -> AccountSnapshot:
        if not self.client.request_account_values_snapshot(timeout=self.timeout):
            raise RuntimeError("account values incomplete (no accountSummaryEnd)")
        if not self.client.request_positions_snapshot(timeout=self.timeout):
            raise RuntimeError("positions incomplete (no positionEnd)")
        values = self.client.account_values_snapshot.get(self.account)
        if not values:
            raise RuntimeError(f"no account values for {self.account}")

        def number(tag: str, required: bool) -> Optional[float]:
            raw = values.get(tag)
            if raw is None:
                if required:
                    raise RuntimeError(f"account value {tag} missing for {self.account}")
                return None
            return float(raw[0])

        positions: Dict[str, float] = {}
        for p in self.client.positions_snapshot:
            if p.get("account") != self.account or not float(p.get("position") or 0):
                continue
            key = self.key_for(p)
            positions[key] = positions.get(key, 0.0) + float(p["position"])
        gross = net = 0.0
        for symbol, qty in positions.items():
            snap = self.price_provider(symbol)
            if snap is None or snap.price is None:
                raise RuntimeError(f"no price to value the {symbol} position"
                                   + (f" ({snap.unusable_reason})" if snap is not None and snap.unusable_reason else ""))
            mult = float(self.multiplier_provider(symbol)) if self.multiplier_provider else 1.0
            gross += abs(qty) * snap.price * mult
            net += qty * snap.price * mult
        return AccountSnapshot(cash=number("TotalCashValue", True), positions=positions, gross_exposure=gross,
                               net_exposure=net, net_liquidation=number("NetLiquidation", True),
                               buying_power=number("BuyingPower", False))


def cancel_working_orders(ledger, client, reason: str, logger=None) -> List[int]:
    """Emergency action (explicit, never automatic): ask the broker to cancel every working order of the ledger.
    Returns the internal order ids whose cancel was requested; statuses change when the broker confirms (D4)."""
    log = logger or logging.getLogger("cancel_working_orders")
    requested = []
    for bo in ledger.open_orders():
        if bo.broker_order_id is None or bo.cancel_requested_at is not None:
            continue
        try:
            client.cancel_order(int(bo.broker_order_id))
            ledger.request_cancel(bo.order_id)
            requested.append(bo.order_id)
            log.critical(f"cancel requested for order {bo.order_id} (broker {bo.broker_order_id}): {reason}")
        except Exception as e:
            log.critical(f"cancel of order {bo.order_id} (broker {bo.broker_order_id}) FAILED: {e!r}")
    return requested


def liquidate_all(portfolio_manager, data, tag: str = "liquidate_all") -> dict:
    """Emergency action (explicit, never automatic): target 0 for every instrument the strategy holds, through the
    normal set_holdings path (ledger, reconciler, recovery and the pre-trade gate all apply). Put the scope in
    REDUCE_ONLY first: the gate then lets these sells through and refuses anything that adds risk."""
    held = sorted(portfolio_manager._get_all_held_tickers())
    if not held:
        return {}
    return portfolio_manager.set_holdings({t: 0.0 for t in held}, data, tag=tag)
