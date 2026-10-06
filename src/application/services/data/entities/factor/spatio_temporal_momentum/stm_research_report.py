"""
STM research report — the tables and figures of Tan, Roberts & Zohren (2023),
"Spatio-Temporal Momentum", computed from what the engine actually decided.

Everything here runs AFTER a backtest (evaluation only): realised next-day
returns may be read, they never fed a decision.

Paper item                         -> field
  Table 1  raw signal metrics      -> table_raw
  Table 2  rescaled to target vol  -> table_rescaled
  Figure 1 cumulative returns      -> cumulative (rescaled)
  Figure 3 correlations            -> correlation, rolling_correlation
  Table 6  Sharpe vs costs         -> table_costs
  Figure 4 average turnover        -> turnover
  Figure 5 SHAP, single asset      -> shap (+ shap_asset)
  Figure 6 mean |SHAP|, all assets -> shap

Strategies (paper section 3): Long Only, TSMOM (sign of the longest return
horizon), MACD (Baz et al. response over the configured MACD pairs), CSMOM
(decile long/short on the longest return horizon) and the STM model.  The DMN
reference model is not part of this project and is not reported.

SHAP: the paper uses Deep SHAP.  The `shap` package is not a project
dependency, so SHAP values are computed with Expected Gradients (the method of
shap.GradientExplainer): phi = E[(x - x') * grad f(x' + a (x - x'))],
x' drawn from the model's training inputs, a ~ U(0, 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    STMArtifactStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    captured_returns,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    align_close_panel,
    build_feature_panel,
)

ANN = 252
COST_SCENARIOS_BPS = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0)
METRIC_COLUMNS = ["E[Return]", "Vol.", "Downside Deviation", "MDD", "Sharpe", "Sortino", "Calmar",
                  "Hit Rate", "Ave. P / Ave. L"]


@dataclass
class ShapResult:
    values: np.ndarray            # [S, N_out, P]  SHAP of every input feature for every output asset
    inputs: np.ndarray            # [S, P]         feature values of the explained samples
    feature_names: List[str]      # P names "<ASSET>_t-<lag>_<feature>"
    output_assets: List[str]      # N_out
    artifact_id: Optional[int] = None
    method: str = "Expected Gradients (shap.GradientExplainer formulation)"


@dataclass
class STMResearchReport:
    model_name: str
    period: tuple
    n_sessions: int
    assets: List[str]
    raw_returns: pd.DataFrame          # date x strategy (Eq. 1, no costs)
    rescaled_returns: pd.DataFrame     # date x strategy, portfolio vol-targeted
    table_raw: pd.DataFrame
    table_rescaled: pd.DataFrame
    table_costs: pd.DataFrame          # strategy x cost (bps) -> Sharpe (rescaled)
    cumulative: pd.DataFrame
    correlation: pd.DataFrame
    rolling_correlation: pd.DataFrame
    rolling_window: int
    turnover: pd.DataFrame             # date x strategy, average turnover across assets (Eq. 12)
    shap: Optional[ShapResult] = None
    shap_asset: Optional[str] = None
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metrics (paper section 5.4, annualised)
# ---------------------------------------------------------------------------

def strategy_metrics(r: pd.Series) -> Dict[str, float]:
    r = pd.Series(r).dropna()
    if len(r) < 2:
        return {c: float("nan") for c in METRIC_COLUMNS}
    mean_ann = r.mean() * ANN
    vol = r.std(ddof=1) * math.sqrt(ANN)
    downside = math.sqrt(np.mean(np.minimum(r, 0.0) ** 2)) * math.sqrt(ANN)
    wealth = np.concatenate([[1.0], np.cumprod(1.0 + r.to_numpy())])
    mdd = float(-np.min(wealth / np.maximum.accumulate(wealth) - 1.0))
    gains, losses = r[r > 0], r[r < 0]
    return {
        "E[Return]": mean_ann,
        "Vol.": vol,
        "Downside Deviation": downside,
        "MDD": mdd,
        "Sharpe": mean_ann / vol if vol > 0 else float("nan"),
        "Sortino": mean_ann / downside if downside > 0 else float("nan"),
        "Calmar": mean_ann / mdd if mdd > 0 else float("nan"),
        "Hit Rate": float((r > 0).mean()),
        "Ave. P / Ave. L": (gains.mean() / abs(losses.mean())) if len(gains) and len(losses) else float("nan"),
    }


def metrics_table(returns: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({c: strategy_metrics(returns[c]) for c in returns.columns}).T[METRIC_COLUMNS]


def rescale_to_target_vol(r: pd.Series, target_vol: float, span: int) -> pd.Series:
    """Portfolio-level vol targeting with an ex-ante (lagged) EWM volatility estimate."""
    ex_ante = r.ewm(span=span, min_periods=span).std().shift(1) * math.sqrt(ANN)
    return (r * target_vol / ex_ante).dropna()


def average_turnover(positions: np.ndarray, vols: np.ndarray, target_vol: float) -> np.ndarray:
    """Eq. 12 averaged over assets: sigma_tgt * |X_t/sigma_t - X_{t-1}/sigma_{t-1}|."""
    ann = vols * math.sqrt(ANN)
    to = target_vol * np.abs(np.diff(positions / (ann + 1e-12), axis=0))
    return to.mean(axis=1)


# ---------------------------------------------------------------------------
# Benchmark positions (paper section 3)
# ---------------------------------------------------------------------------

def benchmark_positions(features: np.ndarray, feature_names: List[str], longest_return_name: str,
                        macd_names: List[str]) -> Dict[str, np.ndarray]:
    """features: [S, N, F] at each decision date."""
    s, n, _ = features.shape
    longest = features[:, :, feature_names.index(longest_return_name)]
    out = {"Long Only": np.ones((s, n)), "TSMOM": np.sign(longest)}
    if macd_names:
        y = np.mean([features[:, :, feature_names.index(m)] for m in macd_names], axis=0)
        out["MACD"] = y * np.exp(-(y ** 2) / 4.0) / 0.89
    k = max(1, int(round(0.1 * n)))
    order = np.argsort(longest, axis=1)
    cs = np.zeros((s, n))
    rows = np.arange(s)[:, None]
    cs[rows, order[:, -k:]] = 1.0
    cs[rows, order[:, :k]] = -1.0
    out["CSMOM"] = cs
    return out


# ---------------------------------------------------------------------------
# SHAP (Expected Gradients)
# ---------------------------------------------------------------------------

def expected_gradients(model: torch.nn.Module, X: np.ndarray, background: np.ndarray,
                       n_draws: int = 16, seed: int = 0, chunk: int = 256) -> np.ndarray:
    """
    SHAP values of every input for every output: [S, N_out, N, T, F].
    X, background: [*, N, T, F].
    """
    rng = np.random.default_rng(seed)
    model.eval()
    s = len(X)
    bg_idx = rng.integers(0, len(background), size=(s, n_draws))
    alphas = rng.random((s, n_draws))
    x = np.repeat(X[:, None], n_draws, axis=1)                      # [S, D, N, T, F]
    xb = background[bg_idx]                                          # [S, D, N, T, F]
    a = alphas[..., None, None, None]
    points = torch.tensor((xb + a * (x - xb)).reshape(-1, *X.shape[1:]), dtype=torch.float32)
    delta = (x - xb).reshape(-1, *X.shape[1:])

    n_out = None
    grads_all = []
    for start in range(0, len(points), chunk):
        p = points[start:start + chunk].clone().requires_grad_(True)
        out = model(p)                                               # [B, N_out]
        n_out = out.shape[1]
        g = []
        for k in range(n_out):
            (gk,) = torch.autograd.grad(out[:, k].sum(), p, retain_graph=k < n_out - 1)
            g.append(gk.detach().numpy())
        grads_all.append(np.stack(g, axis=1))                        # [B, N_out, N, T, F]
    grads = np.concatenate(grads_all)                                # [S*D, N_out, N, T, F]
    phi = grads * delta[:, None]
    return phi.reshape(s, n_draws, n_out, *X.shape[1:]).mean(axis=1)


def _shap_for_artifact(loaded, closes: pd.DataFrame, sessions: List[pd.Timestamp],
                       max_samples: int, n_draws: int) -> Optional[ShapResult]:
    meta = loaded.metadata
    cfg = loaded.config
    assets = loaded.assets
    start = pd.Timestamp(meta["history_start"])
    window = closes.loc[start:, assets] if all(a in closes for a in assets) else None
    if window is None:
        return None
    aligned, _ = align_close_panel(window)
    panel = build_feature_panel(aligned, cfg.features, cfg.prediction_horizon, assets=assets)
    T = cfg.model.lookback
    scaler = loaded.scaler

    def x_at(i):
        f = panel.features if not scaler else (panel.features - np.asarray(scaler["a"])) / np.asarray(scaler["b"])
        return f[i - T + 1:i + 1].transpose(1, 0, 2)

    valid = lambda i: i - T + 1 >= panel.first_valid_row and not np.isnan(panel.features[i - T + 1:i + 1]).any()
    val_end = pd.Timestamp(meta["validation_end"])
    explain_rows = [panel.dates.get_loc(d) for d in sessions if d in panel.dates]
    explain_rows = [i for i in explain_rows if valid(i)][-max_samples:]
    bg_rows = [i for i in range(len(panel.dates)) if panel.dates[i] <= val_end and valid(i)]
    if not explain_rows or not bg_rows:
        return None
    X = np.stack([x_at(i) for i in explain_rows])
    B = np.stack([x_at(i) for i in bg_rows])
    phi = expected_gradients(loaded.model, X, B, n_draws=n_draws)    # [S, N_out, N, T, F]
    s, n_out, n, t, f = phi.shape
    names = [f"{assets[a]}_t-{t - j}_{panel.feature_names[k]}"
             for a in range(n) for j in range(t) for k in range(f)]
    return ShapResult(values=phi.reshape(s, n_out, n * t * f), inputs=X.reshape(s, n * t * f),
                      feature_names=names, output_assets=list(assets), artifact_id=loaded.artifact_id)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(cycle_results: List[Any], closes: pd.DataFrame, config: STMConfiguration,
                 factory=None, shap_asset: Optional[str] = None, shap_samples: int = 40,
                 shap_draws: int = 12, rolling_window: Optional[int] = None) -> Optional[STMResearchReport]:
    decided = [r for r in cycle_results if getattr(r, "scores", None) and r.session is not None]
    if not decided:
        return None
    aligned, _ = align_close_panel(closes)
    panel = build_feature_panel(aligned, config.features, config.prediction_horizon)
    by_session = {r.session: r for r in decided}
    rows = [panel.dates.get_loc(s) for s in sorted(by_session) if s in panel.dates]
    rows = [i for i in rows if not np.isnan(panel.target[i]).any() and not np.isnan(panel.features[i]).any()]
    if len(rows) < 3:
        return None
    dates = panel.dates[rows]
    labels, vols = panel.target[rows], panel.daily_vol[rows]
    feats = panel.features[rows]
    tgt = config.training.target_vol

    model_name = f"STM ({config.model.model_type.upper()})"
    stm = np.array([[by_session[panel.dates[i]].scores.get(a, 0.0) for a in panel.assets] for i in rows])
    names = config.features.feature_names()
    longest = config.features.return_feature_names()[int(np.argmax(config.features.return_horizons))]
    positions = {**benchmark_positions(feats, names, longest, config.features.macd_feature_names()),
                 model_name: stm}

    raw = pd.DataFrame({k: captured_returns(p, labels, vols, 0.0, tgt) for k, p in positions.items()}, index=dates)
    span = config.features.vol_lookback
    rescaled = pd.DataFrame({k: rescale_to_target_vol(raw[k], tgt, span) for k in raw}).dropna()

    costs = {}
    for k, p in positions.items():
        costs[k] = {}
        for c in COST_SCENARIOS_BPS:
            net = pd.Series(captured_returns(p, labels, vols, c, tgt), index=dates)
            costs[k][c] = strategy_metrics(rescale_to_target_vol(net, tgt, span))["Sharpe"]
    table_costs = pd.DataFrame(costs).T
    table_costs.columns = [f"{c:g}" for c in COST_SCENARIOS_BPS]

    turnover = pd.DataFrame({k: average_turnover(p, vols, tgt) for k, p in positions.items()}, index=dates[1:])

    window = rolling_window or max(20, min(ANN, len(rescaled) // 3))
    others = [c for c in ("TSMOM", "CSMOM", "MACD") if c in rescaled]
    rolling = pd.DataFrame({f"{model_name}-{o}": rescaled[model_name].rolling(window).corr(rescaled[o])
                            for o in others})

    shap_res = None
    notes = [
        "DMN (reference model of the paper) is not implemented in this project and is not reported.",
        f"TSMOM / CSMOM use the longest configured return horizon ({max(config.features.return_horizons)} days); "
        "the paper uses 252 days.",
        f"Rescaled results target {tgt:.0%} annualised volatility with an ex-ante {span}-day EWM estimate.",
        f"Rolling correlations use a {window}-session window (paper: 1 year).",
    ]
    if factory is not None:
        store = STMArtifactStore(factory, config)
        chosen = {d: store.select(d) for d in dates}
        used: Dict[int, list] = {}
        artifacts = {}
        for d, sel in chosen.items():
            if sel is not None:
                used.setdefault(sel[0].id, []).append(d)
                artifacts[sel[0].id] = sel[0]
        if used:
            # explain the model that made the most decisions (ties -> most recent)
            best = max(used, key=lambda a: (len(used[a]), max(used[a])))
            loaded = store.load(artifacts[best])
            shap_res = _shap_for_artifact(loaded, closes, used[best], shap_samples, shap_draws)
            notes.append("SHAP values: Expected Gradients (shap.GradientExplainer formulation); the paper uses Deep SHAP.")
    if shap_res is not None and (shap_asset is None or shap_asset not in shap_res.output_assets):
        shap_asset = "BAC" if "BAC" in shap_res.output_assets else shap_res.output_assets[0]

    return STMResearchReport(
        model_name=model_name,
        period=(str(dates[0].date()), str(dates[-1].date())),
        n_sessions=len(dates),
        assets=list(panel.assets),
        raw_returns=raw,
        rescaled_returns=rescaled,
        table_raw=metrics_table(raw),
        table_rescaled=metrics_table(rescaled),
        table_costs=table_costs,
        cumulative=(1.0 + rescaled).cumprod(),
        correlation=rescaled.corr(),
        rolling_correlation=rolling,
        rolling_window=window,
        turnover=turnover,
        shap=shap_res,
        shap_asset=shap_asset,
        notes=notes,
    )
