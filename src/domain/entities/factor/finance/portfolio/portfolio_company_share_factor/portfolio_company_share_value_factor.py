from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from domain.entities.factor.finance.portfolio.portfolio_company_share_factor.portfolio_company_share_factor import PortfolioCompanyShareFactor
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding


class PortfolioCompanyShareValueFactor(PortfolioCompanyShareFactor):
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

    def calculate_portfolio_value(self, holdings: List[PortfolioCompanyShareHolding], quantities: List[Decimal]) -> Decimal:
        """
        Calculate the total portfolio value from a list of holdings and their corresponding quantities.
        
        Args:
            holdings: List of portfolio company share holdings
            quantities: List of corresponding quantities for each holding (must be same length as holdings)
            
        Returns:
            Total portfolio value (sum of all holding values)
            
        Raises:
            ValueError: If holdings and quantities lists have different lengths
                       or if any holding has no price information
        """
        if len(holdings) != len(quantities):
            raise ValueError("Holdings and quantities lists must have the same length")
            
        total_value = Decimal('0')
        
        for holding, quantity in zip(holdings, quantities):
            if holding.asset.price is None:
                raise ValueError(f"Holding {holding.id} has no price information")
                
            if quantity < 0:
                raise ValueError(f"Quantity for holding {holding.id} cannot be negative")
                
            # Convert price to Decimal for precise calculation
            price = Decimal(str(holding.asset.price))
            holding_value = quantity * price
            total_value += holding_value
            
        return total_value