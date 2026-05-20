"""
Company Share Transaction Value Factor domain entity.

This factor represents the total value of a company share transaction,
calculated from order quantity and order price factors.
"""

from __future__ import annotations
from typing import List, Optional
from decimal import Decimal

from src.domain.entities.factor.factor_value import FactorValue
from ..holding.company_share_portfolio_holding_factor import CompanySharePortfolioHoldingFactor


class CompanyShareTransactionValueFactor(CompanySharePortfolioHoldingFactor):
    """
    Factor representing the total value of a company share transaction.
    
    This factor is computed by multiplying the order quantity factor 
    by the order price factor to get the total transaction value.
    
    Transaction Value = Order Quantity × Order Price
    """

    def __init__(
        self,
        name: str = "Company Share Transaction Value",
        group: str = "transaction",
        subgroup: Optional[str] = "value",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "order_management",
        definition: Optional[str] = "Total value of company share transaction (quantity × price)",
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

    def calculate(self, order_values: List[FactorValue]) -> Decimal:
        """
        Calculate transaction value by multiplying quantity and price.
        
        Args:
            order_values: List containing [quantity_factor_value, price_factor_value]
            
        Returns:
            Decimal: Total transaction value
        """
        if len(order_values) < 2:
            return Decimal('0')
            
        quantity_value = order_values[0].value if hasattr(order_values[0], 'value') else order_values[0]
        price_value = order_values[1].value if hasattr(order_values[1], 'value') else order_values[1]
        
        return Decimal(str(quantity_value)) * Decimal(str(price_value))