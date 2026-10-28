"""
Factor analysis of a strategy's returns: CAPM, Fama-French 3 / 5 factors, or a custom set of factor returns.

    y_t = alpha + sum_k beta_k F_k,t + e_t,   y_t = R_t - RF_t  (total-return strategy)  or  R_t  (excess-return,
                                                                  self-financing strategy): RF subtracted at most once

Steps (each reported):
1. the strategy's realised-stamped bar returns and the factor returns are compounded to the analysis frequency
   (daily, weekly, monthly); a period without data is absent, never zero;
2. only periods where the strategy, every factor and (for total returns) RF are all present are used; the periods
   each side lost are counted;
3. OLS with Newey-West standard errors (Bartlett kernel; lags from the n^(2/9) rule unless given);
4. alpha annualised arithmetically (alpha x periods per year), with its confidence interval scaled the same way;
5. contributions beta_k F_k,t, the fitted (factor) part and the residual; their cumulative sums are an additive,
   model-based decomposition (not causal attribution);
6. rolling regressions, residual diagnostics and outliers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.research import statistics as st
from src.application.services.research.project_returns import StrategyReturns
from src.domain.entities.research.factor_models import (
    CONVENTIONS,
    FACTOR_MODELS,
    FREQUENCIES,
    RF,
    TOTAL,
    model_factors,
)


@dataclass
class FactorAnalysisConfig:
    model: str = "capm"
    factors: Optional[List[str]] = None              # custom model: the factor columns to use
    frequency: str = "D"
    start: Optional[str] = None
    end: Optional[str] = None
    convention: Optional[str] = None                 # None = the strategy's default
    rolling_window: Optional[int] = None
    hac: bool = True
    hac_lags: Optional[int] = None
    confidence: float = 0.95


@dataclass
class FactorAnalysisResult:
    strategy: str
    model: str
    model_label: str
    factors: List[str]
    frequency: str
    periods_per_year: int
    convention: str
    convention_note: str
    sample: Dict[str, object]
    regression: st.OLSResult
    alpha_annualised: Dict[str, float]
    contributions: pd.DataFrame                      # period x factor (beta_k F_k,t)
    series: pd.DataFrame                             # period x [strategy, factors, fitted, residual, alpha]
    cumulative: pd.DataFrame                         # strategy (compounded) and additive factor / residual parts
    rolling: Optional[pd.DataFrame]
    residual_stats: Dict[str, Optional[float]]
    outliers: pd.Series
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def coefficient_table(self) -> pd.DataFrame:
        return self.regression.table()


class FactorDataMissing(Exception):
    """The factor returns needed for this analysis are not available (never fabricated)."""


def prepare(strategy: StrategyReturns, factor_frame: pd.DataFrame, cfg: FactorAnalysisConfig):
    """(y, X, rf_used, sample info, notes) on the aligned periods of the analysis frequency."""
    if cfg.frequency not in FREQUENCIES:
        raise ValueError(f"unknown frequency '{cfg.frequency}' (use {sorted(FREQUENCIES)})")
    factors = model_factors(cfg.model, cfg.factors)
    missing = [f for f in factors if f not in factor_frame.columns]
    if missing:
        raise FactorDataMissing(f"the factor data has no {missing} (columns: {list(factor_frame.columns)})")
    convention = cfg.convention or strategy.convention
    if convention not in CONVENTIONS:
        raise ValueError(f"unknown return convention '{convention}'")
    needs_rf = convention == TOTAL
    if needs_rf and RF not in factor_frame.columns:
        raise FactorDataMissing("the strategy reports total returns but the factor data has no risk-free rate (RF): "
                                "it cannot be turned into an excess return")
    r = strategy.returns.copy()
    if cfg.start:
        r = r[r.index >= pd.Timestamp(cfg.start)]
    if cfg.end:
        r = r[r.index <= pd.Timestamp(cfg.end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)]
    y_raw = st.compound_to(r, cfg.frequency)
    cols = factors + ([RF] if needs_rf else [])
    f = factor_frame[cols].copy()
    f = pd.DataFrame({c: st.compound_to(f[c], cfg.frequency) for c in cols})
    joined = pd.concat([y_raw.rename("__y__"), f], axis=1)
    strategy_periods = int(y_raw.notna().sum())
    usable = joined.dropna()
    sample = {
        "strategy_periods": strategy_periods,
        "factor_periods_in_range": int(f.loc[(f.index >= y_raw.index.min()) & (f.index <= y_raw.index.max())]
                                       .dropna().shape[0]) if len(y_raw) else 0,
        "aligned_periods": int(len(usable)),
        "strategy_periods_without_factor_data": int(y_raw.index.difference(usable.index).size),
        "first": str(usable.index.min().date()) if len(usable) else None,
        "last": str(usable.index.max().date()) if len(usable) else None,
        "strategy_first": str(y_raw.index.min().date()) if len(y_raw) else None,
        "strategy_last": str(y_raw.index.max().date()) if len(y_raw) else None,
        "factor_last": str(factor_frame.index.max().date()) if len(factor_frame) else None,
    }
    y = usable["__y__"] - (usable[RF] if needs_rf else 0.0)
    notes = [CONVENTIONS[convention],
             f"Returns compounded to {FREQUENCIES[cfg.frequency][0]} periods; periods without data are dropped, "
             f"nothing is filled."]
    if strategy.bar_minutes:
        notes.append(f"The strategy trades {strategy.bar_minutes}-minute bars; its bar returns are compounded "
                     f"by the date they are realised on.")
    return y, usable[factors], needs_rf, sample, notes, convention


def analyse(strategy: StrategyReturns, factor_frame: pd.DataFrame, cfg: FactorAnalysisConfig) -> FactorAnalysisResult:
    y, X, needs_rf, sample, notes, convention = prepare(strategy, factor_frame, cfg)
    k = X.shape[1] + 1
    warnings = []
    if sample["aligned_periods"] <= k + 1:
        last_factor = sample["factor_last"]
        raise FactorDataMissing(
            f"only {sample['aligned_periods']} aligned period(s) for {k} parameters: the strategy covers "
            f"{sample['strategy_first']} .. {sample['strategy_last']} and the factor data ends {last_factor}")
    if sample["strategy_periods_without_factor_data"]:
        warnings.append(f"{sample['strategy_periods_without_factor_data']} of {sample['strategy_periods']} strategy "
                        f"periods have no factor data (factor data ends {sample['factor_last']}) and are excluded")
    ppy = FREQUENCIES[cfg.frequency][1]
    min_obs = max(30, 10 * k)
    res = st.ols(y, X, hac=cfg.hac, lags=cfg.hac_lags, confidence=cfg.confidence, min_obs=min_obs)
    warnings += res.warnings
    a_idx = res.names.index("alpha")
    alpha_ann = {"alpha": float(res.coef[a_idx] * ppy), "ci_low": float(res.ci_low[a_idx] * ppy),
                 "ci_high": float(res.ci_high[a_idx] * ppy), "t": float(res.t[a_idx]), "p_value": float(res.p[a_idx]),
                 "method": f"arithmetic: alpha per period x {ppy}"}
    betas = dict(zip(res.names[1:], res.coef[1:]))
    index = res.residuals.index
    contributions = pd.DataFrame({f: betas[f] * X.loc[index, f] for f in X.columns}, index=index)
    series = pd.DataFrame({"strategy": y.loc[index], **{f: X.loc[index, f] for f in X.columns},
                           "fitted": res.fitted, "residual": res.residuals, "alpha": res.coef[a_idx]})
    cumulative = pd.DataFrame({
        "strategy (compounded)": (1.0 + y.loc[index]).cumprod() - 1.0,
        "factor part (additive)": contributions.sum(axis=1).cumsum(),
        "alpha (additive)": pd.Series(res.coef[a_idx], index=index).cumsum(),
        "residual (additive)": res.residuals.cumsum(),
    })
    rolling = None
    sample["rolling_window"] = cfg.rolling_window
    if cfg.rolling_window:
        try:
            rolling = st.rolling_ols(y, X, cfg.rolling_window, confidence=cfg.confidence)
        except ValueError as e:
            warnings.append(f"rolling regression skipped: {e}")
    resid = res.residuals
    residual_stats = {"std": float(resid.std(ddof=1)), "annualised_std": float(resid.std(ddof=1) * np.sqrt(ppy)),
                      **res.diagnostics}
    notes.append("Regression-based attribution is a model-based decomposition, not causal attribution.")
    notes.append(f"Standard errors: {'Newey-West HAC, ' + str(res.hac_lags) + ' lags' if res.hac else 'classical OLS'};"
                 f" t / p / {int(cfg.confidence * 100)}% intervals from Student t with {res.df} degrees of freedom.")
    label = FACTOR_MODELS[cfg.model][0] if cfg.model in FACTOR_MODELS else "Custom factor model"
    return FactorAnalysisResult(
        strategy=strategy.name, model=cfg.model, model_label=label, factors=list(X.columns), frequency=cfg.frequency,
        periods_per_year=ppy, convention=convention, convention_note=CONVENTIONS[convention], sample=sample,
        regression=res, alpha_annualised=alpha_ann, contributions=contributions, series=series,
        cumulative=cumulative, rolling=rolling, residual_stats=residual_stats, outliers=st.outliers(resid),
        warnings=warnings, notes=notes)


def compare(strategies: List[StrategyReturns], factor_frame: pd.DataFrame, cfg: FactorAnalysisConfig) -> Dict:
    """The same model on several strategies over their COMMON aligned periods (one sample for all)."""
    prepared = {}
    for s in strategies:
        try:
            y, X, *_ = prepare(s, factor_frame, cfg)
            prepared[s.name] = (s, y)
        except (FactorDataMissing, ValueError) as e:
            prepared[s.name] = (s, e)
    common = None
    for name, (s, y) in prepared.items():
        if isinstance(y, Exception):
            continue
        common = y.index if common is None else common.intersection(y.index)
    rows, skipped = {}, {n: str(v[1]) for n, v in prepared.items() if isinstance(v[1], Exception)}
    if common is None or len(common) == 0:
        return {"rows": pd.DataFrame(), "periods": 0, "skipped": skipped}
    for name, (s, y) in prepared.items():
        if isinstance(y, Exception):
            continue
        sub = StrategyReturns(s.name, s.returns, s.convention, s.bar_minutes, s.source)
        c = FactorAnalysisConfig(**{**cfg.__dict__, "rolling_window": None})
        try:
            r = analyse(sub, factor_frame, c)
        except (FactorDataMissing, ValueError) as e:
            skipped[name] = str(e)
            continue
        # restrict to the common periods
        res = st.ols(r.series.loc[common, "strategy"], r.series.loc[common, r.factors], hac=cfg.hac,
                     lags=cfg.hac_lags, confidence=cfg.confidence, min_obs=0)
        wealth = (1.0 + r.series.loc[common, "strategy"]).cumprod()
        row = {"alpha (annualised)": res.coef[0] * r.periods_per_year, "alpha t": res.t[0], "R2": res.r2,
               "adj R2": res.adj_r2, "cumulative excess return": float(wealth.iloc[-1] - 1.0),
               "max drawdown": float(-(wealth / wealth.cummax() - 1.0).min()), "convention": r.convention}
        row.update({f"beta {n}": c for n, c in zip(res.names[1:], res.coef[1:])})
        rows[name] = row
    return {"rows": pd.DataFrame.from_dict(rows, orient="index"), "periods": int(len(common)), "skipped": skipped,
            "first": str(common.min().date()), "last": str(common.max().date())}
