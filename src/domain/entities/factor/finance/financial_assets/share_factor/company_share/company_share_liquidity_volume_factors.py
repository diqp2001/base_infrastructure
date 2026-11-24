"""
CompanyShare liquidity and volume factors over several periods (added 2026-11-23, owner's choice: the S&P 500
cross-sectional momentum candidates). Daily bars only (close, volume, high, low through DependencySpecs, like
company_share_liquidity_factors); a period of N sessions reads the N (or N + 1 for returns) last closed bars.

    avg_dollar_volume_{5d,1m,3m,6m,12m}    mean(close x volume)
    amihud_illiquidity_{5d,1m,3m,6m,12m}   mean(|r| / (close x volume)) x 1e9      (Amihud 2002; r = close-to-close)
    volume_volatility_{5d,1m,3m,6m,12m}    std(volume) / mean(volume)            (coefficient of variation)
    relative_volume_{5d,1m,3m,6m}          mean(volume, N) / mean(volume, 252)
    volume_price_trend_{5d,1m,3m,6m,12m}   sum(volume x r) / sum(volume)         (volume-weighted mean return)
    avg_price_range_{5d,1m,3m}             mean((high - low) / close)
    turnover_{5d,1m,3m,6m,12m}             mean(volume) / shares outstanding      (true share turnover)

Turnover's share count is the balance sheet's commonStockSharesOutstanding (quarterly, point in time: the latest
count published at the value's time, read like every statement series; Eulerpool maps it from the XBRL tag
CommonStockSharesOutstanding, 2026-11-24).

No value when a window is incomplete, a volume / dollar volume is zero where it divides, or a close is not positive.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_factors import (  # noqa: E501
    _CompanyShareLiquidityFactor,
    _spec,
    _values,
)

YEAR = 252
SHARES_OUTSTANDING = "commonStockSharesOutstanding"


def _returns(closes: List[float]) -> List[Optional[float]]:
    return [(b - a) / a if a > 0 else None for a, b in zip(closes[:-1], closes[1:])]


class _PeriodFactor(_CompanyShareLiquidityFactor):
    PERIOD = 21


class _AvgDollarVolumeFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "liquidity", "turnover"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.PERIOD, "closes"), _spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes, volumes = _values(dependencies, "closes"), _values(dependencies, "volumes")
        if len(closes) < self.PERIOD or len(volumes) < self.PERIOD:
            return None
        pairs = list(zip(closes[-self.PERIOD:], volumes[-self.PERIOD:]))
        return sum(c * v for c, v in pairs) / self.PERIOD


class _AmihudIlliquidityFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "liquidity", "daily"
    SCALE = 1e9

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.PERIOD + 1, "closes"), _spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes, volumes = _values(dependencies, "closes"), _values(dependencies, "volumes")
        if len(closes) < self.PERIOD + 1 or len(volumes) < self.PERIOD:
            return None
        closes, volumes = closes[-(self.PERIOD + 1):], volumes[-self.PERIOD:]
        ratios = []
        for r, c, v in zip(_returns(closes), closes[1:], volumes):
            if r is None or c * v <= 0:
                return None
            ratios.append(abs(r) / (c * v))
        return sum(ratios) / len(ratios) * self.SCALE


class _VolumeVolatilityFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "volume", "turnover"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        volumes = _values(dependencies, "volumes")
        if len(volumes) < max(self.PERIOD, 2):
            return None
        window = volumes[-self.PERIOD:]
        mean = sum(window) / len(window)
        if mean <= 0:
            return None
        var = sum((v - mean) ** 2 for v in window) / (len(window) - 1)
        return math.sqrt(var) / mean


class _RelativeVolumeFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "volume", "turnover"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("volume", YEAR, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        volumes = _values(dependencies, "volumes")
        if len(volumes) < YEAR:
            return None
        year = sum(volumes[-YEAR:]) / YEAR
        if year <= 0:
            return None
        return (sum(volumes[-self.PERIOD:]) / self.PERIOD) / year


class _VolumePriceTrendFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "volume", "trend"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("close", self.PERIOD + 1, "closes"), _spec("volume", self.PERIOD, "volumes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        closes, volumes = _values(dependencies, "closes"), _values(dependencies, "volumes")
        if len(closes) < self.PERIOD + 1 or len(volumes) < self.PERIOD:
            return None
        returns, volumes = _returns(closes[-(self.PERIOD + 1):]), volumes[-self.PERIOD:]
        if any(r is None for r in returns):
            return None
        total = sum(volumes)
        if total <= 0:
            return None
        return sum(v * r for v, r in zip(volumes, returns)) / total


class _AvgPriceRangeFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "price", "range"

    @property
    def calculate_dependencies(self) -> list:
        return [_spec("high", self.PERIOD, "highs"), _spec("low", self.PERIOD, "lows"),
                _spec("close", self.PERIOD, "closes")]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        highs, lows, closes = (_values(dependencies, k) for k in ("highs", "lows", "closes"))
        if min(len(highs), len(lows), len(closes)) < self.PERIOD:
            return None
        bars = list(zip(highs[-self.PERIOD:], lows[-self.PERIOD:], closes[-self.PERIOD:]))
        if any(c <= 0 for _, _, c in bars):
            return None
        return sum((h - lo) / c for h, lo, c in bars) / self.PERIOD


class _TurnoverFactor(_PeriodFactor):
    DEFAULT_GROUP, DEFAULT_SUBGROUP = "volume", "turnover"

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (  # noqa: E501
            BALANCE_SHEET, GROUP, QUARTERLY, STATEMENT_SOURCES,
        )
        return [_spec("volume", self.PERIOD, "volumes"),
                DependencySpec(factor_type=CompanyShareFactor, group=GROUP, subgroup=BALANCE_SHEET,
                               frequency=QUARTERLY, name_in=[SHARES_OUTSTANDING], key="shares_outstanding",
                               source_in=list(STATEMENT_SOURCES))]

    def calculate(self, dependencies: Dict) -> Optional[float]:
        volumes, shares = _values(dependencies, "volumes"), _values(dependencies, "shares_outstanding")
        if len(volumes) < self.PERIOD or not shares or shares[-1] <= 0:
            return None
        return (sum(volumes[-self.PERIOD:]) / self.PERIOD) / shares[-1]


class CompanyShareAvgDollarVolume5DFactor(_AvgDollarVolumeFactor):
    PERIOD, DEFAULT_NAME = 5, "avg_dollar_volume_5d"
    DEFINITION = "1-week (5-session) average daily dollar volume (close x volume)"


class CompanyShareAvgDollarVolume1MFactor(_AvgDollarVolumeFactor):
    PERIOD, DEFAULT_NAME = 21, "avg_dollar_volume_1m"
    DEFINITION = "1-month (21-session) average daily dollar volume (close x volume)"


class CompanyShareAvgDollarVolume3MFactor(_AvgDollarVolumeFactor):
    PERIOD, DEFAULT_NAME = 63, "avg_dollar_volume_3m"
    DEFINITION = "3-month (63-session) average daily dollar volume (close x volume)"


class CompanyShareAvgDollarVolume6MFactor(_AvgDollarVolumeFactor):
    PERIOD, DEFAULT_NAME = 126, "avg_dollar_volume_6m"
    DEFINITION = "6-month (126-session) average daily dollar volume (close x volume)"


class CompanyShareAvgDollarVolume12MFactor(_AvgDollarVolumeFactor):
    PERIOD, DEFAULT_NAME = 252, "avg_dollar_volume_12m"
    DEFINITION = "12-month (252-session) average daily dollar volume (close x volume)"


class CompanyShareAmihudIlliquidity5DFactor(_AmihudIlliquidityFactor):
    PERIOD, DEFAULT_NAME = 5, "amihud_illiquidity_5d"
    DEFINITION = "1-week (5-session) Amihud illiquidity: mean of |daily return| / dollar volume, x 1e9"


class CompanyShareAmihudIlliquidity1MFactor(_AmihudIlliquidityFactor):
    PERIOD, DEFAULT_NAME = 21, "amihud_illiquidity_1m"
    DEFINITION = "1-month (21-session) Amihud illiquidity: mean of |daily return| / dollar volume, x 1e9"


class CompanyShareAmihudIlliquidity3MFactor(_AmihudIlliquidityFactor):
    PERIOD, DEFAULT_NAME = 63, "amihud_illiquidity_3m"
    DEFINITION = "3-month (63-session) Amihud illiquidity: mean of |daily return| / dollar volume, x 1e9"


class CompanyShareAmihudIlliquidity6MFactor(_AmihudIlliquidityFactor):
    PERIOD, DEFAULT_NAME = 126, "amihud_illiquidity_6m"
    DEFINITION = "6-month (126-session) Amihud illiquidity: mean of |daily return| / dollar volume, x 1e9"


class CompanyShareAmihudIlliquidity12MFactor(_AmihudIlliquidityFactor):
    PERIOD, DEFAULT_NAME = 252, "amihud_illiquidity_12m"
    DEFINITION = "12-month (252-session) Amihud illiquidity: mean of |daily return| / dollar volume, x 1e9"


class CompanyShareVolumeVolatility5DFactor(_VolumeVolatilityFactor):
    PERIOD, DEFAULT_NAME = 5, "volume_volatility_5d"
    DEFINITION = "1-week (5-session) volume volatility: standard deviation / mean of the daily volume"


class CompanyShareVolumeVolatility1MFactor(_VolumeVolatilityFactor):
    PERIOD, DEFAULT_NAME = 21, "volume_volatility_1m"
    DEFINITION = "1-month (21-session) volume volatility: standard deviation / mean of the daily volume"


class CompanyShareVolumeVolatility3MFactor(_VolumeVolatilityFactor):
    PERIOD, DEFAULT_NAME = 63, "volume_volatility_3m"
    DEFINITION = "3-month (63-session) volume volatility: standard deviation / mean of the daily volume"


class CompanyShareVolumeVolatility6MFactor(_VolumeVolatilityFactor):
    PERIOD, DEFAULT_NAME = 126, "volume_volatility_6m"
    DEFINITION = "6-month (126-session) volume volatility: standard deviation / mean of the daily volume"


class CompanyShareVolumeVolatility12MFactor(_VolumeVolatilityFactor):
    PERIOD, DEFAULT_NAME = 252, "volume_volatility_12m"
    DEFINITION = "12-month (252-session) volume volatility: standard deviation / mean of the daily volume"


class CompanyShareRelativeVolume5DFactor(_RelativeVolumeFactor):
    PERIOD, DEFAULT_NAME = 5, "relative_volume_5d"
    DEFINITION = "1-week (5-session) relative volume: mean daily volume over the period / over 12 months (252 sessions)"


class CompanyShareRelativeVolume1MFactor(_RelativeVolumeFactor):
    PERIOD, DEFAULT_NAME = 21, "relative_volume_1m"
    DEFINITION = "1-month (21-session) relative volume: mean daily volume over the period / over 12 months (252 sessions)"


class CompanyShareRelativeVolume3MFactor(_RelativeVolumeFactor):
    PERIOD, DEFAULT_NAME = 63, "relative_volume_3m"
    DEFINITION = "3-month (63-session) relative volume: mean daily volume over the period / over 12 months (252 sessions)"


class CompanyShareRelativeVolume6MFactor(_RelativeVolumeFactor):
    PERIOD, DEFAULT_NAME = 126, "relative_volume_6m"
    DEFINITION = "6-month (126-session) relative volume: mean daily volume over the period / over 12 months (252 sessions)"


class CompanyShareVolumePriceTrend5DFactor(_VolumePriceTrendFactor):
    PERIOD, DEFAULT_NAME = 5, "volume_price_trend_5d"
    DEFINITION = "1-week (5-session) volume price trend: volume-weighted mean daily return, sum(volume x return) / sum(volume)"


class CompanyShareVolumePriceTrend1MFactor(_VolumePriceTrendFactor):
    PERIOD, DEFAULT_NAME = 21, "volume_price_trend_1m"
    DEFINITION = "1-month (21-session) volume price trend: volume-weighted mean daily return, sum(volume x return) / sum(volume)"


class CompanyShareVolumePriceTrend3MFactor(_VolumePriceTrendFactor):
    PERIOD, DEFAULT_NAME = 63, "volume_price_trend_3m"
    DEFINITION = "3-month (63-session) volume price trend: volume-weighted mean daily return, sum(volume x return) / sum(volume)"


class CompanyShareVolumePriceTrend6MFactor(_VolumePriceTrendFactor):
    PERIOD, DEFAULT_NAME = 126, "volume_price_trend_6m"
    DEFINITION = "6-month (126-session) volume price trend: volume-weighted mean daily return, sum(volume x return) / sum(volume)"


class CompanyShareVolumePriceTrend12MFactor(_VolumePriceTrendFactor):
    PERIOD, DEFAULT_NAME = 252, "volume_price_trend_12m"
    DEFINITION = "12-month (252-session) volume price trend: volume-weighted mean daily return, sum(volume x return) / sum(volume)"


class CompanyShareAvgPriceRange5DFactor(_AvgPriceRangeFactor):
    PERIOD, DEFAULT_NAME = 5, "avg_price_range_5d"
    DEFINITION = "1-week (5-session) average daily price range: mean of (high - low) / close"


class CompanyShareAvgPriceRange1MFactor(_AvgPriceRangeFactor):
    PERIOD, DEFAULT_NAME = 21, "avg_price_range_1m"
    DEFINITION = "1-month (21-session) average daily price range: mean of (high - low) / close"


class CompanyShareAvgPriceRange3MFactor(_AvgPriceRangeFactor):
    PERIOD, DEFAULT_NAME = 63, "avg_price_range_3m"
    DEFINITION = "3-month (63-session) average daily price range: mean of (high - low) / close"


class CompanyShareTurnover5DFactor(_TurnoverFactor):
    PERIOD, DEFAULT_NAME = 5, "turnover_5d"
    DEFINITION = "1-week (5-session) share turnover: mean daily volume / shares outstanding (latest published count)"


class CompanyShareTurnover1MFactor(_TurnoverFactor):
    PERIOD, DEFAULT_NAME = 21, "turnover_1m"
    DEFINITION = "1-month (21-session) share turnover: mean daily volume / shares outstanding (latest published count)"


class CompanyShareTurnover3MFactor(_TurnoverFactor):
    PERIOD, DEFAULT_NAME = 63, "turnover_3m"
    DEFINITION = "3-month (63-session) share turnover: mean daily volume / shares outstanding (latest published count)"


class CompanyShareTurnover6MFactor(_TurnoverFactor):
    PERIOD, DEFAULT_NAME = 126, "turnover_6m"
    DEFINITION = "6-month (126-session) share turnover: mean daily volume / shares outstanding (latest published count)"


class CompanyShareTurnover12MFactor(_TurnoverFactor):
    PERIOD, DEFAULT_NAME = 252, "turnover_12m"
    DEFINITION = "12-month (252-session) share turnover: mean daily volume / shares outstanding (latest published count)"


LIQUIDITY_VOLUME_FACTOR_CLASSES = (
    CompanyShareAvgDollarVolume5DFactor,
    CompanyShareAvgDollarVolume1MFactor,
    CompanyShareAvgDollarVolume3MFactor,
    CompanyShareAvgDollarVolume6MFactor,
    CompanyShareAvgDollarVolume12MFactor,
    CompanyShareAmihudIlliquidity5DFactor,
    CompanyShareAmihudIlliquidity1MFactor,
    CompanyShareAmihudIlliquidity3MFactor,
    CompanyShareAmihudIlliquidity6MFactor,
    CompanyShareAmihudIlliquidity12MFactor,
    CompanyShareVolumeVolatility5DFactor,
    CompanyShareVolumeVolatility1MFactor,
    CompanyShareVolumeVolatility3MFactor,
    CompanyShareVolumeVolatility6MFactor,
    CompanyShareVolumeVolatility12MFactor,
    CompanyShareRelativeVolume5DFactor,
    CompanyShareRelativeVolume1MFactor,
    CompanyShareRelativeVolume3MFactor,
    CompanyShareRelativeVolume6MFactor,
    CompanyShareVolumePriceTrend5DFactor,
    CompanyShareVolumePriceTrend1MFactor,
    CompanyShareVolumePriceTrend3MFactor,
    CompanyShareVolumePriceTrend6MFactor,
    CompanyShareVolumePriceTrend12MFactor,
    CompanyShareAvgPriceRange5DFactor,
    CompanyShareAvgPriceRange1MFactor,
    CompanyShareAvgPriceRange3MFactor,
)

# turnover reads a statement series too: not computed from bars alone (kept out of the bar group)
TURNOVER_FACTOR_CLASSES = (
    CompanyShareTurnover5DFactor,
    CompanyShareTurnover1MFactor,
    CompanyShareTurnover3MFactor,
    CompanyShareTurnover6MFactor,
    CompanyShareTurnover12MFactor,
)
