from __future__ import annotations

from datetime import date
from typing import List, Optional, TYPE_CHECKING

from src.domain.entities.entity import Entity

if TYPE_CHECKING:
    from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding


class Portfolio(Entity):
    """
    Pure identification Portfolio.

    Represents a basket / collection of underlying financial assets.
    The Portfolio acts as a container for any type of PortfolioHolding.
    Allocation, weights, risk, PnL, etc. live elsewhere (factors/services).
    """

    def __init__(
        self,
        id: Optional[int],
        name: str,
        start_date: date,
        end_date: Optional[date] = None,
        holdings: Optional[List['PortfolioHolding']] = None,
    ):
        super().__init__(id)
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.holdings = holdings or []

    def add_holding(self, holding: 'PortfolioHolding') -> None:
        if holding not in self.holdings:
            self.holdings.append(holding)

    def remove_holding(self, holding: 'PortfolioHolding') -> bool:
        if holding in self.holdings:
            self.holdings.remove(holding)
            return True
        return False

    def get_holdings_by_type(self, holding_type: str) -> List['PortfolioHolding']:
        return [h for h in self.holdings if h.__class__.__name__ == holding_type]

    def has_holdings(self) -> bool:
        return len(self.holdings) > 0

    def holding_count(self) -> int:
        return len(self.holdings)

    def __repr__(self) -> str:
        return f"Portfolio(id={self.id}, name='{self.name}', holdings={len(self.holdings)})"
