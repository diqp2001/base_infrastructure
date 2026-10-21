"""
Evaluation — reusable calculations extracted from the reference
`evaluation.ipynb` (unpack_data / plot_results) and the validation block of
`train_multivariate.ipynb`.

Captured portfolio return on day t (reference unpack_data):
    T_t   = target_vol * |Δ_t (pred / annualised_vol)|        (turnover)
    R_t   = mean_assets( pred * vol_scaled_return - 1e-4 * c * T_t )
where ``vol_scaled_return`` is the label (return t -> t+1 scaled to
``target_vol``), i.e. the signal at t is applied to the NEXT day's return.

Baselines are not part of the reference repository; they are the standard
comparisons of the momentum literature the paper builds on:
    long_only — +1 on every asset
    tsmom     — sign of the 252-day normalised return (time-series momentum)
    csmom     — cross-sectional rank of the 252-day return mapped to [-1, 1]
    macd      — Baz et al. response phi(y) = y * exp(-y^2 / 4) / 0.89 of the
                average normalised MACD signal
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_metrics import (
    hit_rate,
    performance_summary,
)


def captured_returns(preds: np.ndarray, returns: np.ndarray, vols: np.ndarray, c: float,
                     target_vol: float = 0.15, periods_per_year: int = 252) -> np.ndarray:
    """Per-row universe return net of turnover costs (reference unpack_data). Inputs are [S, N]."""
    ann_vols = vols * periods_per_year ** 0.5
    T = target_vol * np.abs(np.diff(preds / (ann_vols + 1e-12), prepend=0.0, axis=0))
    R = returns * preds - 1e-4 * c * T
    return np.mean(R, axis=1)


def evaluate_positions(preds: np.ndarray, returns: np.ndarray, vols: np.ndarray, dates,
                       basis_points=(0, 1, 5, 10), target_vol: float = 0.15) -> Dict[str, object]:
    out: Dict[str, object] = {"hit_rate": hit_rate(returns, preds), "by_cost": {}}
    for c in basis_points:
        R = captured_returns(preds, returns, vols, c, target_vol)
        out["by_cost"][c] = {
            **performance_summary(R),
            "returns": pd.Series(R, index=pd.DatetimeIndex(dates)),
        }
    return out


# ----------------------------------------------------------------------
# Baselines (positions in the same units as model signals)
# ----------------------------------------------------------------------

def _last_step_feature(X: np.ndarray, feature_names: List[str], name: str) -> np.ndarray:
    return X[:, :, -1, feature_names.index(name)]


def baseline_positions(X: np.ndarray, feature_names: List[str]) -> Dict[str, np.ndarray]:
    """X is the [S, N, T, F] model input of each sample (only the last row is used)."""
    positions: Dict[str, np.ndarray] = {"long_only": np.ones(X.shape[:2])}
    if "norm_annual_return" in feature_names:
        annual = _last_step_feature(X, feature_names, "norm_annual_return")
        positions["tsmom"] = np.sign(annual)
        n = annual.shape[1]
        if n > 1:
            ranks = np.argsort(np.argsort(annual, axis=1), axis=1)
            positions["csmom"] = ranks / (n - 1) * 2.0 - 1.0
    macd_names = [f for f in feature_names if f.startswith("macd_")]
    if macd_names:
        y = np.mean([_last_step_feature(X, feature_names, f) for f in macd_names], axis=0)
        positions["macd"] = y * np.exp(-(y ** 2) / 4.0) / 0.89
    return positions


def evaluate_with_baselines(model_preds: np.ndarray, samples, feature_names: List[str],
                            basis_points=(0, 1, 5, 10), target_vol: float = 0.15,
                            model_name: str = "stm") -> Dict[str, Dict[str, object]]:
    """Evaluate the model and every baseline on the same samples (last-step labels)."""
    returns = samples.y[:, -1, :]
    vols = samples.vol[:, -1, :]
    strategies: Dict[str, np.ndarray] = {model_name: model_preds}
    strategies.update(baseline_positions(samples.X, feature_names))
    return {
        name: evaluate_positions(pos, returns, vols, samples.dates, basis_points, target_vol)
        for name, pos in strategies.items()
    }


def signals_to_weights(signals: Dict[str, float], daily_vol: Dict[str, float], target_vol: float = 0.15,
                       gross_cap: Optional[float] = None, periods_per_year: int = 252) -> Dict[str, float]:
    """
    Portfolio weights equivalent to the research return R = mean(pred * r * target_vol / ann_vol):
        w_i = signal_i * target_vol / (ann_vol_i * N)
    Optionally rescaled so the gross exposure does not exceed ``gross_cap``.
    """
    n = len(signals)
    if n == 0:
        return {}
    weights = {}
    for asset, s in signals.items():
        vol = daily_vol.get(asset)
        if vol is None or not np.isfinite(vol) or vol <= 0:
            weights[asset] = 0.0
            continue
        weights[asset] = float(s) * target_vol / (vol * periods_per_year ** 0.5) / n     # vol is per row
    if gross_cap:
        gross = sum(abs(w) for w in weights.values())
        if gross > gross_cap:
            weights = {a: w * gross_cap / gross for a, w in weights.items()}
    return weights
