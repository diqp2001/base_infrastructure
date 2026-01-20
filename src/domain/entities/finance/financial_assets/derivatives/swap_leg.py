"""
SwapLeg entity for swap leg components.
"""

from typing import Optional
from datetime import date
from decimal import Decimal


class SwapLeg:
    """
    SwapLeg entity representing one leg of a swap contract.
    Contains currency and underlying asset references as IDs.
    """
    def __init__(
            self,
            id: Optional[int],
            currency_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            swap_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
        ):

        self.id = id
        self.currency_id = currency_id
        self.underlying_asset_id = underlying_asset_id
        self.swap_id = swap_id
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"<SwapLeg(id={self.id}, currency_id={self.currency_id}, underlying_asset_id={self.underlying_asset_id}, swap_id={self.swap_id})>"