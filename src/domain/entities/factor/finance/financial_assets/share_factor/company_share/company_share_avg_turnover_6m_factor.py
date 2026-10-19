"""
CompanyShareAvgTurnover6mFactor - 6-month average daily share turnover.
"""

from __future__ import annotations
from typing import Optional, List
from .company_share_factor import CompanyShareFactor


class CompanyShareAvgTurnover6mFactor(CompanyShareFactor):
    """Average daily traded volume over the past 6 months (126 trading days)."""

    PERIOD = 126  # 6 calendar months ≈ 126 trading days

    def __init__(self, factor_id: Optional[int] = None, name: str = "avg_turnover_6m", group: str = "volume",
                 subgroup: Optional[str] = "turnover", frequency: Optional[str] = "1d",
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
        return [self._spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies=None, *args, **kwargs):
        """Resolution service: the stored series; otherwise the explicit arguments of average()."""
        if isinstance(dependencies, dict):
            volumes = dependencies.get("volumes") or []
            return self.average(volumes) if len(volumes) == self.PERIOD else None
        if dependencies is not None:
            args = (dependencies,) + args
        return self.average(*args, **kwargs)

    def average(self, volumes: List[float]) -> Optional[float]:
        """Return the arithmetic mean of the provided volume observations."""
        valid = [v for v in volumes if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)
