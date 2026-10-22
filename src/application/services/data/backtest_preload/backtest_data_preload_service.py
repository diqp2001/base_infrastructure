"""
BacktestDataPreloadService — loads, BEFORE a backtest starts, every bar series the backtest will read, so that the
engine and the trading cycle find the data locally at each step and never wait on IBKR during the run.

    service = BacktestDataPreloadService(market_data_service, log=progress.log)
    report = service.preload([PreloadSeries(CompanyShare, "JPM", "TRADES", "10 mins"), ...],
                             start="2026-09-15", end="2026-10-09 16:00")

For each series:
  1. the entity is created / found through the engine's own path (MarketDataService._get_entity_by_ticker);
  2. ONE import covering ``start`` .. now goes through the engine's own import path
     (MarketDataService._get_point_in_time_data -> IBKR repositories -> factor_values), so the stored series are
     exactly those the engine reads (subgroup = whatToShow, frequency = bar size);
  3. the stored bars are compared with the bars the exchange was open for (NYSE calendar) — the report says what
     is missing;
  4. every raw bar factor of the entity (any whatToShow, any frequency) is registered as loaded over [start, end]
     (preloaded_coverage): inside that window the resolver never asks IBKR for this entity's raw data again — a
     missing bar gets the latest closed stored bar, or nothing.

Nothing here changes how the engine or the backtest run; it only makes sure the data is already there.
IBKR constraint: requests must end within the last 6 months, so every import ends now with a duration reaching
back to ``start``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import pandas as pd

from src.application.services.data.entities.factor import preloaded_coverage

RAW_FIELDS = ("open", "high", "low", "close", "volume")


@dataclass
class PreloadSeries:
    entity_class: type
    symbol: str
    what_to_show: str = "TRADES"
    bar_size_setting: str = "1 day"


@dataclass
class PreloadResult:
    symbol: str
    what_to_show: str
    bar_size_setting: str
    entity_id: Optional[int] = None
    imported: bool = False
    expected_bars: int = 0
    stored_bars: int = 0
    first_bar: Optional[str] = None
    last_bar: Optional[str] = None
    registered_factors: List[int] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def coverage_pct(self) -> float:
        return 100.0 * self.stored_bars / self.expected_bars if self.expected_bars else float("nan")


def import_duration(start, end, bar_size_setting: str) -> str:
    """IBKR duration string reaching from ``start`` to ``end``: years for daily bars, weeks for intraday bars."""
    days = max(1, (pd.Timestamp(end) - pd.Timestamp(start)).days)
    if "day" in bar_size_setting or "week" in bar_size_setting or "month" in bar_size_setting:
        return f"{max(1, math.ceil(days / 365.25))} Y"
    return f"{max(1, math.ceil(days / 7))} W"


def bar_minutes_of(bar_size_setting: str) -> Optional[int]:
    """10 for '10 mins', 60 for '1 hour', None for daily and longer bars."""
    from src.domain.entities.factor.factor import Factor
    seconds = Factor.frequency_seconds(Factor.bar_size_to_frequency(bar_size_setting))
    if not seconds or seconds >= 86400:
        return None
    return int(seconds // 60)


class BacktestDataPreloadService:

    def __init__(self, market_data_service, log: Optional[Callable[[str], None]] = None):
        self.market_data_service = market_data_service
        self.factory = market_data_service.entity_service.repository_factory
        self.log = log or logging.getLogger(self.__class__.__name__).info

    # ------------------------------------------------------------------

    def preload(self, series: List[PreloadSeries], start, end, register: bool = True) -> List[PreloadResult]:
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        request_end = pd.Timestamp.now().floor("min")
        results = []
        for spec in series:
            result = PreloadResult(spec.symbol, spec.what_to_show, spec.bar_size_setting)
            try:
                entity = self.market_data_service._get_entity_by_ticker(spec.symbol, spec.entity_class)
                if entity is None or getattr(entity, "id", None) is None:
                    result.error = f"no {spec.entity_class.__name__} entity"
                    results.append(result)
                    continue
                result.entity_id = int(entity.id)
                duration = import_duration(start, request_end, spec.bar_size_setting)
                self.market_data_service._get_point_in_time_data(
                    ticker=spec.symbol, entity_class=spec.entity_class, point_in_time=request_end.to_pydatetime(),
                    bar_size_setting=spec.bar_size_setting, duration_str=duration, what_to_show=spec.what_to_show,
                )
                result.imported = True
                self._check(result, spec, entity, start, end)
                if register:
                    for factor_id in self._raw_factor_ids(entity):
                        preloaded_coverage.register(factor_id, result.entity_id, start.to_pydatetime(),
                                                    end.to_pydatetime())
                        result.registered_factors.append(factor_id)
            except Exception as e:                        # one series failing never stops the others
                result.error = str(e)
            results.append(result)
            self.log(self.line(result))
        self.log(self.summary(results))
        return results

    # ------------------------------------------------------------------

    def _series_factors(self, spec: PreloadSeries, entity) -> list:
        """The raw bar factors (open / high / low / close / volume) of this series: subgroup = whatToShow,
        frequency = the bar size, of the entity's factor class."""
        from src.domain.entities.factor.factor import Factor
        from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING
        factor_cls = ENTITY_FACTOR_MAPPING[type(entity)][0]
        repo = self.factory.get_local_repository(factor_cls)
        frequency = Factor.bar_size_to_frequency(spec.bar_size_setting)
        out = []
        for f in repo.get_all() if repo is not None else []:
            if (getattr(f, "name", None) in RAW_FIELDS and getattr(f, "subgroup", None) == spec.what_to_show
                    and getattr(f, "frequency", None) == frequency and getattr(f, "source", None) != "calculated"):
                out.append(f)
        return out

    def _raw_factor_ids(self, entity) -> List[int]:
        """EVERY raw bar factor of the entity's class (any whatToShow, any frequency): once the run's series are
        loaded, no raw series of this entity is fetched from IBKR inside the window — a lookup on another frequency
        (e.g. the 5-minute closes the valuation chain also reads) or on a refused type (MIDPOINT) gets the latest
        closed stored bar or nothing, instead of an IBKR request per bar."""
        from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING
        repo = self.factory.get_local_repository(ENTITY_FACTOR_MAPPING[type(entity)][0])
        return [int(f.id) for f in (repo.get_all() if repo is not None else [])
                if getattr(f, "name", None) in RAW_FIELDS and getattr(f, "source", None) != "calculated"
                and getattr(f, "id", None) is not None]

    def _series_factor_ids(self, spec: PreloadSeries, entity) -> List[int]:
        return [int(f.id) for f in self._series_factors(spec, entity) if getattr(f, "id", None) is not None]

    def _check(self, result: PreloadResult, spec: PreloadSeries, entity, start, end) -> None:
        """Stored close bars in [start, end] against the bars the exchange was open for."""
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_data_coverage import (
            expected_bars,
        )
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key
        minutes = bar_minutes_of(spec.bar_size_setting)
        grid = expected_bars(start, end, minutes)
        result.expected_bars = len(grid)
        close = [f for f in self._series_factors(spec, entity) if f.name == "close"]
        if not close:
            return
        repo = self.factory.factor_value_local_repo
        stamps = set()
        for f in close:
            for d in repo.get_all_dates_by_id_entity_id(int(f.id), result.entity_id, type(entity).__name__):
                stamps.add(bar_key(pd.Timestamp(d), minutes))
        inside = sorted(s for s in stamps if s in set(grid))
        result.stored_bars = len(inside)
        if stamps:
            result.first_bar, result.last_bar = str(min(stamps)), str(max(stamps))

    # ------------------------------------------------------------------

    @staticmethod
    def line(r: PreloadResult) -> str:
        if r.error:
            return f"[preload] {r.symbol} {r.what_to_show} {r.bar_size_setting}: FAILED — {r.error}"
        return (f"[preload] {r.symbol} {r.what_to_show} {r.bar_size_setting}: {r.stored_bars}/{r.expected_bars} "
                f"bars ({r.coverage_pct:.1f}%), stored {r.first_bar} .. {r.last_bar}")

    @staticmethod
    def summary(results: List[PreloadResult]) -> str:
        ok = [r for r in results if not r.error]
        expected = sum(r.expected_bars for r in ok)
        stored = sum(r.stored_bars for r in ok)
        failed = [f"{r.symbol}:{r.what_to_show}" for r in results if r.error]
        pct = 100.0 * stored / expected if expected else float("nan")
        return (f"[preload] {len(ok)}/{len(results)} series loaded, {stored}/{expected} expected bars stored "
                f"({pct:.1f}%)" + (f"; failed: {', '.join(failed)}" if failed else ""))

    @staticmethod
    def to_frame(results: List[PreloadResult]) -> pd.DataFrame:
        return pd.DataFrame([{
            "symbol": r.symbol, "what_to_show": r.what_to_show, "bar_size": r.bar_size_setting,
            "entity_id": r.entity_id, "imported": r.imported, "expected_bars": r.expected_bars,
            "stored_bars": r.stored_bars, "coverage_pct": round(r.coverage_pct, 2) if r.expected_bars else None,
            "first_bar": r.first_bar, "last_bar": r.last_bar, "registered_factors": len(r.registered_factors),
            "error": r.error} for r in results])
