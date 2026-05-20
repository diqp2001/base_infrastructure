from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor
from src.domain.entities.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHolding


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
        name: str = "Portfolio Company Share Value",
        group: str = "portfolio",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of all company share holdings in portfolio",
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

    def calculate(self, holdings_values: List[FactorValue]) -> Decimal:
        """
        Calculate the total portfolio value by summing the values of all holdings. factor values of factor CompanySharePortfolioHoldingValueFactor
        """
        
            
        total_value = Decimal('0')
        
        for holding_value in holdings_values:
            
            total_value += holding_value
            
        return total_value