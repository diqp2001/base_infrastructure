from __future__ import annotations
from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.dependency_spec import DependencySpec


class CompanySharePortfolioPortfolioHoldingValueFactor(PortfolioHoldingFactor):
    """
    Factor representing the total value of a CompanySharePortfolio holding within a Portfolio.
    
    This factor calculates the value of a company share portfolio when it's held as an asset 
    within another portfolio. The value depends on:
    - CompanySharePortfolioHoldingValueFactor (value of the underlying company share portfolio)
    - Position (quantity of the company share portfolio being held)
    
    Value = CompanySharePortfolioValue × Position.quantity
    """

    def __init__(
        self,
        name: str = "Company Share Portfolio Portfolio Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        frequency: Optional[str] = '5m',
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of CompanySharePortfolio holding within Portfolio",
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
        vals = dependencies.get('CompanySharePortfolioValueFactor')
        if not vals:
            return None
        return sum(Decimal(str(v)) for v in vals if isinstance(v, (int, float, Decimal))) or None

    @property
    def calculate_dependencies(self) -> List[DependencySpec]:
        from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor
        return [
            DependencySpec(
                factor_type=CompanySharePortfolioValueFactor,
                group="value",
                subgroup="value",
                source="calculated",
            ),
        ]

    def __repr__(self):
        return f"CompanySharePortfolioPortfolioHoldingValueFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"