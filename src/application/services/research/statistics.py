"""
Statistics of factor research and factor regressions (pure functions on pandas / numpy, no I/O).

Conventions
* A *panel* is a DataFrame indexed by timestamp, one column per security. A value at ``t`` is known at ``t``.
* Only observations present in every series of a computation are used (pairwise / aligned deletion); nothing is
  filled. Every result carries the number of observations it used.
* Correlations: Pearson or Spearman (rank). Fewer than ``min_obs`` observations or a constant series -> no
  coefficient, with the reason.
* Three different correlation notions are kept apart: pooled (all security-time pairs), cross-sectional (one
  coefficient per timestamp, then summarised over time) and time-series (correlation of two return series).
* OLS with classical and Newey-West (HAC, Bartlett kernel) standard errors; t-statistics, p-values and confidence
  intervals use the Student t distribution with n - k degrees of freedom.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sps

PEARSON, SPEARMAN = "pearson", "spearman"
METHODS = (PEARSON, SPEARMAN)
MIN_OBS = 10


# ── correlations ───────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Correlation:
    value: Optional[float]
    n: int
    note: str = ""


def correlation(x, y, method: str = PEARSON, min_obs: int = MIN_OBS) -> Correlation:
    """Correlation of two aligned 1-d series over the pairs where both are finite."""
    if method not in METHODS:
        raise ValueError(f"unknown correlation method '{method}' (use {METHODS})")
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    n = int(len(a))
    if n < min_obs:
        return Correlation(None, n, f"insufficient observations ({n} < {min_obs})")
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return Correlation(None, n, "constant series")
    if method == SPEARMAN:
        a, b = sps.rankdata(a), sps.rankdata(b)
    value = float(np.corrcoef(a, b)[0, 1])
    return Correlation(max(-1.0, min(1.0, value)), n)


def correlation_matrix(frame: pd.DataFrame, method: str = PEARSON, min_obs: int = MIN_OBS
                       ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[Tuple[str, str], str]]:
    """(coefficients, observation counts, notes per pair) — pairwise deletion, every pair its own sample."""
    cols = list(frame.columns)
    coef = pd.DataFrame(np.nan, index=cols, columns=cols)
    counts = pd.DataFrame(0, index=cols, columns=cols, dtype=int)
    notes: Dict[Tuple[str, str], str] = {}
    for i, a in enumerate(cols):
        for b in cols[i:]:
            c = correlation(frame[a].to_numpy(), frame[b].to_numpy(), method, min_obs)
            coef.loc[a, b] = coef.loc[b, a] = np.nan if c.value is None else c.value
            counts.loc[a, b] = counts.loc[b, a] = c.n
            if c.note:
                notes[(a, b)] = notes[(b, a)] = c.note
    return coef, counts, notes


def _aligned(a: pd.DataFrame, b: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    index = a.index.intersection(b.index)
    columns = a.columns.intersection(b.columns)
    return a.loc[index, columns], b.loc[index, columns]


def pooled_correlation(panel_a: pd.DataFrame, panel_b: pd.DataFrame, method: str = PEARSON,
                       min_obs: int = MIN_OBS) -> Correlation:
    """One coefficient over every (timestamp, security) pair where both panels have a value."""
    a, b = _aligned(panel_a, panel_b)
    return correlation(a.to_numpy().ravel(), b.to_numpy().ravel(), method, min_obs)


@dataclass
class CrossSectionalCorrelations:
    by_date: pd.Series                       # timestamp -> coefficient (NaN where not computable)
    counts: pd.Series                        # timestamp -> securities used
    summary: Dict[str, Optional[float]] = field(default_factory=dict)


def cross_sectional_correlations(panel_a: pd.DataFrame, panel_b: pd.DataFrame, method: str = PEARSON,
                                 min_assets: int = 5) -> CrossSectionalCorrelations:
    """One coefficient per timestamp across securities, then its distribution over time (mean, median, std,
    t-statistic of the mean, share of positive dates, first-half vs second-half mean as a stability check)."""
    a, b = _aligned(panel_a, panel_b)
    values, counts = {}, {}
    for t in a.index:
        c = correlation(a.loc[t].to_numpy(), b.loc[t].to_numpy(), method, min_assets)
        values[t] = np.nan if c.value is None else c.value
        counts[t] = c.n
    by_date = pd.Series(values, dtype=float).sort_index()
    valid = by_date.dropna()
    n = len(valid)
    summary: Dict[str, Optional[float]] = {"dates": float(len(by_date)), "dates_with_value": float(n)}
    if n:
        sd = float(valid.std(ddof=1)) if n > 1 else float("nan")
        half = n // 2
        summary.update(
            mean=float(valid.mean()), median=float(valid.median()), std=sd,
            t_stat=float(valid.mean() / (sd / math.sqrt(n))) if n > 1 and sd > 0 else None,
            share_positive=float((valid > 0).mean()),
            first_half_mean=float(valid.iloc[:half].mean()) if half else None,
            second_half_mean=float(valid.iloc[half:].mean()) if half else None,
        )
    return CrossSectionalCorrelations(by_date, pd.Series(counts, dtype=int).sort_index(), summary)


# ── descriptive statistics ───────────────────────────────────────────────────────────────────────────────────────

def describe_panel(panel: pd.DataFrame, expected_cells: Optional[int] = None) -> Dict[str, Optional[float]]:
    values = panel.to_numpy(dtype=float).ravel()
    present = values[np.isfinite(values)]
    total = expected_cells if expected_cells is not None else values.size
    out: Dict[str, Optional[float]] = {
        "observations": float(present.size), "expected": float(total),
        "missing": float(total - present.size), "coverage_pct": 100.0 * present.size / total if total else None,
        "securities": float(int(panel.notna().any(axis=0).sum())), "timestamps": float(int(panel.notna().any(axis=1).sum())),
    }
    if present.size:
        q = np.quantile(present, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
        out.update(mean=float(present.mean()), std=float(present.std(ddof=1)) if present.size > 1 else None,
                   min=float(present.min()), max=float(present.max()), median=float(q[3]),
                   q01=float(q[0]), q05=float(q[1]), q25=float(q[2]), q75=float(q[4]), q95=float(q[5]),
                   q99=float(q[6]))
    return out


def cross_sectional_profile(panel: pd.DataFrame) -> pd.DataFrame:
    """Per timestamp: securities with a value, mean, median, 25% / 75% quantiles (the cross-sectional evolution)."""
    return pd.DataFrame({"count": panel.notna().sum(axis=1), "mean": panel.mean(axis=1),
                         "median": panel.median(axis=1), "q25": panel.quantile(0.25, axis=1),
                         "q75": panel.quantile(0.75, axis=1)})


# ── forward returns and quantile portfolios ──────────────────────────────────────────────────────────────────────

def forward_returns(closes: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """Return from the close at t to the close ``horizon`` rows later, stamped at t (what a decision at t earns).
    The last ``horizon`` rows have no future and are NaN; a missing close gives NaN (never filled)."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    closes = closes.sort_index()
    return closes.shift(-horizon) / closes - 1.0


@dataclass
class QuantilePortfolios:
    returns: pd.DataFrame                   # timestamp x [Q1 .. Qn, 'Qn - Q1'] (equal weight)
    counts: pd.DataFrame                    # timestamp x [Q1 .. Qn]
    value_weighted: Optional[pd.DataFrame]  # same, weighted by market cap (None: no market caps given)
    turnover: pd.DataFrame                  # timestamp x [Q1 .. Qn]: share of the quantile's names replaced
    labels: List[str] = field(default_factory=list)


def quantile_portfolios(factor: pd.DataFrame, fwd: pd.DataFrame, n_quantiles: int = 5, min_assets: Optional[int] = None,
                        market_caps: Optional[pd.DataFrame] = None) -> QuantilePortfolios:
    """At each timestamp t, securities with both a factor value and a forward return are cut into equal-count
    quantiles of the factor (ties broken by order; Q1 = lowest); each quantile earns the mean forward return of its
    names (and the cap-weighted mean when ``market_caps`` known at t are given). Rebalanced at every timestamp."""
    min_assets = min_assets or n_quantiles
    labels = [f"Q{i + 1}" for i in range(n_quantiles)]
    a, r = _aligned(factor, fwd)
    caps = market_caps.reindex(index=a.index, columns=a.columns) if market_caps is not None else None
    rets, counts, vw, members = {}, {}, {}, {}
    prev: Dict[int, set] = {}
    turnover = {}
    for t in a.index:
        s = a.loc[t]
        rr = r.loc[t]
        ok = s.notna() & rr.notna() & np.isfinite(s) & np.isfinite(rr)
        names = s[ok]
        if len(names) < max(min_assets, n_quantiles):
            rets[t] = [np.nan] * (n_quantiles + 1)
            counts[t] = [0] * n_quantiles
            vw[t] = [np.nan] * (n_quantiles + 1)
            turnover[t] = [np.nan] * n_quantiles
            continue
        bucket = pd.qcut(names.rank(method="first"), n_quantiles, labels=False)
        q_means = rr[ok].groupby(bucket).mean().reindex(range(n_quantiles))
        rets[t] = list(q_means.to_numpy()) + [float(q_means.iloc[-1] - q_means.iloc[0])]
        counts[t] = list(bucket.value_counts().reindex(range(n_quantiles), fill_value=0).to_numpy())
        if caps is not None:
            c = caps.loc[t][ok]
            w = []
            for q in range(n_quantiles):
                idx = bucket[bucket == q].index
                cw = c[idx]
                good = cw.notna() & (cw > 0)
                w.append(float((rr[idx][good] * cw[good]).sum() / cw[good].sum()) if good.any() else np.nan)
            vw[t] = w + [w[-1] - w[0]]
        turn = []
        for q in range(n_quantiles):
            now = set(bucket[bucket == q].index)
            before = prev.get(q)
            turn.append(np.nan if not before else 1.0 - len(now & before) / max(len(now), 1))
            prev[q] = now
        turnover[t] = turn
        members[t] = bucket
    columns = labels + [f"Q{n_quantiles} - Q1"]
    return QuantilePortfolios(
        returns=pd.DataFrame.from_dict(rets, orient="index", columns=columns).sort_index(),
        counts=pd.DataFrame.from_dict(counts, orient="index", columns=labels).sort_index(),
        value_weighted=(pd.DataFrame.from_dict(vw, orient="index", columns=columns).sort_index()
                        if caps is not None else None),
        turnover=pd.DataFrame.from_dict(turnover, orient="index", columns=labels).sort_index(),
        labels=labels,
    )


def performance(returns: pd.Series, periods_per_year: float) -> Dict[str, Optional[float]]:
    """Simple-return series -> cumulative, annualised mean (x periods), volatility (x sqrt periods), Sharpe (no
    risk-free rate subtracted: mean / std x sqrt(periods)), maximum drawdown of the compounded wealth."""
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 2:
        return {"observations": float(len(r))}
    wealth = (1.0 + r).cumprod()
    sd = float(r.std(ddof=1))
    return {
        "observations": float(len(r)),
        "cumulative_return": float(wealth.iloc[-1] - 1.0),
        "annualised_return": float(r.mean() * periods_per_year),
        "annualised_volatility": float(sd * math.sqrt(periods_per_year)),
        "sharpe": float(r.mean() / sd * math.sqrt(periods_per_year)) if sd > 0 else None,
        "max_drawdown": float(-(wealth / wealth.cummax() - 1.0).min()),
    }


# ── regression ───────────────────────────────────────────────────────────────────────────────────────────────────

def newey_west_lags(n: int) -> int:
    """Newey-West (1994) rule of thumb: floor(4 (n / 100)^(2/9))."""
    return int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))) if n > 0 else 0


@dataclass
class OLSResult:
    names: List[str]                         # 'alpha' first, then the regressors
    coef: np.ndarray
    se: np.ndarray                           # standard errors used for inference (HAC or classical)
    se_classical: np.ndarray
    t: np.ndarray
    p: np.ndarray
    ci_low: np.ndarray
    ci_high: np.ndarray
    n: int
    k: int
    df: int
    r2: float
    adj_r2: float
    residuals: pd.Series
    fitted: pd.Series
    hac: bool
    hac_lags: int
    confidence: float
    diagnostics: Dict[str, Optional[float]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def table(self) -> pd.DataFrame:
        return pd.DataFrame({"coef": self.coef, "std_err": self.se, "t": self.t, "p_value": self.p,
                             f"ci_{int(self.confidence * 100)}_low": self.ci_low,
                             f"ci_{int(self.confidence * 100)}_high": self.ci_high}, index=self.names)


def ols(y: pd.Series, X: pd.DataFrame, hac: bool = True, lags: Optional[int] = None, confidence: float = 0.95,
        min_obs: int = 30) -> OLSResult:
    """y = alpha + X beta + e on the rows where y and every regressor are finite (nothing filled)."""
    data = pd.concat([pd.Series(y, name="__y__"), X], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    names = ["alpha"] + list(X.columns)
    n, k = len(data), len(names)
    if n <= k:
        raise ValueError(f"not enough aligned observations: {n} for {k} parameters")
    yv = data["__y__"].to_numpy(dtype=float)
    Xv = np.column_stack([np.ones(n), data[list(X.columns)].to_numpy(dtype=float)])
    XtX_inv = np.linalg.pinv(Xv.T @ Xv)
    beta = XtX_inv @ Xv.T @ yv
    fitted = Xv @ beta
    e = yv - fitted
    df = n - k
    sigma2 = float(e @ e) / df
    se_classical = np.sqrt(np.clip(np.diag(XtX_inv) * sigma2, 0, None))
    used_lags = (newey_west_lags(n) if lags is None else int(lags)) if hac else 0
    if hac:
        Xe = Xv * e[:, None]
        S = Xe.T @ Xe
        for lag in range(1, used_lags + 1):
            w = 1.0 - lag / (used_lags + 1.0)                       # Bartlett kernel
            G = Xe[lag:].T @ Xe[:-lag]
            S += w * (G + G.T)
        cov = XtX_inv @ S @ XtX_inv * n / df                        # small-sample correction n / (n - k)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    else:
        se = se_classical
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta / se, np.nan)
    p = 2.0 * sps.t.sf(np.abs(t), df)
    crit = sps.t.ppf(0.5 + confidence / 2.0, df)
    tss = float(((yv - yv.mean()) ** 2).sum())
    r2 = 1.0 - float(e @ e) / tss if tss > 0 else float("nan")
    adj = 1.0 - (1.0 - r2) * (n - 1) / df if tss > 0 else float("nan")
    warnings = []
    if n < min_obs:
        warnings.append(f"short sample: {n} observations (< {min_obs}); estimates are unreliable")
    cond = float(np.linalg.cond(Xv)) if n else float("nan")
    if cond > 1e3 and k > 2:
        warnings.append(f"regressors are close to collinear (condition number {cond:.0f}): betas are unstable")
    dw = float(np.sum(np.diff(e) ** 2) / (e @ e)) if float(e @ e) > 0 else None
    jb = sps.jarque_bera(e) if n > 2 else None
    diagnostics = {"durbin_watson": dw, "condition_number": cond,
                   "jarque_bera": float(jb.statistic) if jb is not None else None,
                   "jarque_bera_p": float(jb.pvalue) if jb is not None else None,
                   "residual_std": float(np.sqrt(sigma2)), "skew": float(sps.skew(e)) if n > 2 else None,
                   "excess_kurtosis": float(sps.kurtosis(e)) if n > 3 else None}
    index = data.index
    return OLSResult(names=names, coef=beta, se=se, se_classical=se_classical, t=t, p=p,
                     ci_low=beta - crit * se, ci_high=beta + crit * se, n=n, k=k, df=df, r2=r2, adj_r2=adj,
                     residuals=pd.Series(e, index=index), fitted=pd.Series(fitted, index=index), hac=hac,
                     hac_lags=used_lags, confidence=confidence, diagnostics=diagnostics, warnings=warnings)


def rolling_ols(y: pd.Series, X: pd.DataFrame, window: int, confidence: float = 0.95) -> pd.DataFrame:
    """Coefficients, their classical confidence bands and R-squared over a rolling window of aligned rows,
    stamped at the window's last row."""
    data = pd.concat([pd.Series(y, name="__y__"), X], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    k = X.shape[1] + 1
    if window <= k + 1:
        raise ValueError(f"the rolling window ({window}) must exceed the number of parameters + 1 ({k + 1})")
    rows = []
    for end in range(window, len(data) + 1):
        chunk = data.iloc[end - window:end]
        try:
            res = ols(chunk["__y__"], chunk[list(X.columns)], hac=False, confidence=confidence, min_obs=0)
        except (ValueError, np.linalg.LinAlgError):
            continue
        row = {"r2": res.r2}
        for name, c, lo, hi in zip(res.names, res.coef, res.ci_low, res.ci_high):
            row[name], row[f"{name}_low"], row[f"{name}_high"] = c, lo, hi
        rows.append((chunk.index[-1], row))
    return pd.DataFrame([r for _, r in rows], index=[t for t, _ in rows])


def outliers(residuals: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Residuals more than ``threshold`` standard deviations from zero."""
    sd = residuals.std(ddof=1)
    return residuals[np.abs(residuals) > threshold * sd] if sd and sd > 0 else residuals.iloc[0:0]


def compound_to(returns: pd.Series, rule: str) -> pd.Series:
    """Compound simple returns into coarser periods ('D' daily, 'W-FRI' weekly, 'M' month-end); a period with no
    return is absent (not zero)."""
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        return r
    grouped = (1.0 + r).groupby(r.index.to_period(rule) if rule != "D" else r.index.normalize())
    out = grouped.prod() - 1.0
    if rule != "D":
        out.index = out.index.to_timestamp(how="end").normalize()
    return out
