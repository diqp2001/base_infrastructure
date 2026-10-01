from __future__ import annotations
from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.dependency_spec import DependencySpec


class CompanyShareOptionPortfolioPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """
    Factor representing the total value of a CompanyShareOptionPortfolio holding within a Portfolio.

    Value = CompanyShareOptionPortfolioValue (position is always 1 sub-portfolio)
    """

    def __init__(
        self,
        name: str = "Company Share Option Portfolio Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = '5m',
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of CompanyShareOptionPortfolio holding within Portfolio",
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
        vals = dependencies.get('CompanyShareOptionPortfolioValueFactor')
        if not vals:
            return None
        return sum(Decimal(str(v)) for v in vals if isinstance(v, (int, float, Decimal))) or None

    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_value_factor import CompanyShareOptionPortfolioValueFactor
        return [
            DependencySpec(
                factor_type=CompanyShareOptionPortfolioValueFactor,
                group="value",
                subgroup="value",
                source="calculated",
            ),
        ]

    def __repr__(self):
        return f"CompanyShareOptionPortfolioPortfolioHoldingValueFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"
