from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CompanyShareOptionPortfolioValueFactor(CompanyShareOptionPortfolioFactor):
    """
    Factor representing the total value of all company share option holdings in a portfolio.

    Total Portfolio Value = Sum of all (Holding Quantity × Option Price)
    """

    def __init__(
        self,
        name: str = "Company Share Option Portfolio Value",
        group: str = "value",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of all company share option holdings in portfolio",
        frequency: Optional[str] = '5m',
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            frequency=frequency,
            factor_id=factor_id,
        )

    def calculate(self, dependencies: dict) -> Decimal:
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
            print(f"Error calculating company share option portfolio value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.holding.company_share_option_portfolio.company_share_option_portfolio_holding_value_factor import CompanyShareOptionPortfolioHoldingValueFactor
        return [
            DependencySpec(
                factor_type=CompanyShareOptionPortfolioHoldingValueFactor,
                group="holding",
                subgroup="value",
                source="calculated",
            ),
        ]
