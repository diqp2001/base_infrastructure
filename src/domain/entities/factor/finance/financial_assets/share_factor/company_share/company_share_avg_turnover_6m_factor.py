"""
CompanyShareAvgTurnover6mFactor - 6-month average daily share turnover.
"""

from __future__ import annotations
from typing import Optional, List
from .company_share_factor import CompanyShareFactor


class CompanyShareAvgTurnover6mFactor(CompanyShareFactor):
    """Average daily traded volume over the past 6 months (126 trading days)."""

    PERIOD = 126  # 6 calendar months ≈ 126 trading days

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(factor_id=factor_id, **kwargs)

    def calculate(self, volumes: List[float]) -> Optional[float]:
        """Return the arithmetic mean of the provided volume observations."""
        valid = [v for v in volumes if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)
