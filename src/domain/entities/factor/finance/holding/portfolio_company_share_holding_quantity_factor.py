from __future__ import annotations
from typing import Optional

from .portfolio_company_share_holding_factor import PortfolioCompanyShareHoldingFactor


class PortfolioCompanyShareHoldingQuantityFactor(PortfolioCompanyShareHoldingFactor):
    """
    Factor representing the number of shares held in a portfolio for a specific company share.
    
    This factor tracks the quantity/number of shares held, forming the basis for 
    value calculations when combined with price factors.
    """

    def __init__(
        self,
        name: str = "Portfolio Company Share Holding Quantity",
        group: str = "holding",
        subgroup: Optional[str] = "quantity",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Number of shares held in portfolio for specific company",
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