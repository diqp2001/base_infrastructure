"""
Books option expiries, exercises and assignments (P.08.13, GA-C4) at session start, before the position
reconciliation, so the book matches the broker after an expiry. Detection is the pure domain
``finance.option_lifecycle.lifecycle_events``; this books each event in ONE database transaction:

    option leg       an internal FILLED order closing the option at 0 (no cash)
    underlying leg   exercised / assigned: an internal FILLED order moving the underlying at the strike (cash)

Internal order refs: ``ibkr:LIFECYCLE:<kind>:<option symbol>:<expiry>`` — booked once (``_create_or_get``). Used by
StartupRecovery(option_lifecycle=...) only for strategies that hold options; nothing changes for a stock strategy.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional

from src.domain.entities.finance.option_lifecycle import LifecycleEvent, lifecycle_events


class OptionLifecycleBooker:

    def __init__(self, trade_manager, portfolio_id: Callable[[], int], cash_portfolio_id: Callable[[], int],
                 broker: str = "ibkr", multiplier: float = 100.0, logger=None):
        self.trade_manager = trade_manager
        self.portfolio_id = portfolio_id
        self.cash_portfolio_id = cash_portfolio_id
        self.broker = broker
        self.multiplier = multiplier
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def apply(self, book: Dict[str, float], broker_positions: Dict[str, float], today: date,
              when: Optional[datetime] = None) -> List[LifecycleEvent]:
        """Detect and book; returns the events booked. An event that cannot be booked is rolled back alone and
        logged; it then shows as a position mismatch (blocking) for the operator."""
        when = when or datetime.combine(today, datetime.min.time())
        booked = []
        for event in lifecycle_events(book, broker_positions, today, self.multiplier):
            if self.trade_manager._book_atomically(lambda e=event: self._book(e, when)):
                booked.append(event)
                self.logger.warning(f"option lifecycle booked: {event.describe()}")
            else:
                self.logger.error(f"option lifecycle NOT booked: {event.describe()}")
        return booked

    def _book(self, event: LifecycleEvent, when: datetime) -> bool:
        legs = [(event.option.symbol, -event.option_quantity, 0.0)]
        if event.underlying_quantity:
            legs.append((event.option.underlying, event.underlying_quantity, event.price))
        for i, (symbol, signed_qty, price) in enumerate(legs):
            if not self._book_leg(event, i, symbol, signed_qty, price, when):
                return False
        return True

    def _book_leg(self, event: LifecycleEvent, leg: int, symbol: str, signed_qty: float, price: float,
                  when: datetime) -> bool:
        tm, portfolio_id = self.trade_manager, self.portfolio_id()
        holding_id = tm._resolve_holding_id(symbol, portfolio_id, when)
        account_id = tm._resolve_account_id(when)
        if holding_id is None or account_id is None:
            self.logger.error(f"{event.describe()}: {symbol} cannot be booked (holding={holding_id}, "
                              f"account={account_id})")
            return False
        ref = f"{self.broker}:LIFECYCLE:{event.kind}:{''.join(event.option.symbol.split())}:{event.option.expiry}:{leg}"
        side = "BUY" if signed_qty > 0 else "SELL"
        order = tm.order_repo._create_or_get(
            external_order_id=ref, portfolio_id=portfolio_id, order_type="MARKET", side=side,
            quantity=abs(signed_qty), created_at=when, status="FILLED", symbol=symbol, holding_id=holding_id,
            account_id=account_id, price=price, filled_quantity=abs(signed_qty), average_fill_price=price)
        if order is None:
            return False
        return tm.book_execution(order_id=order.id, ticker=symbol, signed_qty=signed_qty, price=price,
                                 portfolio_id=portfolio_id, cash_portfolio_id=self.cash_portfolio_id(), when=when,
                                 ref=ref)


def book_of(strategy_qty: Callable[[str], float], tickers: Iterable[str]) -> Dict[str, float]:
    """symbol -> book quantity for the strategy's tickers."""
    return {t: float(strategy_qty(t) or 0.0) for t in tickers}
