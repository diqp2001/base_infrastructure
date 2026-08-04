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
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "calculated",
        definition: Optional[str] = "Total value of company share holding (quantity × price)",
        factor_id: Optional[int] = None,
    ):
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
        try:
            price = Decimal(str(dependencies.get('CompanyShareValueFactor', '0') or '0'))
            quantity = Decimal(str(dependencies.get('Position', '0') or '0'))
            return price * quantity
        except Exception as e:
            print(f"Error calculating company share portfolio holding value: {e}")
            return Decimal('0.0')

    @property
    def calculate_dependencies(self) -> List[str]:
        return ['CompanyShareValueFactor', 'Position']