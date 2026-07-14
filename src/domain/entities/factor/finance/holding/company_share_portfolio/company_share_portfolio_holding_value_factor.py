from __future__ import annotations
from typing import List, Optional, Dict, Any
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

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        """
        Calculate the total value of company share holdings in a portfolio.
        
        Args:
            dependencies: Dictionary containing:
                - 'company_share_price_factor': CompanySharePriceFactor (or CompanyShareMidPriceFactor)
                - 'position': Position providing quantity of shares
                
        Returns:
            Total value as Decimal (price × quantity)
        """
        try:
            # Get the company share price
            price_factor = dependencies.get('company_share_mid_price_factor', Decimal('0'))
            if hasattr(price_factor, 'value'):
                price = price_factor.value
            else:
                price = Decimal(str(price_factor))
            
            # Get the position quantity
            position = dependencies.get('position')
            quantity = Decimal('0')
            
            if position:
                if hasattr(position, 'quantity'):
                    quantity = Decimal(str(position.quantity))
                elif isinstance(position, (int, float, Decimal)):
                    quantity = Decimal(str(position))
                elif isinstance(position, dict) and 'quantity' in position:
                    quantity = Decimal(str(position['quantity']))
            
            total_value = price * quantity
            
            return total_value
            
        except Exception as e:
            print(f"Error calculating company share portfolio holding value: {e}")
            return Decimal('0.0')
    
    def get_dependencies(self) -> List[str]:
        """
        Define the dependencies for this factor calculation.
        
        Returns:
            List of dependency factor names
        """
        return [
            "company_share_mid_price_factor",  # CompanySharePriceFactor (using mid price)
            "position"  # Position providing quantity
        ]