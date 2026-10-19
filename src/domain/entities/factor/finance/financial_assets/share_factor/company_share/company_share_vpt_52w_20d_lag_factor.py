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

    def __init__(self, factor_id: Optional[int] = None, name: str = "vpt_52w_20d_lag", group: str = "volume",
                 subgroup: Optional[str] = "trend", frequency: Optional[str] = "1d",
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
        return [self._spec("close", 273, "closes"), self._spec("volume", 21, "volumes")]

    def calculate(self, dependencies=None, *args, **kwargs):
        """Resolution service: the stored series; otherwise the explicit arguments of vpt()."""
        if isinstance(dependencies, dict):
            closes, volumes = dependencies.get("closes") or [], dependencies.get("volumes") or []
            if len(closes) < 273 or len(volumes) < 21:
                return None
            # 20 bars ago: volume and close; 272 bars ago: start close (52 weeks + 20 days)
            return self.vpt(volumes[0], closes[-21], closes[0])
        if dependencies is not None:
            args = (dependencies,) + args
        return self.vpt(*args, **kwargs)

    def vpt(
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
