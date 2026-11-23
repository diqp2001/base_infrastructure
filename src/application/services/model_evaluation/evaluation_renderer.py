"""
Figures and tables of a classifier evaluation for the PowerBuffet page (server-side matplotlib -> base64 PNG, the
convention of research/research_renderer). Presentation only: every number comes from the evaluation results.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.research import research_renderer as rr
from src.application.services.research.research_renderer import plt
from src.domain.entities.ml.classifier_evaluation import class_label


def _heatmap(values: np.ndarray, row_labels: List[str], col_labels: List[str], title: str, xlabel: str,
             ylabel: str, cmap: str, vmin: float, vmax: float, fmt):
    fig, ax = plt.subplots(figsize=(1.1 * len(col_labels) + 2.2, 0.8 * len(row_labels) + 1.6))
    shown = np.where(np.isfinite(values), values, np.nan)
    im = ax.imshow(shown, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(col_labels)), col_labels)
    ax.set_yticks(range(len(row_labels)), row_labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    span = vmax - vmin
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            if not np.isfinite(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color="#6c757d")
                continue
            dark = abs(v - (vmin + vmax) / 2) > 0.3 * span if cmap != "Blues" else (v - vmin) > 0.6 * span
            ax.text(j, i, fmt(v), ha="center", va="center", fontsize=8, color="white" if dark else "#212529")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def fig_confusion(result, normalised: bool = False):
    labels = [class_label(k, result.classes) for k in result.classes]
    if normalised:
        values = np.array([[np.nan if v is None else v for v in row] for row in result.row_normalised()], dtype=float)
        return _heatmap(values, [f"true {x}" for x in labels], [f"pred {x}" for x in labels],
                        "True vs predicted class (share of each true class)", "predicted class", "true class",
                        "Blues", 0.0, 1.0, lambda v: f"{v:.0%}")
    values = np.array(result.confusion_matrix, dtype=float)
    return _heatmap(values, [f"true {x}" for x in labels], [f"pred {x}" for x in labels],
                    "True vs predicted class (counts)", "predicted class", "true class", "Blues", 0.0,
                    max(float(values.max()), 1.0), lambda v: f"{int(v)}")


def fig_correlation(analysis):
    c = analysis.correlation
    if c is None or c.empty:
        return None
    return _heatmap(c.to_numpy(dtype=float), list(c.index), list(c.columns),
                    f"Correlation of the P(class {analysis.target_class}) quintile return series",
                    "probability quintile", "probability quintile", "RdBu_r", -1.0, 1.0, lambda v: f"{v:.2f}")


def fig_cumulative(analysis):
    if analysis.cumulative is None or analysis.cumulative.empty:
        return None
    cum = analysis.cumulative.copy()
    title = (f"Cumulative realised return of the P(class {analysis.target_class}) quintiles "
             f"(equal weight, {analysis.horizon}-bar forward returns" +
             (", non-overlapping dates)" if analysis.horizon > 1 else ")"))
    return rr.fig_series(cum, title, ylabel="cumulative return")


def figures(evaluation, target_class: Optional[int]) -> Dict[str, Optional[str]]:
    out = {"confusion_counts": rr.png(fig_confusion(evaluation.classification)),
           "confusion_share": rr.png(fig_confusion(evaluation.classification, normalised=True))}
    analysis = evaluation.probability_quintiles.get(target_class) if target_class is not None else None
    if analysis is not None:
        f = fig_cumulative(analysis)
        out["cumulative"] = rr.png(f) if f is not None else None
        f = fig_correlation(analysis)
        out["correlation"] = rr.png(f) if f is not None else None
    return out


def per_class_table(result) -> pd.DataFrame:
    rows = {class_label(c.label, result.classes): {"support (true)": c.support, "predicted": c.predicted,
                                                   "precision": c.precision, "recall": c.recall, "F1": c.f1}
            for c in result.per_class}
    return pd.DataFrame(rows).T


def confusion_table(result, normalised: bool = False) -> pd.DataFrame:
    labels = [class_label(k, result.classes) for k in result.classes]
    data = result.row_normalised() if normalised else result.confusion_matrix
    return pd.DataFrame([[np.nan if v is None else v for v in row] for row in data],
                        index=[f"true {x}" for x in labels], columns=[f"pred {x}" for x in labels])


def probability_overview(evaluation) -> pd.DataFrame:
    """One row per class probability: spread Qn - Q1, monotonicity, observations."""
    rows = {}
    for k, a in evaluation.probability_quintiles.items():
        s = a.summary
        if s is None or s.empty:
            continue
        rows[f"P({class_label(k, evaluation.classes)})"] = {
            "mean Q1": s["mean_forward_return"].iloc[0], f"mean Q{a.n_quantiles}": s["mean_forward_return"].iloc[-1],
            f"Q{a.n_quantiles} - Q1": s["mean_forward_return"].iloc[-1] - s["mean_forward_return"].iloc[0],
            "monotonicity (Spearman)": a.monotonicity, "dates": int(s["dates"].max())}
    return pd.DataFrame(rows).T
