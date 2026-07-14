from __future__ import annotations
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor


class CurrencyPortfolioPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """Factor representing the total value of a CurrencyPortfolio holding within a Portfolio."""

    def __init__(
        self,
        name: str = "Currency Portfolio Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "portfolio_value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of CurrencyPortfolio holding within Portfolio",
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

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        try:
            portfolio_value = dependencies.get('CurrencyPortfolioValueFactor', Decimal('0'))
            if hasattr(portfolio_value, 'value'):
                portfolio_value = portfolio_value.value
            portfolio_value = Decimal(str(portfolio_value))

            position = dependencies.get('Position')
            quantity = Decimal('1')
            if position:
                if hasattr(position, 'quantity'):
                    quantity = Decimal(str(position.quantity))
                elif isinstance(position, (int, float, Decimal)):
                    quantity = Decimal(str(position))
                elif isinstance(position, dict) and 'quantity' in position:
                    quantity = Decimal(str(position['quantity']))

            return portfolio_value * quantity
        except Exception as e:
            print(f"Error calculating CurrencyPortfolio portfolio holding value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[str]:
        return [
            "CurrencyPortfolioValueFactor",
            "Position",
        ]
