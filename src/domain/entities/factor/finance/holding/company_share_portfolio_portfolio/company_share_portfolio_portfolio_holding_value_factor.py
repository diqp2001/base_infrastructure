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
        """
        Calculate the total value of a CompanySharePortfolio holding within a Portfolio.
        
        Args:
            dependencies: Dictionary containing:
                - 'company_share_portfolio_value': CompanySharePortfolioHoldingValueFactor result
                - 'position': Position providing quantity
                
        Returns:
            Total value as Decimal (portfolio_value × quantity)
        """
        try:
            # Get the underlying CompanySharePortfolio value
            portfolio_value = dependencies.get('company_share_portfolio_value', Decimal('0'))
            if hasattr(portfolio_value, 'value'):
                portfolio_value = portfolio_value.value
            portfolio_value = Decimal(str(portfolio_value))
            
            # Get the position quantity  
            position = dependencies.get('position')
            quantity = Decimal('1')  # Default quantity
            
            if position:
                if hasattr(position, 'quantity'):
                    quantity = Decimal(str(position.quantity))
                elif isinstance(position, (int, float, Decimal)):
                    quantity = Decimal(str(position))
                elif isinstance(position, dict) and 'quantity' in position:
                    quantity = Decimal(str(position['quantity']))
            
            total_value = portfolio_value * quantity
            
            return total_value
            
        except Exception as e:
            print(f"Error calculating CompanySharePortfolio portfolio holding value: {e}")
            return Decimal('0.0')

    def get_dependencies(self) -> List[str]:
        """
        Define the dependencies for this factor calculation.
        
        Returns:
            List of dependency factor names
        """
        return [
            "company_share_portfolio_holding_value_factor",  # CompanySharePortfolioHoldingValueFactor
            "position"  # Position providing quantity
        ]

    def __repr__(self):
        return f"CompanySharePortfolioPortfolioHoldingValueFactor(name={self.name}, group={self.group}, subgroup={self.subgroup})"