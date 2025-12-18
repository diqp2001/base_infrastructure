from __future__ import annotations
from typing import Optional

from .portfolio_company_share_holding_factor import PortfolioCompanyShareHoldingFactor


class PortfolioCompanyShareHoldingValueFactor(PortfolioCompanyShareHoldingFactor):
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