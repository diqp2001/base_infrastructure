"""
Figures (matplotlib -> base64 PNG) and HTML tables of the factor analysis and the factor research, in the style
of the project reports (csm_report_renderer, stm_report_renderer).
"""

from __future__ import annotations

import base64
import io
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=105, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _dates(ax):
    ax.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax.xaxis.get_major_locator()))


def cell(v, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return f"{v:.{digits}g}" if abs(v) < 1e-3 or abs(v) >= 1e4 else f"{v:.{digits}f}"
    return str(v)


def table_html(df: pd.DataFrame, digits: int = 4, index_name: str = "") -> str:
    if df is None or df.empty:
        return '<p class="muted small">No data.</p>'
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = "".join(f"<tr><td>{i}</td>" + "".join(f"<td>{cell(v, digits)}</td>" for v in r) + "</tr>"
                   for i, r in zip(df.index, df.astype(object).to_numpy()))
    return (f'<table class="table table-sm mb-0"><thead><tr><th>{index_name}</th>{head}</tr></thead>'
            f"<tbody>{rows}</tbody></table>")


# ── factor analysis ──────────────────────────────────────────────────────────────────────────────────────────────

def coefficient_frame(result) -> pd.DataFrame:
    t = result.coefficient_table().copy()
    t["significance"] = ["***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "" for p in t["p_value"]]
    return t


def fig_cumulative(result):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    c = result.cumulative
    ax.plot(c.index, c["strategy (compounded)"], label="strategy excess return (compounded)", linewidth=1.8)
    ax.plot(c.index, c["factor part (additive)"], label="factor part (sum of beta x factor)", linestyle="--")
    ax.plot(c.index, c["alpha (additive)"], label="alpha (cumulative)", linestyle=":")
    ax.plot(c.index, c["residual (additive)"], label="residual (cumulative)", linewidth=0.9, alpha=0.8)
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.set_title(f"{result.strategy}: cumulative performance and its {result.model_label} decomposition")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    _dates(ax)
    return fig


def fig_contributions(result):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    cum = result.contributions.cumsum()
    for col in cum.columns:
        ax.plot(cum.index, cum[col], label=f"{col} contribution")
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.set_title("Cumulative factor contributions (beta x factor return, additive)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    _dates(ax)
    return fig


def fig_rolling(result):
    r = result.rolling
    names = ["alpha"] + result.factors
    fig, axes = plt.subplots(len(names) + 1, 1, figsize=(10, 2.0 * (len(names) + 1)), sharex=True)
    for ax, name in zip(axes, names):
        ax.plot(r.index, r[name], linewidth=1.2)
        ax.fill_between(r.index, r[f"{name}_low"], r[f"{name}_high"], alpha=0.25)
        ax.axhline(0, color="grey", linewidth=0.6)
        ax.set_ylabel(name, fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.4)
    axes[-1].plot(r.index, r["r2"], color="black", linewidth=1.0)
    axes[-1].set_ylabel("R-squared", fontsize=8)
    axes[-1].grid(True, linestyle="--", alpha=0.4)
    _dates(axes[-1])
    axes[0].set_title(f"Rolling {result.model_label} ({result.sample.get('rolling_window', '')} periods; "
                      f"{int(result.regression.confidence * 100)}% classical bands)")
    fig.tight_layout()
    return fig


def fig_residuals(result):
    e = result.regression.residuals
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"width_ratios": [2, 1]})
    a1.plot(e.index, e, linewidth=0.8)
    out = result.outliers
    if len(out):
        a1.scatter(out.index, out, color="#d62728", s=14, zorder=3, label="> 3 sd")
        a1.legend(fontsize=8)
    a1.axhline(0, color="grey", linewidth=0.6)
    a1.set_title("Residuals")
    a1.grid(True, linestyle="--", alpha=0.4)
    _dates(a1)
    a2.hist(e, bins=min(40, max(10, len(e) // 5)), color="#1f77b4", alpha=0.8)
    a2.set_title("Residual distribution")
    fig.tight_layout()
    return fig


def factor_analysis_figures(result) -> Dict[str, str]:
    figs = {"cumulative": png(fig_cumulative(result)), "contributions": png(fig_contributions(result)),
            "residuals": png(fig_residuals(result))}
    if result.rolling is not None and len(result.rolling):
        figs["rolling"] = png(fig_rolling(result))
    return figs


# ── factor research ──────────────────────────────────────────────────────────────────────────────────────────────

def fig_distribution(values: np.ndarray, title: str):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    v = values[np.isfinite(values)]
    if v.size:
        ax.hist(v, bins=min(60, max(10, v.size // 20)), color="#1f77b4", alpha=0.85)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.4)
    return fig


def fig_profile(profile: pd.DataFrame, title: str):
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.plot(profile.index, profile["median"], label="median", linewidth=1.3)
    ax.plot(profile.index, profile["mean"], label="mean", linewidth=0.9, linestyle="--")
    ax.fill_between(profile.index, profile["q25"], profile["q75"], alpha=0.25, label="25%-75%")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.4)
    _dates(ax)
    return fig


def fig_series(frame: pd.DataFrame, title: str, ylabel: str = "", zero: bool = True):
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for col in frame.columns:
        ax.plot(frame.index, frame[col], label=str(col), linewidth=1.1)
    if zero:
        ax.axhline(0, color="grey", linewidth=0.6)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if len(frame.columns) > 1:
        ax.legend(fontsize=7, ncol=3)
    ax.grid(True, linestyle="--", alpha=0.4)
    _dates(ax)
    return fig


def fig_scatter(x: np.ndarray, y: np.ndarray, xlabel: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    ok = np.isfinite(x) & np.isfinite(y)
    ax.scatter(x[ok], y[ok], s=6, alpha=0.4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} vs {xlabel} ({int(ok.sum())} pairs)")
    ax.grid(True, linestyle="--", alpha=0.4)
    return fig


def correlation_cells(coef: pd.DataFrame, counts: pd.DataFrame, notes: Dict) -> List[List[Dict]]:
    """Rows of {value, n, note, color} for the interactive matrix (red negative, blue positive)."""
    rows = []
    for a in coef.index:
        row = []
        for b in coef.columns:
            v = coef.loc[a, b]
            if np.isfinite(v):
                strength = min(1.0, abs(float(v)))
                color = (f"rgba(31,111,235,{0.15 + 0.75 * strength:.2f})" if v >= 0
                         else f"rgba(218,54,51,{0.15 + 0.75 * strength:.2f})")
            else:
                color = "transparent"
            row.append({"a": a, "b": b, "value": None if not np.isfinite(v) else float(v),
                        "n": int(counts.loc[a, b]), "note": notes.get((a, b), ""), "color": color})
        rows.append(row)
    return rows
