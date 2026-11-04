"""
Shared pre-trade gate (BI-022, P.05): attached to a broker, every order passes it before it is sent. Snapshots come
from the caller's providers; when a provider fails, the order is refused (fail closed).

    gate = PreTradeGate(RiskLimits(max_order_notional=50_000, max_position_quantity=500),
                        account_provider=lambda: AccountSnapshot(cash=..., positions=..., gross_exposure=...),
                        price_provider=lambda symbol: PriceSnapshot(price, as_of),
                        controls=TradingControlsService(repo), account="U123", strategy="CSM",   # P.05
                        throttle=OrderThrottle(max_orders=20, window_seconds=60))                 # P.05
    broker.attach_risk_gate(gate)

Order of the checks: trading controls (kill switch / disabled / reduce-only) -> order rate and duplicates -> book
currency (P.08.10: with a ``currency_provider``, an instrument whose contract currency is not the book's is refused
until multi-currency books exist) -> the risk limits (domain pre_trade_risk.check_order). An InteractiveBrokersBroker
sends nothing without a gate.
"""

import logging
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from src.domain.entities.finance.order.pre_trade_risk import (
    AccountSnapshot, OrderIntent, PriceSnapshot, RiskLimits, check_order,
)
from src.domain.entities.finance.order.trading_control import ControlMode, reduces_position


class PreTradeGate:

    def __init__(self, limits: RiskLimits, account_provider: Callable[[], AccountSnapshot],
                 price_provider: Callable[[str], Optional[PriceSnapshot]],
                 multiplier_provider: Optional[Callable[[str], float]] = None,
                 clock: Callable[[], datetime] = datetime.now, logger: Optional[logging.Logger] = None,
                 controls=None, account: Optional[str] = None, strategy: Optional[str] = None, throttle=None,
                 currency_provider: Optional[Callable[[str], Optional[str]]] = None, book_currency: str = "USD"):
        self.limits = limits
        self.account_provider = account_provider
        self.price_provider = price_provider
        self.multiplier_provider = multiplier_provider
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.controls = controls
        self.account = account
        self.strategy = strategy
        self.throttle = throttle
        self.currency_provider = currency_provider      # symbol -> currency of the contract the order uses, or None
        self.book_currency = book_currency.upper()
        self.rejections: List[Tuple[str, Tuple[str, ...]]] = []          # (symbol, reasons), for reporting

    @staticmethod
    def symbol_of(order) -> str:
        symbol = getattr(order, "symbol", "")
        return str(getattr(symbol, "value", None) or getattr(symbol, "ticker", None) or symbol)

    @staticmethod
    def signed_quantity(order) -> float:
        """Buy > 0, sell < 0. Engine orders keep a POSITIVE quantity and a SELL direction (P.06 paper finding: the
        gate judged every sell as a buy); a sign that contradicts the direction is refused."""
        quantity = float(order.quantity)
        direction = getattr(order, "direction", None)
        name = str(getattr(direction, "name", direction) or "").upper()
        if name.endswith("SELL"):
            return -abs(quantity)
        if name.endswith("BUY") and quantity < 0:
            raise ValueError(f"negative quantity {quantity} with direction BUY")
        return quantity

    def allows(self, order) -> bool:
        symbol = self.symbol_of(order)
        quantity = None
        try:
            quantity = self.signed_quantity(order)
            reasons = self._reasons(quantity, symbol)
        except Exception as e:                                           # no snapshot: fail closed
            reasons = (f"risk check failed: {e}",)
        if reasons:
            self.rejections.append((symbol, reasons))
            self.logger.warning(f"Pre-trade risk: order {getattr(order, 'id', '?')} {symbol} "
                                f"{quantity if quantity is not None else order.quantity} refused — {'; '.join(reasons)}")
            return False
        if self.throttle is not None:
            self.throttle.record(symbol, quantity)
        return True

    def allows_modification(self, order, previous_quantity: float) -> bool:
        """P.03.04: a working order changed to ``order.quantity`` (was ``previous_quantity``, both unsigned). Trading
        disabled refuses every change (cancel instead); a smaller or same-size order (e.g. a limit-price change)
        needs nothing else; a larger one is judged on the increase alone — reduce-only, currency and the risk limits
        — and never on the order rate / duplicate throttle (it is the same working order)."""
        symbol = self.symbol_of(order)
        try:
            new = self.signed_quantity(order)
            increase = abs(new) - abs(float(previous_quantity))
            reasons: Tuple[str, ...] = ()
            if self.controls is not None:
                mode, why = self.controls.mode_for(self.account, self.strategy)
                if mode is ControlMode.DISABLED:
                    reasons = tuple(f"trading disabled: {w}" for w in why) or ("trading disabled",)
            if not reasons and increase > 0:
                throttle, self.throttle = self.throttle, None
                try:
                    reasons = self._reasons(increase if new > 0 else -increase, symbol)
                finally:
                    self.throttle = throttle
        except Exception as e:
            reasons = (f"risk check failed: {e}",)
        if reasons:
            self.rejections.append((symbol, reasons))
            self.logger.warning(f"Pre-trade risk: modification of order {getattr(order, 'id', '?')} {symbol} to "
                                f"{order.quantity} refused — {'; '.join(reasons)}")
            return False
        return True

    def _reasons(self, quantity: float, symbol: str) -> Tuple[str, ...]:
        account = None
        if self.controls is not None:
            mode, why = self.controls.mode_for(self.account, self.strategy)
            if mode is ControlMode.DISABLED:
                return tuple(f"trading disabled: {w}" for w in why) or ("trading disabled",)
            if mode is ControlMode.REDUCE_ONLY:
                account = self.account_provider()
                if not reduces_position(account.positions.get(symbol, 0.0), quantity):
                    return tuple(f"reduce-only: order does not reduce the {symbol} position; {w}" for w in why)
        if self.throttle is not None:
            refusal = self.throttle.refusal(symbol, quantity)
            if refusal:
                return (refusal,)
        if self.currency_provider is not None:
            currency = self.currency_provider(symbol)
            if not currency or str(currency).upper() != self.book_currency:
                return (f"currency: {symbol} contract currency {currency or 'unknown (no contract found)'} is not the "
                        f"book's {self.book_currency} (multi-currency books are not supported)",)
        intent = OrderIntent(symbol, quantity,
                             float(self.multiplier_provider(symbol)) if self.multiplier_provider else 1.0)
        results = check_order(intent, self.price_provider(symbol), account or self.account_provider(), self.limits,
                              self.clock())
        return tuple(f"{r.rule}: {r.reason}" for r in results if not r.passed)
