"""
Cross-sectional momentum features and label, from a daily close panel (index = session, columns = tickers).

Features: the 24 momentum factors of LGBMMomentumFeatureDefinition, each computed by ITS OWN DOMAIN FACTOR's
``calculate()`` on the closes window its DependencySpec asks for (``lookback`` N closes ending at the date, or
'ytd' = the last close of the previous year + every close of the year up to the date). The factor-resolution
path (CompanyShareCrossSectionalMomentumFactor) feeds the same calculate() with the same windows, so both paths
read identical values. Every value at date d uses closes up to d only.

Optional ``cs_rank_<name>``: percentile rank of the feature across the assets that have it on that date.

Label (training only): 1 when the return over the next ``horizon`` sessions beats the cross-sectional median of
that date, 0 otherwise; NaN when the future is not known yet. Assets are never aligned: a row (date, asset) is
usable when that asset has every feature it needs, whatever the other assets have.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMFeatureConfig,
    CSMLabelConfig,
)
from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
    LGBMMomentumFeatureDefinition,
)

_FACTOR_MODULES = ("company_share_return_factors", "company_share_ma_factors", "company_share_trend_factors",
                   "company_share_risk_factors", "company_share_drawdown_factors",
                   "company_share_composite_momentum_factors")
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


def momentum_factor_classes() -> Dict[str, type]:
    """feature name -> domain factor class (LGBMMomentumFeatureDefinition.FEATURE_MAP)."""
    classes = {}
    for module in _FACTOR_MODULES:
        mod = importlib.import_module(_PACKAGE + module)
        classes.update(dict(inspect.getmembers(mod, inspect.isclass)))
    return {feature: classes[cls_name] for cls_name, feature in LGBMMomentumFeatureDefinition.FEATURE_MAP}


def _lookback(factor) -> object:
    specs = factor.calculate_dependencies
    if len(specs) != 1 or getattr(specs[0], "lookback", None) is None:
        raise ValueError(f"{type(factor).__name__}: expected one close series dependency with a lookback")
    return specs[0].lookback


class CSMFeatureEngine:
    """Computes the candidate features with the domain factors; values are cached per (asset, date)."""

    def __init__(self, features: CSMFeatureConfig):
        self.config = features
        names = set(features.base_feature_names())
        self.factors = {n: cls() for n, cls in momentum_factor_classes().items() if n in names}
        self.lookbacks = {n: _lookback(f) for n, f in self.factors.items()}
        self._cache: Dict[Tuple[str, pd.Timestamp], Dict[str, float]] = {}

    def _value(self, name: str, values: np.ndarray, dates: pd.DatetimeIndex, i: int) -> float:
        lb = self.lookbacks[name]
        if lb == "ytd":
            year = dates[i].year
            first = np.searchsorted(dates.year, year)          # first bar of the year
            if first == 0:
                return np.nan                                     # no close of the previous year known
            window = values[first - 1:i + 1]
        else:
            n = int(lb)
            if i + 1 < n:
                return np.nan
            window = values[i + 1 - n:i + 1]
        try:
            v = self.factors[name].calculate({"CompanyShareFactor": window.tolist()})
        except (ValueError, ZeroDivisionError, TypeError):
            return np.nan
        return float(v) if v is not None and np.isfinite(float(v)) else np.nan

    def asset_features(self, asset: str, series: pd.Series) -> pd.DataFrame:
        """Feature rows of one asset (index = its own sessions)."""
        series = series.dropna().sort_index()
        values, dates = series.to_numpy(dtype=float), series.index
        rows = []
        for i, d in enumerate(dates):
            key = (asset, d)
            row = self._cache.get(key)
            if row is None:
                row = {n: self._value(n, values, dates, i) for n in self.factors}
                self._cache[key] = row
            rows.append(row)
        return pd.DataFrame(rows, index=dates, columns=list(self.factors))


def build_dataset(closes: pd.DataFrame, features: CSMFeatureConfig, label: CSMLabelConfig,
                  engine: Optional[CSMFeatureEngine] = None) -> CSMDataset:
    engine = engine or CSMFeatureEngine(features)
    closes = closes.sort_index().astype(float)
    base = features.base_feature_names()
    per_asset = {a: engine.asset_features(a, closes[a]) for a in closes.columns}
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
