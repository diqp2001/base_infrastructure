"""
CompanyShare relative performance versus the SPY ETF (S&P 500): the share's return over a window minus SPY's
return over the same window (excess return), from daily closes.

    rel_return_spy_1d / _5d / _20d / _3m / _6m     windows of 1, 5, 20, 63 and 126 sessions

The SPY closes are read through a DependencySpec with ``entity_symbol='SPY'``: the resolution service resolves that
dependency on the SPY CompanyShare instead of the share itself. Both windows hold the N + 1 latest closed bars at
the target date.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)

BENCHMARK_SYMBOL = "SPY"


def _close_spec(bars: int, key: str, entity_symbol: Optional[str] = None):
    from src.domain.entities.factor.dependency_spec import DependencySpec
    return DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"],
                          source_not_in=["calculated"], lookback=bars, key=key, entity_symbol=entity_symbol)


def _closes(dependencies: dict, key: str) -> List[float]:
    raw = dependencies.get(key) or []
    raw = raw if isinstance(raw, list) else [raw]
    return [float(v) for v in raw if v is not None]


class _RelativeReturnVsSpyFactor(CompanyShareFactor):
    PERIOD = 1
    DEFAULT_NAME = ""

    def __init__(self, factor_id: Optional[int] = None, name: Optional[str] = None, group: Optional[str] = "return",
                 subgroup: Optional[str] = "daily", frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "numeric", source: Optional[str] = "calculated",
                 definition: Optional[str] = None, **kwargs):
        super().__init__(name=name or self.DEFAULT_NAME, group=group, subgroup=subgroup, frequency=frequency,
                         data_type=data_type, source=source, factor_id=factor_id,
                         definition=definition or (f"{self.PERIOD}-session return minus the {BENCHMARK_SYMBOL} "
                                                   f"return over the same sessions"), **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        return [_close_spec(self.PERIOD + 1, "closes"),
                _close_spec(self.PERIOD + 1, "benchmark_closes", entity_symbol=BENCHMARK_SYMBOL)]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        share, bench = _closes(dependencies, "closes"), _closes(dependencies, "benchmark_closes")
        n = self.PERIOD + 1
        if len(share) < n or len(bench) < n:
            return None
        share, bench = share[-n:], bench[-n:]
        if share[0] == 0 or bench[0] == 0:
            return None
        return (share[-1] / share[0] - 1.0) - (bench[-1] / bench[0] - 1.0)


class CompanyShareRelativeReturnVsSpy1DFactor(_RelativeReturnVsSpyFactor):
    PERIOD, DEFAULT_NAME = 1, "rel_return_spy_1d"


class CompanyShareRelativeReturnVsSpy5DFactor(_RelativeReturnVsSpyFactor):
    PERIOD, DEFAULT_NAME = 5, "rel_return_spy_5d"


class CompanyShareRelativeReturnVsSpy20DFactor(_RelativeReturnVsSpyFactor):
    PERIOD, DEFAULT_NAME = 20, "rel_return_spy_20d"


class CompanyShareRelativeReturnVsSpy3MFactor(_RelativeReturnVsSpyFactor):
    PERIOD, DEFAULT_NAME = 63, "rel_return_spy_3m"


class CompanyShareRelativeReturnVsSpy6MFactor(_RelativeReturnVsSpyFactor):
    PERIOD, DEFAULT_NAME = 126, "rel_return_spy_6m"


RELATIVE_PERFORMANCE_FACTOR_CLASSES = (
    CompanyShareRelativeReturnVsSpy1DFactor, CompanyShareRelativeReturnVsSpy5DFactor,
    CompanyShareRelativeReturnVsSpy20DFactor, CompanyShareRelativeReturnVsSpy3MFactor,
    CompanyShareRelativeReturnVsSpy6MFactor,
)
