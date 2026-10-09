"""
Dataset construction — model input X[t] = [assets x lookback x features].

Mirrors the reference MultivariateTrainValTestSplitter:
  * X sample at row i uses feature rows i-T+1 .. i (``shift(T-j-1)``)
  * y sample at row i uses target rows i-Tt+1 .. i
  * train  = rows with date <= start
    val    = start < date <= start + val
    test   = start + val < date <= start + val + test
  * optional scaler fitted on train rows only

Deliberate differences (look-ahead hygiene):
  * the last ``purge_days`` train / val rows are dropped, because their
    labels are returns realised inside the next fold;
  * every sample must have fully observed features and labels — missing
    data is reported and excluded, never filled.

Asset order, feature order and dates are carried with every array so the
same ordering is reused at inference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_features import (
    compute_universe_features,
    first_valid_feature_row,
)


@dataclass
class FeaturePanel:
    """Aligned features for a whole universe."""

    dates: pd.DatetimeIndex
    assets: List[str]
    feature_names: List[str]
    features: np.ndarray          # [D, N, F]
    target: np.ndarray            # [D, N] vol-scaled forward return (label; NaN when unknown)
    target_orig: np.ndarray       # [D, N] non-scaled forward return
    daily_vol: np.ndarray         # [D, N]
    first_valid_row: int          # rows before this are warm-up
    report: Dict[str, object] = field(default_factory=dict)

    def index_at_or_before(self, as_of) -> int:
        """Last row whose date <= as_of (the as_of close is assumed known)."""
        ts = pd.Timestamp(as_of)
        pos = int(self.dates.searchsorted(ts, side="right")) - 1
        return pos


def align_close_panel(close_panel: pd.DataFrame, required_rows: int = 0) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """
    Inner-join closes across assets (reference: pd.merge(..., how='inner') on Date).

    Assets with fewer than ``required_rows`` observations are dropped and
    reported rather than silently shrinking the common history.
    """
    report: Dict[str, object] = {}
    panel = close_panel.sort_index()
    panel = panel.where(panel > 0)
    counts = panel.notna().sum()
    dropped_assets = [a for a in panel.columns if counts[a] < required_rows]
    if dropped_assets:
        panel = panel.drop(columns=dropped_assets)
    report["dropped_assets_insufficient_history"] = dropped_assets
    before = len(panel)
    panel = panel.dropna(how="any")
    report["dropped_dates_missing_any_asset"] = before - len(panel)
    report["n_assets"] = panel.shape[1]
    report["n_dates"] = len(panel)
    return panel, report


def build_feature_panel(close_panel: pd.DataFrame, cfg: STMFeatureConfig, horizon: int = 1,
                        assets: Optional[List[str]] = None) -> FeaturePanel:
    """Compute features for an aligned close panel (dates x assets)."""
    if assets is not None:
        missing = [a for a in assets if a not in close_panel.columns]
        if missing:
            raise ValueError(f"Close panel is missing assets required by the model: {missing}")
        close_panel = close_panel[assets]
    close_panel = close_panel.sort_index()
    if close_panel.isna().any().any():
        raise ValueError("Close panel contains missing values; align it with align_close_panel first")

    names = cfg.feature_names()
    frames = compute_universe_features(close_panel, cfg, horizon)
    asset_list = list(close_panel.columns)
    features = np.stack([frames[a][names].to_numpy(dtype=float) for a in asset_list], axis=1)
    target = np.stack([frames[a]["target_returns"].to_numpy(dtype=float) for a in asset_list], axis=1)
    target_orig = np.stack([frames[a]["target_returns_nonscaled"].to_numpy(dtype=float) for a in asset_list], axis=1)
    vol = np.stack([frames[a]["daily_vol"].to_numpy(dtype=float) for a in asset_list], axis=1)
    first = first_valid_feature_row(frames, names, cfg.min_warmup_rows)
    return FeaturePanel(
        dates=pd.DatetimeIndex(close_panel.index),
        assets=asset_list,
        feature_names=names,
        features=features,
        target=target,
        target_orig=target_orig,
        daily_vol=vol,
        first_valid_row=first,
    )


# ----------------------------------------------------------------------
# Scaling (fit on train rows only)
# ----------------------------------------------------------------------

def fit_scaler(features: np.ndarray, mode: Optional[str]) -> Optional[Dict[str, list]]:
    """Per (asset, feature) scaler, like the reference per-asset sklearn scaler."""
    if mode is None:
        return None
    if mode == "standard":
        mean = np.nanmean(features, axis=0)
        std = np.nanstd(features, axis=0)
        std = np.where(std == 0, 1.0, std)
        return {"mode": "standard", "a": mean.tolist(), "b": std.tolist()}
    if mode == "minmax":
        lo = np.nanmin(features, axis=0)
        hi = np.nanmax(features, axis=0)
        rng = np.where(hi - lo == 0, 1.0, hi - lo)
        return {"mode": "minmax", "a": lo.tolist(), "b": rng.tolist()}
    raise NotImplementedError(f"Unknown scaling '{mode}'")


def apply_scaler(features: np.ndarray, scaler: Optional[Dict[str, list]]) -> np.ndarray:
    if not scaler:
        return features
    return (features - np.asarray(scaler["a"])) / np.asarray(scaler["b"])


# ----------------------------------------------------------------------
# Samples
# ----------------------------------------------------------------------

@dataclass
class SampleSet:
    X: np.ndarray            # [S, N, T, F]
    y: np.ndarray            # [S, Tt, N]
    y_orig: np.ndarray       # [S, Tt, N]
    vol: np.ndarray          # [S, Tt, N]
    dates: pd.DatetimeIndex  # decision date of each sample

    def __len__(self) -> int:
        return len(self.X)


def _window_complete(panel_arrays, i: int, lookback: int, target_steps: int, need_label: bool) -> bool:
    feats, target, target_orig, vol = panel_arrays
    if i - lookback + 1 < 0 or i - target_steps + 1 < 0:
        return False
    if np.isnan(feats[i - lookback + 1:i + 1]).any():
        return False
    if need_label:
        sl = slice(i - target_steps + 1, i + 1)
        if np.isnan(target[sl]).any() or np.isnan(target_orig[sl]).any() or np.isnan(vol[sl]).any():
            return False
    return True


def build_samples(panel: FeaturePanel, rows: List[int], lookback: int, target_steps: int,
                  scaler: Optional[Dict[str, list]] = None, need_label: bool = True) -> SampleSet:
    feats = apply_scaler(panel.features, scaler)
    arrays = (feats, panel.target, panel.target_orig, panel.daily_vol)
    kept = [i for i in rows if i >= panel.first_valid_row and _window_complete(arrays, i, lookback, target_steps, need_label)]
    n, f = len(panel.assets), len(panel.feature_names)
    if not kept:
        empty = np.zeros((0, n, lookback, f))
        return SampleSet(empty, np.zeros((0, target_steps, n)), np.zeros((0, target_steps, n)),
                         np.zeros((0, target_steps, n)), pd.DatetimeIndex([]))
    X = np.stack([feats[i - lookback + 1:i + 1].transpose(1, 0, 2) for i in kept])          # [S, N, T, F]
    y = np.stack([panel.target[i - target_steps + 1:i + 1] for i in kept])                  # [S, Tt, N]
    y_orig = np.stack([panel.target_orig[i - target_steps + 1:i + 1] for i in kept])
    vol = np.stack([panel.daily_vol[i - target_steps + 1:i + 1] for i in kept])
    return SampleSet(X, y, y_orig, vol, panel.dates[kept])


@dataclass
class WalkForwardSplit:
    start: pd.Timestamp
    train_end: pd.Timestamp
    val_end: pd.Timestamp
    test_end: pd.Timestamp
    train: SampleSet
    val: SampleSet
    test: SampleSet
    scaler: Optional[Dict[str, list]]


def walk_forward_starts(training_cfg) -> List[pd.Timestamp]:
    """Reference: pd.date_range('2017-01-01', '2023-12-31', freq='365d')."""
    return list(pd.date_range(training_cfg.first_split_start, training_cfg.last_split_start,
                              freq=f"{training_cfg.split_frequency_days}D"))


def make_split(panel: FeaturePanel, start, config: STMConfiguration,
               test_days: Optional[int] = None) -> WalkForwardSplit:
    t_cfg, m_cfg = config.training, config.model
    start = pd.Timestamp(start)
    val_end = start + pd.Timedelta(days=t_cfg.val_days)
    test_end = val_end + pd.Timedelta(days=t_cfg.test_days if test_days is None else test_days)
    dates = panel.dates
    lookback, target_steps = m_cfg.lookback, m_cfg.target_timesteps()
    purge = max(int(t_cfg.purge_days), int(config.prediction_horizon) - 1, 0)

    train_rows = [i for i in range(len(dates)) if dates[i] <= start]
    val_rows = [i for i in range(len(dates)) if start < dates[i] <= val_end]
    test_rows = [i for i in range(len(dates)) if val_end < dates[i] <= test_end]
    if purge:
        train_rows = train_rows[:-purge] if len(train_rows) > purge else []
        val_rows = val_rows[:-purge] if len(val_rows) > purge else []

    fit_rows = [i for i in train_rows if i >= panel.first_valid_row]
    scaler = fit_scaler(panel.features[fit_rows], t_cfg.scaling) if fit_rows else None

    return WalkForwardSplit(
        start=start,
        train_end=dates[train_rows[-1]] if train_rows else start,
        val_end=val_end,
        test_end=test_end,
        train=build_samples(panel, train_rows, lookback, target_steps, scaler),
        val=build_samples(panel, val_rows, lookback, target_steps, scaler),
        test=build_samples(panel, test_rows, lookback, target_steps, scaler),
        scaler=scaler,
    )


def build_inference_input(panel: FeaturePanel, as_of, lookback: int,
                          scaler: Optional[Dict[str, list]] = None) -> Tuple[np.ndarray, pd.Timestamp]:
    """
    X for one decision date: [1, N, T, F] built from rows with date <= as_of.

    Raises ValueError when the window is incomplete — inference never
    substitutes or forward-fills missing features.
    """
    i = panel.index_at_or_before(as_of)
    if i < 0:
        raise ValueError(f"No feature row at or before {as_of}")
    if i < panel.first_valid_row or i - lookback + 1 < panel.first_valid_row:
        raise ValueError(f"Insufficient history at {as_of}: need {lookback} valid rows after warm-up")
    feats = apply_scaler(panel.features, scaler)
    window = feats[i - lookback + 1:i + 1]
    if np.isnan(window).any():
        raise ValueError(f"Missing feature values in the lookback window ending {panel.dates[i].date()}")
    return window.transpose(1, 0, 2)[None, ...], panel.dates[i]
