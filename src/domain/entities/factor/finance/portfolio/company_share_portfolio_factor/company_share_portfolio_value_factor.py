from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


class CompanySharePortfolioValueFactor(CompanySharePortfolioFactor):
    """
    Factor representing the total value of all company share holdings in a portfolio.
    
    This factor computes the aggregate value by summing all individual holding value factors
    within the portfolio. It represents the total monetary value of all company shares
    held in the portfolio.
    
    Total Portfolio Value = Sum of all (Holding Quantity × Share Price)
    """

    def __init__(
        self,
        name: str = "Company Share Portfolio Value",
        group: str = "value",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of all company share holdings in portfolio",
        frequency: Optional[str] = '1d',
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
            for dependency_value in dependencies.values():
                if isinstance(dependency_value, (int, float, Decimal)):
                    total_value += Decimal(str(dependency_value))
                elif hasattr(dependency_value, 'value'):
                    total_value += Decimal(str(dependency_value.value))
            return total_value
        except Exception as e:
            print(f"Error calculating company share portfolio value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[str]:
        return ['CompanySharePortfolioHoldingValueFactor']