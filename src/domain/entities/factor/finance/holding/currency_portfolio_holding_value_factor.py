from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor


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

    @property
    def calculate_dependencies(self) -> List[str]:
        return ['CurrencyValueFactor', 'Position']

    def calculate(self, dependencies: dict) -> Decimal:
        currency_value = dependencies.get('CurrencyValueFactor')
        position_quantity = dependencies.get('Position')
        if currency_value is None:
            currency_value = Decimal('0')
        if position_quantity is None:
            position_quantity = Decimal('0')
        return Decimal(str(currency_value)) * Decimal(str(position_quantity))
