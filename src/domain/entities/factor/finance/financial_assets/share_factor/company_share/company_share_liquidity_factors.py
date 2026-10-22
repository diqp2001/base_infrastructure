"""
CompanyShare liquidity, volume-trend and return-extreme factors (daily bars).

    avg_turnover_{1..5}m   mean daily traded volume over 21 x k sessions (avg_turnover_6m: CompanyShareAvgTurnover6mFactor)
    share_turnover         traded volume of the last closed session
    vpt_16w_20d_lag        volume 20 sessions ago x return from 100 to 20 sessions ago (16 weeks = 80 sessions,
                           20-session lag; the formula of CompanyShareVpt52w20dLagFactor)
    max_daily_return_6m    largest daily close-to-close return of the last 126 sessions
    min_return_120d        smallest daily close-to-close return of the last 120 sessions

Share turnover is measured as traded volume (shares), the convention of CompanyShareAvgTurnover6mFactor: no shares
outstanding are stored, so volume / shares outstanding cannot be formed.

Each factor reads the raw daily series it needs through DependencySpecs (``key`` = name of the list in
``calculate``'s dependencies), ``lookback`` = number of closed bars ending at the target date.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)


def _spec(field: str, bars: int, key: str):
    from src.domain.entities.factor.dependency_spec import DependencySpec
    return DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=[field],
                          source_not_in=["calculated"], lookback=bars, key=key)


def _values(dependencies: dict, key: str) -> List[float]:
    raw = dependencies.get(key) or []
    raw = raw if isinstance(raw, list) else [raw]
    return [float(v) for v in raw if v is not None]


def _daily_returns(closes: List[float]) -> List[float]:
    return [(b - a) / a for a, b in zip(closes[:-1], closes[1:]) if a]


class _CompanyShareLiquidityFactor(CompanyShareFactor):
    DEFAULT_NAME = ""
    DEFAULT_GROUP = "volume"
    DEFAULT_SUBGROUP = "turnover"
    DEFINITION = ""

    def __init__(self, factor_id: Optional[int] = None, name: Optional[str] = None, group: Optional[str] = None,
                 subgroup: Optional[str] = None, frequency: Optional[str] = "1d",
                 data_type: Optional[str] = "numeric", source: Optional[str] = "calculated",
                 definition: Optional[str] = None, **kwargs):
        super().__init__(name=name or self.DEFAULT_NAME, group=group or self.DEFAULT_GROUP,
                         subgroup=subgroup or self.DEFAULT_SUBGROUP, frequency=frequency, data_type=data_type,
                         source=source, definition=definition or self.DEFINITION, factor_id=factor_id, **kwargs)


# ── Average share turnover (traded volume) ────────────────────────────────────

class _AvgTurnoverFactor(_CompanyShareLiquidityFactor):
    PERIOD = 21

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        volumes = _values(dependencies, "volumes")
        if len(volumes) < self.PERIOD:
            return None
        return sum(volumes[-self.PERIOD:]) / self.PERIOD


class CompanyShareAvgTurnover1mFactor(_AvgTurnoverFactor):
    PERIOD, DEFAULT_NAME = 21, "avg_turnover_1m"
    DEFINITION = "1-month (21-session) average daily share turnover (traded volume)"


class CompanyShareAvgTurnover2mFactor(_AvgTurnoverFactor):
    PERIOD, DEFAULT_NAME = 42, "avg_turnover_2m"
    DEFINITION = "2-month (42-session) average daily share turnover (traded volume)"


class CompanyShareAvgTurnover3mFactor(_AvgTurnoverFactor):
    PERIOD, DEFAULT_NAME = 63, "avg_turnover_3m"
    DEFINITION = "3-month (63-session) average daily share turnover (traded volume)"


class CompanyShareAvgTurnover4mFactor(_AvgTurnoverFactor):
    PERIOD, DEFAULT_NAME = 84, "avg_turnover_4m"
    DEFINITION = "4-month (84-session) average daily share turnover (traded volume)"


class CompanyShareAvgTurnover5mFactor(_AvgTurnoverFactor):
    PERIOD, DEFAULT_NAME = 105, "avg_turnover_5m"
    DEFINITION = "5-month (105-session) average daily share turnover (traded volume)"


class CompanyShareTurnoverFactor(_CompanyShareLiquidityFactor):
    DEFAULT_NAME = "share_turnover"
    DEFINITION = "Daily share turnover: traded volume of the last closed session"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("volume", 1, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        volumes = _values(dependencies, "volumes")
        return volumes[-1] if volumes else None


# ── Volume price trend ────────────────────────────────────────────────────────

class CompanyShareVpt16w20dLagFactor(_CompanyShareLiquidityFactor):
    """VPT over 16 weeks (80 sessions) observed with a 20-session lag."""
    DEFAULT_NAME, DEFAULT_SUBGROUP = "vpt_16w_20d_lag", "trend"
    DEFINITION = "16-week volume price trend with 20-day lag: volume(t-20) x (close(t-20) - close(t-100)) / close(t-100)"
    WINDOW, LAG = 80, 20

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.WINDOW + self.LAG + 1, "closes"), _spec("volume", self.LAG + 1, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes, volumes = _values(dependencies, "closes"), _values(dependencies, "volumes")
        if len(closes) < self.WINDOW + self.LAG + 1 or len(volumes) < self.LAG + 1:
            return None
        start, close, volume = closes[0], closes[-(self.LAG + 1)], volumes[0]
        if start == 0:
            return None
        return volume * (close - start) / start


# ── Return extremes ───────────────────────────────────────────────────────────

class CompanyShareMaxDailyReturn6mFactor(_CompanyShareLiquidityFactor):
    DEFAULT_NAME, DEFAULT_GROUP, DEFAULT_SUBGROUP = "max_daily_return_6m", "return", "daily"
    DEFINITION = "Largest daily close-to-close return over the past 6 months (126 sessions)"
    PERIOD = 126

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.PERIOD + 1, "closes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes = _values(dependencies, "closes")
        if len(closes) < self.PERIOD + 1:
            return None
        returns = _daily_returns(closes[-(self.PERIOD + 1):])
        return max(returns) if returns else None


class CompanyShareMinReturn120dFactor(_CompanyShareLiquidityFactor):
    DEFAULT_NAME, DEFAULT_GROUP, DEFAULT_SUBGROUP = "min_return_120d", "return", "daily"
    DEFINITION = "Smallest daily close-to-close return over the past 120 sessions"
    PERIOD = 120

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.PERIOD + 1, "closes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes = _values(dependencies, "closes")
        if len(closes) < self.PERIOD + 1:
            return None
        returns = _daily_returns(closes[-(self.PERIOD + 1):])
        return min(returns) if returns else None


LIQUIDITY_FACTOR_CLASSES = (
    CompanyShareAvgTurnover1mFactor, CompanyShareAvgTurnover2mFactor, CompanyShareAvgTurnover3mFactor,
    CompanyShareAvgTurnover4mFactor, CompanyShareAvgTurnover5mFactor, CompanyShareTurnoverFactor,
    CompanyShareVpt16w20dLagFactor, CompanyShareMaxDailyReturn6mFactor, CompanyShareMinReturn120dFactor,
)
