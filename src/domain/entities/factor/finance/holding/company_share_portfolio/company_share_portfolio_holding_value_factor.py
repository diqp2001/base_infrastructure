from __future__ import annotations
from typing import List, Optional
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue

from .company_share_portfolio_holding_factor import CompanySharePortfolioHoldingFactor
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class CompanySharePortfolioHoldingValueFactor(CompanySharePortfolioHoldingFactor):
    """
    Factor representing the total value of a company share holding in a portfolio.
    
    This factor is computed by multiplying the quantity factor (number of shares) 
    by the company share price factor to get the total monetary value of the holding.
    
    Value = Quantity × Price
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Holding Value",
        group: str = "holding",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of company share holding (quantity × price)",
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

    def calculate(self, positions_values: List[FactorValue]) -> Decimal:
        """
        Calculate the total portfolio value by summing the values of all holdings. factor values of factor CompanySharePortfolioHoldingValueFactor
        """
        
            
        total_value = Decimal('0')
        
        for position_value in positions_values:
            
            total_value += position_value
            
        return total_value