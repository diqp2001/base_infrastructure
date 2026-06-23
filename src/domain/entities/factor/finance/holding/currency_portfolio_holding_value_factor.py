from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.factor_value import FactorValue


class CurrencyPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """Factor representing the total value of a CurrencyPortfolioHolding."""

    def __init__(
        self,
        name: str = "Currency Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of currency portfolio holding",
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    def calculate(self, positions_values: List[FactorValue]) -> Decimal:
        total_value = Decimal('0')
        for position_value in positions_values:
            total_value += position_value
        return total_value
