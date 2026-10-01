from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CurrencyPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """Factor representing the total value of a CurrencyPortfolioHolding."""

    def __init__(
        self,
        name: str = "Currency Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of currency portfolio holding",
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
        return [
            DependencySpec(
                factor_type=CurrencyValueFactor,
                group="value",
                subgroup="asset",
                source="calculated",
            ),
            'Position',
        ]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        price_vals = dependencies.get('CurrencyValueFactor')
        quantity_raw = dependencies.get('Position')
        if not price_vals or quantity_raw is None:
            return None
        return Decimal(str(price_vals[0])) * Decimal(str(quantity_raw))
