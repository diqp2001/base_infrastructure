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

    def __init__(self, factor_id: Optional[int] = None, name: str = "monthly_price_range", group: str = "price",
                 subgroup: Optional[str] = "range", frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "numeric", source: Optional[str] = "calculated", **kwargs):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, factor_id=factor_id, **kwargs)

    @staticmethod
    def _spec(field, bars, key):
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        return DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=[field],
                              source_not_in=["calculated"], lookback=bars, key=key)

    @property
    def calculate_dependencies(self) -> list:
        return [self._spec("high", 1, "highs"), self._spec("low", 21, "lows")]

    def calculate(self, dependencies=None, *args, **kwargs):
        """Resolution service: the stored series; otherwise the explicit arguments of price_range()."""
        if isinstance(dependencies, dict):
            highs, lows = dependencies.get("highs") or [], dependencies.get("lows") or []
            if not highs or len(lows) < 21:
                return None
            return self.price_range(highs[-1], lows[0])        # high 1 bar ago, low 21 bars ago
        if dependencies is not None:
            args = (dependencies,) + args
        return self.price_range(*args, **kwargs)

    def price_range(self, high_price: float, low_price: float) -> Optional[float]:
        """Return high_price minus low_price."""
        if high_price is None or low_price is None:
            return None
        return high_price - low_price
