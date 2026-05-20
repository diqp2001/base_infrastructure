from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor
from src.domain.entities.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHolding


class PortfolioValueFactor(PortfolioFactor):
    """
    Factor representing the total value of all company share holdings in a portfolio.
    
    This factor computes the aggregate value by summing all individual holding value factors
    within the portfolio. It represents the total monetary value of all company shares
    held in the portfolio.
    
    Total Portfolio Value = Sum of all (Holding Quantity × Share Price)
    """

    def __init__(
        self,
        name: str = "Portfolio  Value",
        group: str = "portfolio",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "portfolio_management",
        definition: Optional[str] = "Total value of all  holdings in portfolio",
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
"""
src/domain/entities/factor/finance/portfolio/portfolio_value_factor.py

PortfolioValueFactor domain entity - calculates portfolio value from holding values.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from decimal import Decimal

from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor


class PortfolioValueFactor(PortfolioFactor):
    """Domain entity representing a portfolio value factor that calculates total portfolio value."""

    def __init__(
        self,
        name: str,
        group: str = "value",
        subgroup: Optional[str] = "portfolio",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        if definition is None:
            definition = f"Portfolio value factor: {name}"
            
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

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        """
        Calculate portfolio value by summing all holding values.
        
        Args:
            dependencies: Dictionary containing holding value factors
            
        Returns:
            Total portfolio value as Decimal
        """
        try:
            total_value = Decimal('0.0')
            
            # Sum up all holding values from dependencies
            for dependency_name, dependency_value in dependencies.items():
                if isinstance(dependency_value, (int, float, Decimal)):
                    total_value += Decimal(str(dependency_value))
                elif hasattr(dependency_value, 'value'):
                    total_value += Decimal(str(dependency_value.value))
                    
            return total_value
            
        except Exception as e:
            print(f"Error calculating portfolio value: {e}")
            return Decimal('0.0')
