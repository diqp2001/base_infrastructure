"""
CompanyShareMonthlyPriceRangeFactor - 1-month price high minus 1-month price low.
"""

from __future__ import annotations
from typing import Optional
from .company_share_factor import CompanyShareFactor


class CompanyShareMonthlyPriceRangeFactor(CompanyShareFactor):
    """
    Difference between the recent high price and the price low from one month ago.
    Dependencies: high_price (lag=1d) and low_price (lag=21d).
    """

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(factor_id=factor_id, **kwargs)

    def calculate(self, high_price: float, low_price: float) -> Optional[float]:
        """Return high_price minus low_price."""
        if high_price is None or low_price is None:
            return None
        return high_price - low_price
