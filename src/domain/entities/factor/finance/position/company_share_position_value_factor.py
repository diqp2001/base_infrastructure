"""
Company Share Position Value Factor domain entity.

This factor represents the total value of a company share position,
calculated from underlying transaction values.
"""

from __future__ import annotations
from typing import List, Optional
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from ..holding.company_share_portfolio.company_share_portfolio_holding_factor import CompanySharePortfolioHoldingFactor


class CompanySharePositionValueFactor(CompanySharePortfolioHoldingFactor):
    """
    Factor representing the total value of a company share position.
    
    This factor is computed by summing all transaction values that make up
    the position. Each transaction contributes to the overall position value.
    
    Position Value = Sum of all Transaction Values for this position
    """

    def __init__(
        self,
        name: str = "Company Share Position Value",
        group: str = "position",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "transaction_management",
        definition: Optional[str] = "Total value of company share position from transactions",
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

    def calculate(self, transaction_values: List[FactorValue]) -> Decimal:
        """
        Calculate position value by summing transaction values.
        
        Args:
            transaction_values: List of transaction value factor values
            
        Returns:
            Decimal: Total position value
        """
        total_value = Decimal('0')
        
        for transaction_value in transaction_values:
            total_value += transaction_value.value if hasattr(transaction_value, 'value') else transaction_value
            
        return total_value