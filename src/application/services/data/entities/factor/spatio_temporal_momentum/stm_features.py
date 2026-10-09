"""
Feature construction — causal port of the reference `src/features.py`
(DeepMomentumFeatures, MACDFeatures, DefaultFeatureCreator._prepare_series).

Every formula is the reference formula.  The only change is the removal of
``.bfill()`` on the rolling/EWM statistics: back-filling copies statistics
computed from later prices into earlier rows (look-ahead).  Rows that would
have needed the back-fill are left NaN and dropped by the warm-up cut, which
the reference also applies (``cut_nan_samples=253``).  From the first fully
causal row onwards the values are identical to the reference.

A feature at row ``t`` uses closes up to and including ``t`` only.
``target_returns`` at row ``t`` is the vol-scaled return from ``t`` to
``t + horizon`` — it is a training label, never a model input.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMFeatureConfig,
)

AUX_COLUMNS = ["daily_returns", "daily_vol", "target_returns", "target_returns_nonscaled"]


def winsorise_prices(srs: pd.Series, halflife: int, threshold: float, eps: float = 1e-6) -> pd.Series:
    """Reference DefaultFeatureCreator._prepare_series (EWM statistics are causal)."""
    srs = srs.loc[(srs.notnull()) & (srs > eps)].copy()
    ewm = srs.ewm(halflife=halflife)
    means = ewm.mean()
    stds = ewm.std()
    srs = np.minimum(srs, means + threshold * stds)
    srs = np.maximum(srs, means - threshold * stds)
    return srs


def _calc_returns(srs: pd.Series, day_offset: int = 1) -> pd.Series:
    return srs / srs.shift(day_offset) - 1.0


def _calc_daily_vol(daily_returns: pd.Series, vol_lookback: int) -> pd.Series:
    # Reference: .ewm(span, min_periods).std().bfill()  — bfill removed (look-ahead)
    return daily_returns.ewm(span=vol_lookback, min_periods=vol_lookback).std()


def _calc_halflife(timescale: int) -> float:
    return np.log(0.5) / (np.log(1 - 1 / timescale) + 1e-9)


def _calc_macd_signal(srs: pd.Series, short: int, long: int, price_std_window: int, signal_std_window: int) -> pd.Series:
    macd = (
        srs.ewm(halflife=_calc_halflife(short)).mean()
        - srs.ewm(halflife=_calc_halflife(long)).mean()
    )
    # Reference: rolling(63).std().bfill() / rolling(252).std().bfill() — bfill removed
    q = macd / (srs.rolling(price_std_window).std() + 1e-9)
    return q / (q.rolling(signal_std_window).std() + 1e-9)


def compute_asset_features(close: pd.Series, cfg: STMFeatureConfig, horizon: int = 1) -> pd.DataFrame:
    """
    Features + auxiliary columns for one asset, indexed like ``close``.

    Columns: cfg.feature_names() + AUX_COLUMNS.  No rows are dropped here.
    """
    close = close.sort_index()
    srs = winsorise_prices(close, cfg.winsorise_halflife, cfg.winsorise_threshold).reindex(close.index)

    out = pd.DataFrame(index=close.index)
    daily_returns = _calc_returns(srs)
    daily_vol = _calc_daily_vol(daily_returns, cfg.vol_lookback)
    out["daily_returns"] = daily_returns
    out["daily_vol"] = daily_vol

    annualized_vol = daily_vol * np.sqrt(cfg.annualisation)
    # Reference (horizon=1): (daily_returns * vol_target / annualized_vol.shift(1)).shift(-1)
    #   = return(t -> t+1) * vol_target / annualized_vol(t)
    forward_return = srs.shift(-horizon) / srs - 1.0
    out["target_returns"] = forward_return * cfg.vol_target / annualized_vol
    out["target_returns_nonscaled"] = forward_return

    for h, name in zip(cfg.return_horizons, cfg.return_feature_names()):
        out[name] = _calc_returns(srs, h) / daily_vol / np.sqrt(h)

    for (s, l), name in zip(cfg.macd_combinations, cfg.macd_feature_names()):
        out[name] = _calc_macd_signal(srs, s, l, cfg.macd_price_std_window, cfg.macd_signal_std_window)

    return out[cfg.feature_names() + AUX_COLUMNS]


def compute_universe_features(close_panel: pd.DataFrame, cfg: STMFeatureConfig, horizon: int = 1) -> Dict[str, pd.DataFrame]:
    """Per-asset feature frames for every column of ``close_panel`` (dates x assets)."""
    return {asset: compute_asset_features(close_panel[asset], cfg, horizon) for asset in close_panel.columns}


def first_valid_feature_row(frames: Dict[str, pd.DataFrame], feature_names: List[str], min_warmup_rows: int) -> int:
    """Index of the first row where every asset has every feature (plus the reference warm-up cut)."""
    first = min_warmup_rows
    for frame in frames.values():
        valid = frame[feature_names].notna().all(axis=1).to_numpy()
        if not valid.any():
            return len(valid)
        first = max(first, int(np.argmax(valid)))
    return first
