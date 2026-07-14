from __future__ import annotations
from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.finance.holding.portfolio_holding_factor import PortfolioHoldingFactor
from src.domain.entities.factor.factor_value import FactorValue


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
        subgroup: Optional[str] = "portfolio_value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of CompanySharePortfolio holding within Portfolio",
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
            portfolio_value = dependencies.get('CompanySharePortfolioValueFactor', Decimal('0'))
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
            print(f"Error calculating CompanySharePortfolio portfolio holding value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[str]:
        return [
            "CompanySharePortfolioValueFactor",
            "Position",
        ]

    def __repr__(self):
        return f"CompanySharePortfolioPortfolioHoldingValueFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"