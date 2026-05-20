"""
Company Share Order Quantity Factor domain entity.

This factor represents the quantity (number of shares) in a company share order.
This is a base factor with no dependencies.
"""

from __future__ import annotations
from typing import Optional

from ..financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareOrderQuantityFactor(CompanyShareFactor):
    """
    Factor representing the quantity of shares in a company share order.
    
    This is a base factor that tracks the number of shares being ordered.
    It has no dependencies and is directly input from order data.
    """

    def __init__(
        self,
        name: str = "Company Share Order Quantity",
        group: str = "order",
        subgroup: Optional[str] = "quantity",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "order_system",
        definition: Optional[str] = "Number of shares in company share order",
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