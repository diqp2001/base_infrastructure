"""
Performance metrics used by the reference evaluation notebook.

The reference imports them from `empyrical` (sharpe_ratio, sortino_ratio,
calmar_ratio, max_drawdown, annual_return) and sklearn's accuracy_score.
`empyrical` is not a project dependency, so the same formulas are
re-implemented here for daily simple returns with a zero risk-free rate.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

APPROX_BDAYS_PER_YEAR = 252


def _clean(returns) -> np.ndarray:
    r = np.asarray(returns, dtype=float).ravel()
    return r[~np.isnan(r)]


def sharpe_ratio(returns) -> float:
    r = _clean(returns)
    if len(r) < 2:
        return float("nan")
    std = np.std(r, ddof=1)
    if std == 0:
        return float("nan")
    return float(np.mean(r) / std * np.sqrt(APPROX_BDAYS_PER_YEAR))


def downside_risk(returns) -> float:
    r = _clean(returns)
    if len(r) == 0:
        return float("nan")
    downside = np.clip(r, -np.inf, 0.0)
    return float(np.sqrt(np.mean(downside ** 2)) * np.sqrt(APPROX_BDAYS_PER_YEAR))


def sortino_ratio(returns) -> float:
    r = _clean(returns)
    if len(r) < 2:
        return float("nan")
    dr = downside_risk(r)
    if not dr:
        return float("nan")
    return float(np.mean(r) * APPROX_BDAYS_PER_YEAR / dr)


def max_drawdown(returns) -> float:
    r = _clean(returns)
    if len(r) == 0:
        return float("nan")
    cumulative = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    running_max = np.maximum.accumulate(cumulative)
    return float(np.min(cumulative / running_max - 1.0))


def annual_return(returns) -> float:
    r = _clean(returns)
    if len(r) == 0:
        return float("nan")
    ending = np.prod(1.0 + r)
    years = len(r) / APPROX_BDAYS_PER_YEAR
    if ending <= 0:
        return -1.0
    return float(ending ** (1.0 / years) - 1.0)


def calmar_ratio(returns) -> float:
    mdd = max_drawdown(returns)
    if not mdd or np.isnan(mdd):
        return float("nan")
    return float(annual_return(returns) / abs(mdd))


def hit_rate(returns_by_asset, preds_by_asset, direction_threshold: float = 0.0) -> float:
    """Reference 'Hitrate': per-asset accuracy of the predicted direction, averaged over assets."""
    returns_by_asset = np.asarray(returns_by_asset, dtype=float)
    preds_by_asset = np.asarray(preds_by_asset, dtype=float)
    true_dir = (returns_by_asset > direction_threshold).astype(int)
    pred_dir = (preds_by_asset > direction_threshold).astype(int)
    accs = [float(np.mean(true_dir[:, i] == pred_dir[:, i])) for i in range(true_dir.shape[1])]
    return float(np.mean(accs)) if accs else float("nan")


def performance_summary(portfolio_returns) -> Dict[str, float]:
    return {
        "sharpe_ratio": sharpe_ratio(portfolio_returns),
        "sortino_ratio": sortino_ratio(portfolio_returns),
        "calmar_ratio": calmar_ratio(portfolio_returns),
        "max_drawdown": max_drawdown(portfolio_returns),
        "annual_return": annual_return(portfolio_returns),
    }
