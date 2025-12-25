from __future__ import annotations
from typing import Optional
from decimal import Decimal

from .portfolio_company_share_holding_factor import PortfolioCompanyShareHoldingFactor
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


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

    def calculate_value(self, company_share: CompanyShare, quantity: Decimal) -> Decimal:
        """
        Calculate the total value of a holding given a company share and quantity.
        
        Args:
            company_share: The company share object containing price information
            quantity: Number of shares held (as Decimal for precision)
            
        Returns:
            Total value of the holding (quantity × current price)
            
        Raises:
            ValueError: If company share price is None or quantity is negative
        """
        if company_share.price is None:
            raise ValueError("Company share price cannot be None")
            
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
            
        # Convert price to Decimal for precise calculation
        price = Decimal(str(company_share.price))
        
        return quantity * price