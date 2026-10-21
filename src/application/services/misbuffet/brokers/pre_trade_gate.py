"""
Shared pre-trade gate (BI-022): attached to a broker, every order passes `check_order` (domain pre_trade_risk)
before it is sent. Snapshots come from the caller's providers; when a provider fails, the order is refused.

    gate = PreTradeGate(RiskLimits(max_order_notional=50_000, max_position_quantity=500),
                        account_provider=lambda: AccountSnapshot(cash=..., positions=..., gross_exposure=...),
                        price_provider=lambda symbol: PriceSnapshot(price, as_of))
    broker.attach_risk_gate(gate)
"""

import logging
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from src.domain.entities.finance.order.pre_trade_risk import (
    AccountSnapshot, OrderIntent, PriceSnapshot, RiskLimits, check_order,
)


class PreTradeGate:

    def __init__(self, limits: RiskLimits, account_provider: Callable[[], AccountSnapshot],
                 price_provider: Callable[[str], Optional[PriceSnapshot]],
                 multiplier_provider: Optional[Callable[[str], float]] = None,
                 clock: Callable[[], datetime] = datetime.now, logger: Optional[logging.Logger] = None):
        self.limits = limits
        self.account_provider = account_provider
        self.price_provider = price_provider
        self.multiplier_provider = multiplier_provider
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.rejections: List[Tuple[str, Tuple[str, ...]]] = []          # (symbol, reasons), for reporting

    @staticmethod
    def symbol_of(order) -> str:
        symbol = getattr(order, "symbol", "")
        return str(getattr(symbol, "value", None) or getattr(symbol, "ticker", None) or symbol)

    def allows(self, order) -> bool:
        symbol = self.symbol_of(order)
        try:
            intent = OrderIntent(symbol, float(order.quantity),
                                 float(self.multiplier_provider(symbol)) if self.multiplier_provider else 1.0)
            results = check_order(intent, self.price_provider(symbol), self.account_provider(), self.limits,
                                  self.clock())
            reasons = tuple(f"{r.rule}: {r.reason}" for r in results if not r.passed)
        except Exception as e:                                           # no snapshot: fail closed
            reasons = (f"risk check failed: {e}",)
        if reasons:
            self.rejections.append((symbol, reasons))
            self.logger.warning(f"Pre-trade risk: order {getattr(order, 'id', '?')} {symbol} {order.quantity} "
                                f"refused — {'; '.join(reasons)}")
            return False
        return True
