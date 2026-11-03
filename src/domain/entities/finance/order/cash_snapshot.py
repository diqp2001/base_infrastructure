"""
CashSnapshot (P.04.04 / P.06.13): the broker's cash and the strategy's book cash, taken together once per day by the
start-up recovery, and what the comparison booked. Append-only; pure, no I/O.

The account trades only this strategy (owner, 2026-11-02), so between two snapshots the broker's cash and the book
cash move by the same fills and commissions; what is left is financing (short-credit interest, borrow fees),
dividends, fees — or a deposit / withdrawal / a trade the books missed:

    difference = (broker_cash - previous.broker_cash) - (book_cash_before - previous.book_cash)

|difference| <= threshold   booked on the book cash as one FINANCING entry (``booked``)
|difference| >  threshold   not booked: a CASH_DRIFT discrepancy for the owner (``unexplained``)

``book_cash`` is stored AFTER the booking, so the next comparison starts from what the books now hold. The first
snapshot of an account is a baseline (no comparison).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CashSnapshot:
    account: str
    portfolio_id: int                              # the strategy's main portfolio (its CurrencyPortfolio holds the cash)
    taken_at: datetime                             # UTC naive
    broker_cash: float                             # IBKR TotalCashValue (base currency)
    book_cash: float                               # book cash after this snapshot's booking
    currency: str = "USD"
    broker_change: Optional[float] = None          # since the previous snapshot; None for a baseline
    book_change: Optional[float] = None
    booked: float = 0.0                            # FINANCING booked on the book cash (+ credit, - debit)
    unexplained: float = 0.0                       # difference above the threshold, left to the owner (CASH_DRIFT)
    transaction_ref: Optional[str] = None          # the FINANCING cash transaction
    note: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.account:
            raise ValueError("a cash snapshot needs its account")

    @property
    def is_baseline(self) -> bool:
        return self.broker_change is None

    @property
    def difference(self) -> Optional[float]:
        if self.broker_change is None or self.book_change is None:
            return None
        return round(self.broker_change - self.book_change, 2)


def cash_difference(previous: CashSnapshot, broker_cash: float, book_cash: float) -> tuple:
    """(broker change, book change, difference) since `previous`, to the cent."""
    broker_change = round(broker_cash - previous.broker_cash, 2)
    book_change = round(book_cash - previous.book_cash, 2)
    return broker_change, book_change, round(broker_change - book_change, 2)
