"""
Rendering of the STM research report: matplotlib figures in the layout of
Tan, Roberts & Zohren (2023), HTML tables, and a multi-page PDF
(matplotlib PdfPages — no extra dependency).
"""

from __future__ import annotations

import base64
import io
from typing import Callable, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.ticker  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (  # noqa: E402
    STMResearchReport,
)

BENCHMARKS = ("Long Only", "TSMOM", "MACD", "CSMOM")


def _is_benchmark(name: str) -> bool:
    return name in BENCHMARKS


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_cumulative(rep: STMResearchReport):
    """Figure 1: Cumulative Returns - Rescaled to Target Volatility."""
    fig, ax = plt.subplots(figsize=(9, 6))
    for name in rep.cumulative.columns:
        ax.plot(rep.cumulative.index, rep.cumulative[name], label=name,
                linestyle=":" if _is_benchmark(name) else "-", linewidth=1.4 if not _is_benchmark(name) else 1.1)
    ax.set_yscale("log")
    plain = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    ax.yaxis.set_major_formatter(plain)
    ax.yaxis.set_minor_formatter(plain)
    ax.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Returns (Log Scale)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.set_title("Figure 1: Cumulative Returns - Rescaled to Target Volatility")
    fig.tight_layout()
    return fig


def fig_correlation(rep: STMResearchReport):
    """Figure 3: (Left) Correlation of Strategies (Right) Rolling Correlations of the STM model."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1, 1.3]})
    corr = rep.correlation
    n = len(corr)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    data = np.ma.array(corr.to_numpy(), mask=mask)
    im = ax1.imshow(data, cmap="coolwarm", vmin=-1, vmax=1)
    ax1.set_xticks(range(n), corr.columns, rotation=45, ha="right", fontsize=8)
    ax1.set_yticks(range(n), corr.index, fontsize=8)
    for i in range(n):
        for j in range(i + 1):
            ax1.text(j, i, f"{corr.iat[i, j]:.2g}", ha="center", va="center", fontsize=8)
    ax1.set_frame_on(False)
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    ax1.set_title("Correlation of Strategies")
    for col in rep.rolling_correlation.columns:
        ax2.plot(rep.rolling_correlation.index, rep.rolling_correlation[col], label=col, linewidth=1.1)
    ax2.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))
    ax2.set_ylim(-1, 1)
    ax2.axhline(0, color="grey", linewidth=0.6)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Correlation of Strategies")
    ax2.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3, fontsize=8)
    ax2.set_title(f"{rep.rolling_window}-session Rolling Correlations of {rep.model_name}")
    fig.suptitle("Figure 3: (Left) Correlation of Strategies (Right) Rolling Correlations")
    fig.tight_layout()
    return fig


def fig_turnover(rep: STMResearchReport):
    """Figure 4: Average Turnover of Strategies."""
    fig, ax = plt.subplots(figsize=(10, 5))
    cols = list(rep.turnover.columns)
    box = ax.boxplot([rep.turnover[c].dropna() for c in cols], tick_labels=cols, patch_artist=True,
                     showfliers=False, whis=(0, 100))
    for patch, c in zip(box["boxes"], cols):
        patch.set_facecolor("#d62728" if _is_benchmark(c) else "#2ca02c")
    ax.set_ylabel("Average Turnover")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title("Figure 4: Average Turnover of Strategies")
    fig.tight_layout()
    return fig


def _top_features(importance: np.ndarray, k: int = 20) -> np.ndarray:
    return np.argsort(importance)[::-1][:k]


def fig_shap_single(rep: STMResearchReport, top: int = 20):
    """Figure 5: Impact on Predicted Signal Output for a Single Asset (beeswarm)."""
    sh = rep.shap
    fig, ax = plt.subplots(figsize=(10, 8))
    if sh is None:
        ax.text(0.5, 0.5, "SHAP not available", ha="center")
        return fig
    k = sh.output_assets.index(rep.shap_asset)
    phi = sh.values[:, k, :]                                           # [S, P]
    order = _top_features(np.abs(phi).mean(axis=0), top)[::-1]          # least important at the bottom
    rng = np.random.default_rng(0)
    cmap = plt.cm.cool
    for row, j in enumerate(order):
        vals = sh.inputs[:, j]
        lo, hi = np.nanmin(vals), np.nanmax(vals)
        colour = (vals - lo) / (hi - lo) if hi > lo else np.full_like(vals, 0.5)
        ax.scatter(phi[:, j], row + rng.uniform(-0.25, 0.25, len(vals)), c=cmap(colour), s=10, alpha=0.8)
    ax.set_yticks(range(len(order)), [sh.feature_names[j] for j in order], fontsize=8)
    ax.axvline(0, color="grey", linewidth=0.7)
    ax.set_xlabel("SHAP")
    ax.set_ylabel("Spatio-Temporal Features")
    sm = plt.cm.ScalarMappable(cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, ticks=[0, 1])
    cb.ax.set_yticklabels(["Low", "High"])
    cb.set_label("Feature value")
    ax.set_title(f"Figure 5: Impact on Predicted Signal Output for a Single Asset – {rep.shap_asset}")
    fig.tight_layout()
    return fig


def fig_shap_all(rep: STMResearchReport, top: int = 20):
    """Figure 6: Cumulative Mean Absolute Impact on Predicted Signal Output for All Assets."""
    sh = rep.shap
    fig, ax = plt.subplots(figsize=(12, 8))
    if sh is None:
        ax.text(0.5, 0.5, "SHAP not available", ha="center")
        return fig
    per_asset = np.abs(sh.values).mean(axis=0)                         # [N_out, P]
    order = _top_features(per_asset.sum(axis=0), top)[::-1]
    left = np.zeros(len(order))
    palette = np.vstack([plt.cm.tab20.colors, plt.cm.tab20b.colors, plt.cm.tab20c.colors])
    colours = palette[np.arange(len(sh.output_assets)) % len(palette)]
    for a, asset in enumerate(sh.output_assets):
        widths = per_asset[a, order]
        ax.barh(range(len(order)), widths, left=left, color=colours[a], label=asset)
        left += widths
    ax.set_yticks(range(len(order)), [sh.feature_names[j] for j in order], fontsize=8)
    ax.set_xlabel("mean(|SHAP|)")
    ax.set_ylabel("Spatio-Temporal Features")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), ncol=2, fontsize=7)
    ax.set_title("Figure 6: Cumulative Mean Absolute Impact on Predicted Signal Output for All Assets")
    fig.tight_layout()
    return fig


FIGURES: Dict[str, Tuple[str, Callable]] = {
    "figure1": ("Figure 1: Cumulative Returns - Rescaled to Target Volatility", fig_cumulative),
    "figure3": ("Figure 3: (Left) Correlation of Strategies (Right) Rolling Correlations", fig_correlation),
    "figure4": ("Figure 4: Average Turnover of Strategies", fig_turnover),
    "figure5": ("Figure 5: Impact on Predicted Signal Output for a Single Asset", fig_shap_single),
    "figure6": ("Figure 6: Cumulative Mean Absolute Impact on Predicted Signal Output for All Assets", fig_shap_all),
}


def figure_png(rep: STMResearchReport, name: str) -> bytes:
    fig = FIGURES[name][1](rep)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def figure_base64(rep: STMResearchReport, name: str) -> str:
    return base64.b64encode(figure_png(rep, name)).decode()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def tables(rep: STMResearchReport) -> List[Tuple[str, str, pd.DataFrame]]:
    return [
        ("table1", "Table 1: Performance Metrics for Strategies – Raw Signal Outputs", rep.table_raw),
        ("table2", "Table 2: Performance Metrics for Strategies – Rescaled to Target Volatility", rep.table_rescaled),
        ("table6", "Table 6: Impact of Transactions Costs on Sharpe Ratio – Rescaled to Target Volatility "
                   "(columns: transaction cost in basis points)", rep.table_costs),
    ]


def table_html(df: pd.DataFrame) -> str:
    return df.to_html(float_format=lambda v: f"{v:.3f}", classes="table table-sm table-dark table-striped",
                      border=0, na_rep="–")


def _table_figure(title: str, df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 0.5 + 0.38 * (len(df) + 2)))
    ax.axis("off")
    cells = [[("–" if pd.isna(v) else f"{v:.3f}") for v in row] for row in df.to_numpy()]
    t = ax.table(cellText=cells, rowLabels=list(df.index), colLabels=list(df.columns), loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.3)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

PAPER_ORDER = ["table1", "table2", "figure1", "figure3", "table6", "figure4", "figure5", "figure6"]


def build_pdf(rep: STMResearchReport) -> bytes:
    buf = io.BytesIO()
    table_map = {key: (title, df) for key, title, df in tables(rep)}
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        lines = [
            "Spatio-Temporal Momentum — Backtest Report",
            "",
            f"Model: {rep.model_name}",
            f"Period: {rep.period[0]} to {rep.period[1]}  ({rep.n_sessions} sessions)",
            f"Universe ({len(rep.assets)}): {', '.join(rep.assets)}",
            "",
            "Layout follows Tan, Roberts & Zohren (2023), arXiv:2302.10175.",
            "",
            "Notes:",
        ] + [f"  • {n}" for n in rep.notes]
        ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=10, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)
        for key in PAPER_ORDER:
            if key in table_map:
                fig = _table_figure(*table_map[key])
            else:
                fig = FIGURES[key][1](rep)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    return buf.getvalue()
