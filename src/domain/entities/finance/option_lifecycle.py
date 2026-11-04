"""
Option expiry, exercise and assignment from broker position changes (P.08.13, GA-C4). Pure: no database, no broker.

IBKR does not report an expiry or an exercise / assignment as an ordinary execution: after expiry the option position
is gone and, if it was exercised or assigned, the underlying position moved by quantity x multiplier at the strike.
At the next session start, for each option the book still holds whose expiry has passed and that the broker no longer
holds:

    long call  exercised   underlying + qty x multiplier at the strike      short call assigned  underlying - ...
    long put   exercised   underlying - qty x multiplier at the strike      short put  assigned  underlying + ...
    otherwise  expired worthless (closed at 0)

Exercised / assigned only when the broker's underlying position differs from the book's by at least that move, in
its direction (the broker is the authority: an ITM option can be left unexercised, an OTM one assigned). What no
event explains stays a position mismatch for the operator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

OCC_RE = re.compile(r"^(?P<root>[A-Z0-9.]{1,6})\s*(?P<date>\d{6})(?P<right>[CP])(?P<strike>\d{8})$")
EXPIRED, EXERCISED, ASSIGNED = "expired", "exercised", "assigned"
_EPS = 1e-9


@dataclass(frozen=True)
class OptionContract:
    symbol: str                 # OCC local symbol as booked, e.g. "SPY   261120C00450000"
    underlying: str
    expiry: date
    right: str                  # "C" / "P"
    strike: float

    @classmethod
    def parse(cls, symbol: str) -> Optional["OptionContract"]:
        """None when ``symbol`` is not an OCC option symbol (a stock)."""
        m = OCC_RE.match(" ".join(str(symbol).split()).replace(" ", "")) if symbol else None
        if m is None:
            return None
        return cls(symbol, m.group("root"), datetime.strptime(m.group("date"), "%y%m%d").date(), m.group("right"),
                   int(m.group("strike")) / 1000)


@dataclass(frozen=True)
class LifecycleEvent:
    kind: str                   # expired / exercised / assigned
    option: OptionContract
    option_quantity: float      # book quantity closed (signed as held: + long, - short)
    underlying_quantity: float  # signed change of the underlying position (0 when expired)

    @property
    def price(self) -> float:
        """Underlying leg price (the strike); the option leg closes at 0."""
        return self.option.strike

    def describe(self) -> str:
        text = f"{self.option.symbol} {self.option_quantity:+g} {self.kind}"
        if self.underlying_quantity:
            text += f": {self.option.underlying} {self.underlying_quantity:+g} @ {self.option.strike:g}"
        return text


def underlying_move(option: OptionContract, quantity: float, multiplier: float = 100.0) -> float:
    """Signed underlying change if ``quantity`` (signed) of ``option`` is exercised (long) or assigned (short)."""
    direction = 1.0 if option.right == "C" else -1.0
    return direction * quantity * multiplier


def lifecycle_events(book: Dict[str, float], broker: Dict[str, float], today: date,
                     multiplier: float = 100.0) -> List[LifecycleEvent]:
    """Events for the book's options expired before ``today`` (expiry < today) that the broker no longer holds.
    ``book`` / ``broker``: symbol -> signed quantity (stocks and options); broker keys compared without spaces."""
    def norm(s: str) -> str:
        return "".join(str(s).split())
    broker_n = {norm(k): float(v or 0.0) for k, v in broker.items()}
    book_n = {norm(k): float(v or 0.0) for k, v in book.items()}
    unexplained: Dict[str, float] = {}        # underlying -> broker - book, consumed by exercises / assignments
    events = []
    for symbol in sorted(book):
        qty = float(book[symbol] or 0.0)
        option = OptionContract.parse(symbol)
        if option is None or abs(qty) < _EPS or option.expiry >= today or abs(broker_n.get(norm(symbol), 0.0)) > _EPS:
            continue
        under = norm(option.underlying)
        if under not in unexplained:
            unexplained[under] = broker_n.get(under, 0.0) - book_n.get(under, 0.0)
        move = underlying_move(option, qty, multiplier)
        left = unexplained[under]
        if left * move > 0 and abs(left) + _EPS >= abs(move):
            unexplained[under] = left - move
            events.append(LifecycleEvent(EXERCISED if qty > 0 else ASSIGNED, option, qty, move))
        else:
            events.append(LifecycleEvent(EXPIRED, option, qty, 0.0))
    return events


def book_after(book: Dict[str, float], events: Iterable[LifecycleEvent]) -> Dict[str, float]:
    """The book once the events are booked (options closed, underlyings moved)."""
    out = dict(book)
    for e in events:
        out[e.option.symbol] = out.get(e.option.symbol, 0.0) - e.option_quantity
        if e.underlying_quantity:
            out[e.option.underlying] = out.get(e.option.underlying, 0.0) + e.underlying_quantity
    return {k: v for k, v in out.items() if abs(v) > _EPS}
