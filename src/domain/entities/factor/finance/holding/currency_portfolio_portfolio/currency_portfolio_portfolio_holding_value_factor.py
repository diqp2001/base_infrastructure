from __future__ import annotations
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CurrencyPortfolioPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """Factor representing the total value of a CurrencyPortfolio holding within a Portfolio."""

    def __init__(
        self,
        name: str = "Currency Portfolio Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = '1d',
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of CurrencyPortfolio holding within Portfolio",
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

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[Decimal]:
        vals = dependencies.get('CurrencyPortfolioValueFactor')
        if not vals:
            return None
        return sum(Decimal(str(v)) for v in vals if isinstance(v, (int, float, Decimal))) or None

    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.portfolio.currency_portfolio_value_factor import CurrencyPortfolioValueFactor
        return [
            DependencySpec(
                factor_type=CurrencyPortfolioValueFactor,
                group="value",
                subgroup="value",
            ),
        ]
