"""
Results report of a cross-sectional momentum run, built after the run from what the engine decided.

Performance   each decision's weights earn the next session's close-to-close returns (the convention of the STM
              report); benchmarks on the same sessions: equal-weight long-only of the eligible assets and a
              20-session momentum long/short with the same portfolio construction; cost scenarios charge
              ``bps x turnover``. (20-session return = the return_20d factor.)
Quintiles     per decision the scored assets are split into 5 equal-count buckets by predicted probability
              (Q1 = lowest .. Q5 = highest); each bucket earns the equal-weight next-session return of its
              names: cumulative return per quintile and Q5 - Q1 (does the ranking order the returns?).
Prediction    per decision: AUC of the probabilities against the realised label (next return above the
              cross-sectional median), accuracy, top-minus-bottom quantile spread.
Features      gain share of the models used (weighted by the decisions they scored), mean |TreeSHAP| at the
              decisions, how often each feature was in the best Optuna trial and among the top trials; one row per
              retraining (window, CV score, selected features, parameters); Optuna trial histories and
              hyper-parameter importances.
Coverage      stm_data_coverage against the NYSE calendar (history + backtest windows).

Bars: daily by default; with ``config.bar_minutes`` (e.g. 10) every "session" above is a bar of that size, the
returns are bar-to-bar and the metrics are annualised with 252 x bars per session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import build_dataset
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    long_short_weights,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_data_coverage import data_coverage
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import periods_per_year
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    METRIC_COLUMNS,
    strategy_metrics,
)

COST_SCENARIOS_BPS = (0.0, 1.0, 2.0, 5.0, 10.0, 20.0)
N_QUANTILES = 5
SPREAD = "Q5 - Q1"
MODEL_NAME = "CSM (LightGBM + Optuna TPE)"


@dataclass
class CSMReport:
    model_name: str
    period: tuple
    n_sessions: int
    assets: List[str]
    returns: pd.DataFrame                  # session x strategy, net of nothing
    cumulative: pd.DataFrame
    table_performance: pd.DataFrame        # strategy x metric
    table_costs: pd.DataFrame              # strategy x cost (bps) -> Sharpe
    table_prediction: pd.DataFrame         # metric -> Value
    table_importance: pd.DataFrame         # feature x importance measure
    table_retrainings: pd.DataFrame        # one row per retraining
    table_param_importance: pd.DataFrame   # parameter x retraining (Optuna importances)
    selection_matrix: pd.DataFrame         # retraining x feature (1 = selected by the best trial)
    trial_histories: Dict[str, List[Optional[float]]]
    turnover: pd.Series
    notes: List[str] = field(default_factory=list)
    coverage_summary: Optional[pd.DataFrame] = None
    coverage_assets: Optional[pd.DataFrame] = None
    coverage_by_session: Optional[pd.Series] = None
    # equal-weight next-session return of each score quintile (Q1 lowest .. Q5 highest) and Q5 - Q1;
    # None in reports stored before 2026-10-26
    quintile_returns: Optional[pd.DataFrame] = None
    quintile_cumulative: Optional[pd.DataFrame] = None
    table_quintiles: Optional[pd.DataFrame] = None


def _turnover(weights: List[Dict[str, float]]) -> np.ndarray:
    out, prev = [], {}
    for w in weights:
        names = set(w) | set(prev)
        out.append(sum(abs(w.get(a, 0.0) - prev.get(a, 0.0)) for a in names))
        prev = w
    return np.asarray(out)


def _realised(weights: Dict[str, float], fwd: pd.Series) -> float:
    return float(sum(w * fwd.get(a, 0.0) for a, w in weights.items() if np.isfinite(fwd.get(a, np.nan))))


def quantile_labels(n: int = N_QUANTILES) -> List[str]:
    return [f"Q{i + 1}" + (" (lowest)" if i == 0 else " (highest)" if i == n - 1 else "") for i in range(n)]


def quantile_returns(decided: List[Any], one_day: pd.DataFrame, n: int = N_QUANTILES) -> pd.DataFrame:
    """session x [Q1 (lowest) .. Qn (highest), Qn - Q1]: per decision, the assets scored that have a next-session
    return are ranked by probability and cut into ``n`` equal-count buckets (ties broken by order); each bucket
    earns the equal-weight mean of its names' next-session returns. A decision with fewer than ``n`` such assets
    gives NaN."""
    labels = quantile_labels(n)
    rows = {}
    for r in decided:
        fwd = one_day.loc[r.session]
        names = [a for a in r.scores if np.isfinite(fwd.get(a, np.nan)) and np.isfinite(r.scores[a])]
        if len(names) < n:
            rows[pd.Timestamp(r.session)] = [np.nan] * (n + 1)
            continue
        scores = pd.Series({a: r.scores[a] for a in names})
        bucket = pd.qcut(scores.rank(method="first"), n, labels=False)
        means = fwd[names].groupby(bucket).mean().reindex(range(n))
        rows[pd.Timestamp(r.session)] = list(means.to_numpy()) + [float(means.iloc[-1] - means.iloc[0])]
    return pd.DataFrame.from_dict(rows, orient="index", columns=labels + [f"Q{n} - Q1"])


def quantile_table(returns: pd.DataFrame, periods: int = 252) -> pd.DataFrame:
    """Metrics per quintile (and the spread) plus the cumulative return over the run; ``periods`` = bars per year."""
    table = pd.DataFrame({c: strategy_metrics(returns[c], periods) for c in returns}).T[METRIC_COLUMNS]
    table.insert(0, "Cumulative return", [float((1.0 + returns[c].dropna()).prod() - 1.0) for c in returns])
    return table


def _decisions(cycle_results: List[Any]) -> List[Any]:
    seen, out = set(), []
    for r in cycle_results:
        if getattr(r, "session", None) is None or not getattr(r, "weights", None):
            continue
        if r.session in seen:
            continue
        seen.add(r.session)
        out.append(r)
    return out


def build_report(cycle_results: List[Any], closes: pd.DataFrame, config: CSMConfiguration,
                 artifacts: Dict[int, Dict[str, Any]], history_start=None, feature_engine=None) -> Optional[CSMReport]:
    """``artifacts`` = {artifact id: metadata} of the models trained / used during the run."""
    decided = _decisions(cycle_results)
    closes = closes.sort_index()
    periods = periods_per_year(config.bar_minutes)                 # 252 daily, 252 x 39 for 10-minute bars
    unit = "bar" if config.bar_minutes else "session"
    sessions = list(closes.index)
    nxt = {s: sessions[i + 1] for i, s in enumerate(sessions[:-1])}
    decided = [r for r in decided if r.session in nxt]
    if len(decided) < 2:
        return None
    dataset = build_dataset(closes, config.features, config.label, feature_engine)
    dates = pd.DatetimeIndex([r.session for r in decided])
    one_day = closes.shift(-1) / closes - 1.0                       # next-session return from each session

    model_w = [r.weights for r in decided]
    ew_w, mom_w = [], []
    mom_feature = "return_20d" if "return_20d" in dataset.feature_names else dataset.feature_names[0]
    for r in decided:
        eligible = [a for a in r.eligible if a in closes.columns]
        ew_w.append({a: 1.0 / len(eligible) for a in eligible} if eligible else {})
        rows = dataset.rows_on(r.session)
        rows = rows[rows.index.isin(eligible)].dropna(subset=[mom_feature, "daily_vol"])
        mom_w.append(long_short_weights(rows[mom_feature].to_dict(), rows["daily_vol"].to_dict(),
                                        config.training.long_short_quantile, config.training.gross_exposure))
    strategies = {MODEL_NAME: model_w, "Long Only (EW)": ew_w, "Momentum 20d L/S": mom_w}
    returns = pd.DataFrame({name: [_realised(w, one_day.loc[r.session]) for w, r in zip(ws, decided)]
                            for name, ws in strategies.items()}, index=dates)
    turnovers = {name: _turnover(ws) for name, ws in strategies.items()}

    perf = pd.DataFrame({k: strategy_metrics(returns[k], periods) for k in returns}).T[METRIC_COLUMNS]
    perf["Ave. Turnover"] = [float(np.mean(turnovers[k][1:])) if len(turnovers[k]) > 1 else float("nan")
                             for k in perf.index]
    costs = pd.DataFrame({
        k: {f"{c:g}": strategy_metrics(returns[k] - c * 1e-4 * turnovers[k], periods)["Sharpe"] for c in COST_SCENARIOS_BPS}
        for k in returns}).T

    # prediction quality
    from sklearn.metrics import roc_auc_score
    aucs, accs, spreads = [], [], []
    for r in decided:
        fwd = one_day.loc[r.session]
        names = [a for a in r.scores if np.isfinite(fwd.get(a, np.nan))]
        if len(names) < 4:
            continue
        realised = fwd[names]
        y = (realised > realised.median()).astype(int).to_numpy()
        p = np.array([r.scores[a] for a in names])
        if len(np.unique(y)) == 2:
            aucs.append(roc_auc_score(y, p))
        accs.append(float(np.mean((p > np.median(p)).astype(int) == y)))
        q = config.training.long_short_quantile
        lo, hi = np.quantile(p, q), np.quantile(p, 1 - q)
        spreads.append(float(realised[p >= hi].mean() - realised[p <= lo].mean()))
    prediction = pd.DataFrame({"Value": pd.Series({
        "Decisions evaluated": len(accs),
        "Mean AUC (vs realised above-median)": float(np.mean(aucs)) if aucs else float("nan"),
        "Share of decisions with AUC > 0.5": float(np.mean(np.asarray(aucs) > 0.5)) if aucs else float("nan"),
        "Accuracy (prob. above / below the median)": float(np.mean(accs)) if accs else float("nan"),
        f"Mean top-minus-bottom next-{unit} return": float(np.mean(spreads)) if spreads else float("nan"),
        "t-stat of the spread": (float(np.mean(spreads) / (np.std(spreads, ddof=1) / np.sqrt(len(spreads))))
                                 if len(spreads) > 2 and np.std(spreads, ddof=1) > 0 else float("nan")),
    }, dtype=object)})

    quintiles = quantile_returns(decided, one_day)

    # feature importance
    candidates = config.features.feature_names()
    used_counts: Dict[int, int] = {}
    for r in decided:
        if r.artifact_id is not None:
            used_counts[r.artifact_id] = used_counts.get(r.artifact_id, 0) + 1
    metas = {aid: m for aid, m in artifacts.items()}
    total_used = sum(used_counts.values()) or 1
    gain = {f: sum(metas[a].get("gain_importance", {}).get(f, 0.0) * n for a, n in used_counts.items()
                   if a in metas) / total_used for f in candidates}
    shap = {f: float(np.mean([r.shap.get(f, 0.0) for r in decided])) for f in candidates}
    trained = sorted(metas.items(), key=lambda am: (am[1]["trained_as_of"], am[0]))
    selected = {f: float(np.mean([f in m["features"] for _, m in trained])) if trained else float("nan")
                for f in candidates}
    top_freq = {f: float(np.mean([m.get("selection_frequency", {}).get(f, 0.0) for _, m in trained]))
                if trained else float("nan") for f in candidates}
    importance = pd.DataFrame({
        "Gain share %": pd.Series(gain) * 100.0,
        "Mean |SHAP| (log-odds)": pd.Series(shap),
        "Selected by best trial %": pd.Series(selected) * 100.0,
        "Top-trial selection %": pd.Series(top_freq) * 100.0,
    }).sort_values(["Gain share %", "Mean |SHAP| (log-odds)"], ascending=False)

    retrain_rows, selection, histories, param_imp = {}, {}, {}, {}
    for aid, m in trained:
        key = f"{m['trained_as_of']} (#{aid})"
        retrain_rows[key] = {
            "Training window": f"{m['train_start']} .. {m['train_end']}",
            "Rows": int(m.get("n_train_rows", 0)),
            f"CV {m.get('metric', 'score')}": float(m.get("cv_best_value", np.nan)),
            "Trials (pruned)": f"{m.get('n_trials')} ({m.get('n_pruned')})",
            "Features": len(m["features"]),
            "Decisions scored": int(used_counts.get(aid, 0)),
            "Selected features": ", ".join(m["features"]),
            "Parameters": ", ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}"
                                    for k, v in m.get("params", {}).items()),
        }
        selection[key] = {f: 1.0 if f in m["features"] else 0.0 for f in candidates}
        histories[key] = list(m.get("trial_values", []))
        param_imp[key] = m.get("param_importance", {})
    retrainings = pd.DataFrame.from_dict(retrain_rows, orient="index")
    selection_matrix = pd.DataFrame.from_dict(selection, orient="index").reindex(columns=candidates)
    param_table = pd.DataFrame(param_imp).fillna(0.0) if param_imp else pd.DataFrame()

    notes = [
        f"Each decision's weights earn the next {unit}'s close-to-close return (decision on the close of the "
        f"{unit}, as in the STM report); top / bottom {config.training.long_short_quantile:.0%} of the predicted "
        f"probabilities, inverse-volatility weights, dollar-neutral, gross {config.training.gross_exposure:g}.",
        f"Label: next {config.label.horizon}-{unit} return above the cross-sectional median. Optuna TPE "
        f"({config.optimization.n_trials} trials, {config.optimization.n_startup_trials} random start-up trials) "
        f"chooses the features and LightGBM parameters on {config.optimization.n_folds} purged walk-forward folds "
        f"of the {config.training.training_window_rows}-{unit} window ({config.optimization.metric}).",
        "Feature importance: gain share of the models used (weighted by decisions scored), mean |TreeSHAP| "
        "(LightGBM pred_contrib) at the decisions, and how often Optuna selected each feature.",
        "Transaction costs: bps x turnover (sum of |weight changes|) per decision.",
        f"Quintiles: at each decision the scored assets are cut into {N_QUANTILES} equal-count buckets by predicted "
        f"probability (Q1 lowest .. Q{N_QUANTILES} highest); each earns the equal-weight next-{unit} return of its "
        f"names (not the traded inverse-volatility book). A monotone Q1 < .. < Q{N_QUANTILES} order means the "
        f"ranking carries information.",
    ]
    steps = [r for r in cycle_results if getattr(r, "session", None) is not None]
    scored: Dict[str, int] = {}
    for r in decided:
        for a in r.scores:
            scored[a] = scored.get(a, 0) + 1
    universe = list(config.universe.tickers or closes.columns)
    cov = data_coverage(closes, universe, [r.session for r in steps], scored, config.bar_minutes,
                        history_start=history_start,
                        scored_per_decision=[len(getattr(r, "scores", {}) or {}) for r in steps])
    s = cov[0]["Value"]
    notes.append(f"Data coverage: {s['Coverage % — backtest']:.1f}% of the expected {'%d-minute' % config.bar_minutes if config.bar_minutes else 'daily'} bars stored in the "
                 f"backtest window, {s['Coverage % — history']:.1f}% in the history window (NYSE calendar).")

    return CSMReport(
        model_name=MODEL_NAME,
        period=(str(dates[0].date()), str(dates[-1].date())),
        n_sessions=len(dates),
        assets=universe,
        returns=returns,
        cumulative=(1.0 + returns).cumprod(),
        table_performance=perf,
        table_costs=costs,
        table_prediction=prediction,
        table_importance=importance,
        table_retrainings=retrainings,
        table_param_importance=param_table,
        selection_matrix=selection_matrix,
        trial_histories=histories,
        turnover=pd.Series(turnovers[MODEL_NAME], index=dates),
        notes=notes,
        coverage_summary=cov[0],
        coverage_assets=cov[1],
        coverage_by_session=cov[2],
        quintile_returns=quintiles,
        quintile_cumulative=(1.0 + quintiles.fillna(0.0)).cumprod(),
        table_quintiles=quantile_table(quintiles, periods),
    )
