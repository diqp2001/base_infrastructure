"""
Cross-sectional classifier features and label, from daily bar panels (index = session, columns = tickers):
``close`` (required), ``volume``, ``high``, ``low``; plus the close series of the benchmarks the candidates
compare against (``benchmarks`` = {symbol: close series}, e.g. SPY), read where a DependencySpec names an
``entity_symbol``.

Features: the candidates of CSMFeatureDefinition (24 momentum + 11 liquidity / volume-trend / range / return-extreme
factors), each computed by ITS OWN DOMAIN FACTOR's ``calculate()`` on the windows its DependencySpecs ask for: for
every spec, the ``lookback`` last bars of the field in ``name_in`` (close / volume / high / low), passed under the
spec's key; 'ytd' = the last close of the previous year + every close of the year up to the date. The
factor-resolution path (CompanyShareCrossSectionalMomentumFactor) feeds the same calculate() with the same windows,
so both paths read identical values. Every value at date d uses bars up to d only; a window with a missing bar
gives no value.

Optional ``cs_rank_<name>``: percentile rank of the feature across the assets that have it on that date.

Label (training only): 1 when the return over the next ``horizon`` sessions beats the cross-sectional median of
that date, 0 otherwise; NaN when the future is not known yet. Assets are never aligned: a row (date, asset) is
usable when that asset has every feature it needs, whatever the other assets have.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMFeatureConfig,
    CSMLabelConfig,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
    CSMFeatureDefinition,
)

_FACTOR_MODULES = ("company_share_return_factors", "company_share_ma_factors", "company_share_trend_factors",
                   "company_share_risk_factors", "company_share_drawdown_factors",
                   "company_share_composite_momentum_factors", "company_share_liquidity_factors",
                   "company_share_avg_turnover_6m_factor", "company_share_monthly_price_range_factor",
                   "company_share_relative_performance_factors")
BAR_FIELDS = ("close", "volume", "high", "low")
_PACKAGE = "src.domain.entities.factor.finance.financial_assets.share_factor.company_share."


@dataclass
class CSMDataset:
    """Long table: one row per (date, asset)."""
    frame: pd.DataFrame            # MultiIndex (date, asset); feature columns + label, fwd_return, daily_vol
    feature_names: List[str]

    def rows_on(self, date) -> pd.DataFrame:
        try:
            return self.frame.xs(pd.Timestamp(date), level="date")
        except KeyError:
            return self.frame.iloc[0:0].droplevel("date")


def candidate_factor_classes() -> Dict[str, type]:
    """feature name -> domain factor class (CSMFeatureDefinition.FEATURE_MAP)."""
    classes = {}
    for module in _FACTOR_MODULES:
        mod = importlib.import_module(_PACKAGE + module)
        classes.update(dict(inspect.getmembers(mod, inspect.isclass)))
    return {feature: classes[cls_name] for cls_name, feature in CSMFeatureDefinition.FEATURE_MAP}


momentum_factor_classes = candidate_factor_classes          # former name


def _windows(factor) -> List[Tuple[str, object, str]]:
    """(bar field, lookback, dependency key) of every raw series the factor reads."""
    out = []
    for spec in factor.calculate_dependencies:
        names = list(getattr(spec, "name_in", None) or [])
        if len(names) != 1 or names[0] not in BAR_FIELDS or getattr(spec, "lookback", None) is None:
            raise ValueError(f"{type(factor).__name__}: expected raw bar series with a lookback, got {spec}")
        symbol = getattr(spec, "entity_symbol", None)
        out.append((f"{names[0]}@{symbol}" if symbol else names[0], spec.lookback, spec.result_key))
    return out


def benchmark_symbols(features: Optional[CSMFeatureConfig] = None) -> List[str]:
    """Symbols of the other entities the candidates read (DependencySpec.entity_symbol), e.g. ['SPY']."""
    names = set((features or CSMFeatureConfig()).base_feature_names())
    symbols = {field.split("@", 1)[1] for n, cls in candidate_factor_classes().items() if n in names
               for field, _, _ in _windows(cls()) if "@" in field}
    return sorted(symbols)


def max_lookback(features: Optional[CSMFeatureConfig] = None) -> int:
    """Longest fixed window (bars) any candidate reads ('ytd' only needs a close of the previous year)."""
    names = set((features or CSMFeatureConfig()).base_feature_names())
    lookbacks = [lb for n, cls in candidate_factor_classes().items() if n in names
                 for _, lb, _ in _windows(cls()) if isinstance(lb, int)]
    return max(lookbacks) if lookbacks else 1


class CSMFeatureEngine:
    """Computes the candidate features with the domain factors; values are cached per (asset, date)."""

    def __init__(self, features: CSMFeatureConfig):
        self.config = features
        names = set(features.base_feature_names())
        self.factors = {n: cls() for n, cls in candidate_factor_classes().items() if n in names}
        self.windows = {n: _windows(f) for n, f in self.factors.items()}
        self._cache: Dict[Tuple[str, pd.Timestamp], Dict[str, float]] = {}

    @staticmethod
    def _window(values: np.ndarray, dates: pd.DatetimeIndex, i: int, lookback) -> Optional[np.ndarray]:
        if lookback == "ytd":
            first = np.searchsorted(dates.year, dates[i].year)    # first bar of the year
            if first == 0:
                return None                                        # no close of the previous year known
            window = values[first - 1:i + 1]
        else:
            n = int(lookback)
            if i + 1 < n:
                return None
            window = values[i + 1 - n:i + 1]
        return None if np.isnan(window).any() else window

    def _value(self, name: str, bars: Dict[str, np.ndarray], dates: pd.DatetimeIndex, i: int) -> float:
        dependencies = {}
        for field, lookback, key in self.windows[name]:
            if field not in bars:
                return np.nan
            window = self._window(bars[field], dates, i, lookback)
            if window is None:
                return np.nan
            dependencies[key] = window.tolist()
        try:
            v = self.factors[name].calculate(dependencies)
        except (ValueError, ZeroDivisionError, TypeError):
            return np.nan
        return float(v) if v is not None and np.isfinite(float(v)) else np.nan

    def asset_features(self, asset: str, series: Union[pd.Series, pd.DataFrame]) -> pd.DataFrame:
        """Feature rows of one asset (index = its own close sessions); ``series`` = closes or a bar-field frame."""
        frame = series.to_frame("close") if isinstance(series, pd.Series) else series
        frame = frame[frame["close"].notna()].sort_index()
        dates = frame.index
        bars = {f: frame[f].to_numpy(dtype=float) for f in frame.columns}
        rows = []
        for i, d in enumerate(dates):
            key = (asset, d)
            row = self._cache.get(key)
            if row is None:
                row = {n: self._value(n, bars, dates, i) for n in self.factors}
                self._cache[key] = row
            rows.append(row)
        return pd.DataFrame(rows, index=dates, columns=list(self.factors))


def build_dataset(bars: Union[pd.DataFrame, Dict[str, pd.DataFrame]], features: CSMFeatureConfig,
                  label: CSMLabelConfig, engine: Optional[CSMFeatureEngine] = None,
                  benchmarks: Optional[Dict[str, pd.Series]] = None) -> CSMDataset:
    """``bars`` = the close panel, or {field: panel} with 'close' and any of volume / high / low;
    ``benchmarks`` = {symbol: close series} for the candidates that compare with another entity."""
    engine = engine or CSMFeatureEngine(features)
    panels = {"close": bars} if isinstance(bars, pd.DataFrame) else dict(bars)
    closes = panels["close"].sort_index().astype(float)
    base = features.base_feature_names()
    per_asset = {}
    for a in closes.columns:
        frame = pd.DataFrame({f: (panels[f][a].reindex(closes.index) if a in panels[f] else np.nan)
                              for f in BAR_FIELDS if f in panels}, index=closes.index).astype(float)
        for symbol, series in (benchmarks or {}).items():
            frame[f"close@{symbol}"] = series.reindex(closes.index).astype(float)
        per_asset[a] = engine.asset_features(a, frame)
    columns = {n: pd.DataFrame({a: f[n] for a, f in per_asset.items()}).reindex(closes.index) for n in base}
    if features.cross_sectional_ranks:
        for n in base:
            columns[f"cs_rank_{n}"] = columns[n].rank(axis=1, pct=True)

    r = closes.pct_change(fill_method=None)
    h = int(label.horizon)
    fwd = closes.shift(-h) / closes - 1.0
    columns["label"] = fwd.gt(fwd.median(axis=1), axis=0).astype(float).where(fwd.notna())
    columns["fwd_return"] = fwd
    columns["daily_vol"] = r.ewm(span=features.vol_span, min_periods=features.vol_span).std()

    stacked = {name: panel.replace([np.inf, -np.inf], np.nan).stack(future_stack=True)
               for name, panel in columns.items()}
    frame = pd.DataFrame(stacked)
    frame.index = frame.index.set_names(["date", "asset"])
    names = features.feature_names()
    frame = frame[names + ["label", "fwd_return", "daily_vol"]]
    frame = frame[frame[names].notna().any(axis=1) | frame["label"].notna()]
    return CSMDataset(frame=frame.sort_index(), feature_names=names)
