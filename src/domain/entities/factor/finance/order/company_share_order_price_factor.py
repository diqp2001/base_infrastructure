"""
Company Share Order Price Factor domain entity.

This factor represents the price per share in a company share order.
This is a base factor with no dependencies.
"""

from __future__ import annotations
from typing import Optional

from ..financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareOrderPriceFactor(CompanyShareFactor):
    """
    Factor representing the price per share in a company share order.
    
    This is a base factor that tracks the price per share being ordered.
    It has no dependencies and is directly input from order data.
    """

    def __init__(
        self,
        name: str = "Company Share Order Price",
        group: str = "order",
        subgroup: Optional[str] = "price",
        data_type: Optional[str] = "decimal",
        source: Optional[str] = "order_system",
        definition: Optional[str] = "Price per share in company share order",
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