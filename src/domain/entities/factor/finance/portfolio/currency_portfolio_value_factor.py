from __future__ import annotations
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CurrencyPortfolioValueFactor(PortfolioFactor):
    """Factor representing the total value of a CurrencyPortfolio."""

    def __init__(
        self,
        name: str = "Currency Portfolio Value",
        group: str = "value",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        if definition is None:
            definition = f"Currency portfolio value factor: {name}"
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

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        try:
            total_value = Decimal('0.0')
            for key, vals in dependencies.items():
                if key in ('entity', 'target_date'):
                    continue
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, (int, float, Decimal)):
                            total_value += Decimal(str(v))
            return total_value
        except Exception as e:
            print(f"Error calculating currency portfolio value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.holding.currency_portfolio_holding_value_factor import CurrencyPortfolioHoldingValueFactor
        return [
            DependencySpec(
                factor_type=CurrencyPortfolioHoldingValueFactor,
                group="holding",
                subgroup="value",
                source="calculated",
            ),
        ]
