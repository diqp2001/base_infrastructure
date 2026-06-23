"""
CompanyShareVpt52w20dLagFactor - 52-week Volume Price Trend with 20-day lag.

VPT = volume * (close - start_close) / start_close
where close/volume are observed 20 trading days ago and start_close is 272 days ago
(20-day lag + 252 trading days = one year lookback).
"""

from __future__ import annotations
from typing import Optional
from .company_share_factor import CompanyShareFactor


class CompanyShareVpt52w20dLagFactor(CompanyShareFactor):
    """
    Volume Price Trend (VPT) over 52 weeks with a 20-day observation lag.

    calculate(volume, close, start_close):
        - volume: traded volume 20 days ago
        - close: closing price 20 days ago
        - start_close: closing price 272 days ago (52 weeks + 20-day lag)
    """

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(factor_id=factor_id, **kwargs)

    def calculate(
        self,
        volume: float,
        close: float,
        start_close: float,
    ) -> Optional[float]:
        """Return volume * (close - start_close) / start_close."""
        if volume is None or close is None or start_close is None:
            return None
        if start_close == 0:
            return None
        return volume * (close - start_close) / start_close
