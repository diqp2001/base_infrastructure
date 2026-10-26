"""
Rendering of the cross-sectional momentum report: matplotlib figures, HTML tables and a multi-page PDF
(matplotlib PdfPages — no extra dependency). The data-coverage figure and table formatting are the STM ones.
"""

from __future__ import annotations

import base64
import io
from typing import Callable, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report import (  # noqa: E402
    MODEL_NAME,
    CSMReport,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum import (  # noqa: E402
    stm_report_renderer as stm_renderer,
)

table_html = stm_renderer.table_html
QUINTILE_COLOURS = ["#d62728", "#ff7f0e", "#7f7f7f", "#8fbc5a", "#2ca02c"]      # Q1 (lowest) .. Q5 (highest)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_cumulative(rep: CSMReport):
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for name in rep.cumulative.columns:
        main = name == MODEL_NAME
        ax.plot(rep.cumulative.index, rep.cumulative[name], label=name, linestyle="-" if main else ":",
                linewidth=1.6 if main else 1.1)
    # score quintiles (equal weight, Q1 red .. Q3 grey .. Q5 green) and Q5 - Q1; absent from reports stored before 2026-10-26
    quint = getattr(rep, "quintile_cumulative", None)
    if quint is not None and not quint.empty:
        buckets, spread = list(quint.columns[:-1]), quint.columns[-1]
        colours = QUINTILE_COLOURS if len(buckets) == len(QUINTILE_COLOURS) else             plt.get_cmap("RdYlGn")(np.linspace(0.05, 0.95, len(buckets)))
        for name, colour in zip(buckets, colours):
            ax.plot(quint.index, quint[name], label=name, color=colour, linewidth=1.0, alpha=0.9)
        ax.plot(quint.index, quint[spread], label=spread, color="black", linestyle="--", linewidth=1.1)
    ax.axhline(1.0, color="grey", linewidth=0.6)
    ax.set_ylabel("Cumulative return (x)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", fontsize=7, ncol=2)
    wealth = rep.cumulative[MODEL_NAME]
    ax2.fill_between(wealth.index, wealth / wealth.cummax() - 1.0, 0.0, color="#d62728", alpha=0.4)
    ax2.set_ylabel("Drawdown")
    ax2.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))
    ax.set_title("Cumulative Returns (no costs): strategies and score quintiles; Drawdown of the model")
    fig.tight_layout()
    return fig


def fig_importance(rep: CSMReport, top: int = 20):
    imp = rep.table_importance.head(top).iloc[::-1]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 0.9 + 0.32 * len(imp)), sharey=True)
    ax1.barh(imp.index, imp["Gain share %"], color="#1f77b4")
    ax1.set_xlabel("Gain share of the models used (%)")
    ax2.barh(imp.index, imp["Mean |SHAP| (log-odds)"], color="#ff7f0e")
    ax2.set_xlabel("Mean |TreeSHAP| at the decisions (log-odds)")
    for ax in (ax1, ax2):
        ax.grid(True, axis="x", linestyle="--", alpha=0.5)
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle(f"Feature Importance (top {len(imp)} by gain)")
    fig.tight_layout()
    return fig


def fig_selection(rep: CSMReport):
    m = rep.selection_matrix
    fig, ax = plt.subplots(figsize=(12, 1.5 + 0.35 * max(1, len(m))))
    if m.empty:
        ax.axis("off")
        ax.text(0.5, 0.5, "No retraining in this run", ha="center", va="center")
    else:
        ax.imshow(m.to_numpy(dtype=float), cmap="Greens", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(m.shape[1]), m.columns, rotation=75, ha="right", fontsize=7)
        ax.set_yticks(range(m.shape[0]), m.index, fontsize=8)
        ax.set_xlabel("candidate feature (green = selected by the best Optuna trial)")
    ax.set_title("Optuna TPE Feature Selection per Retraining")
    fig.tight_layout()
    return fig


def fig_optuna(rep: CSMReport):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5), gridspec_kw={"width_ratios": [1.4, 1]})
    for key, values in rep.trial_histories.items():
        v = np.array([np.nan if x is None else x for x in values], dtype=float)
        best = pd.Series(v).cummax().to_numpy()
        line, = ax1.plot(np.arange(len(v)), best, linewidth=1.3, label=key)
        ax1.scatter(np.arange(len(v)), v, s=8, alpha=0.4, color=line.get_color())
    ax1.set_xlabel("trial")
    ax1.set_ylabel("validation score (dots) / best so far (line)")
    ax1.grid(True, linestyle="--", alpha=0.5)
    if rep.trial_histories:
        ax1.legend(fontsize=7, loc="lower right")
    ax1.set_title("Optuna TPE optimisation history")
    pim = rep.table_param_importance
    if pim is not None and not pim.empty:
        mean = pim.mean(axis=1).sort_values()
        ax2.barh(mean.index, mean.values, color="#9467bd")
        ax2.set_xlabel("mean importance across retrainings")
    else:
        ax2.axis("off")
        ax2.text(0.5, 0.5, "Hyper-parameter importances unavailable", ha="center", va="center")
    ax2.set_title("Hyper-parameter importance (Optuna)")
    fig.tight_layout()
    return fig


FIGURES: Dict[str, Tuple[str, Callable]] = {
    "fig_cumulative": ("Cumulative Returns (strategies and score quintiles) and Drawdown", fig_cumulative),
    "fig_importance": ("Feature Importance", fig_importance),
    "fig_selection": ("Optuna TPE Feature Selection per Retraining", fig_selection),
    "fig_optuna": ("Optuna Optimisation History and Hyper-parameter Importance", fig_optuna),
    "coverage_figure": ("Data Coverage by Session", stm_renderer.fig_coverage),
}


def figure_png(rep: CSMReport, name: str) -> bytes:
    fig = FIGURES[name][1](rep)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def figure_base64(rep: CSMReport, name: str) -> str:
    return base64.b64encode(figure_png(rep, name)).decode()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def tables(rep: CSMReport) -> List[Tuple[str, str, pd.DataFrame]]:
    return [
        ("table_performance", "Performance (no costs; Ave. Turnover = mean sum of |weight changes|)",
         rep.table_performance),
        ("table_costs", "Sharpe Ratio net of Transaction Costs (columns: cost in basis points of turnover)",
         rep.table_costs),
        ("table_quintiles", "Performance per Score Quintile (equal weight, no costs; Q1 = lowest probability)",
         getattr(rep, "table_quintiles", None)),
        ("table_prediction", "Prediction Quality of the Classifier", rep.table_prediction),
        ("table_importance", "Feature Importance", rep.table_importance),
        ("table_retrainings", "Retrainings: Optuna TPE Result per Model", rep.table_retrainings),
        ("coverage_summary", "Data Coverage – Summary (expected bars from the NYSE calendar)", rep.coverage_summary),
        ("coverage_assets", "Data Coverage by Asset (least covered first)", rep.coverage_assets),
    ]


ORDER = ["table_performance", "fig_cumulative", "table_quintiles", "table_costs", "table_prediction", "fig_importance",
         "table_importance", "fig_selection", "fig_optuna", "table_retrainings", "coverage_summary",
         "coverage_figure", "coverage_assets"]


def _table_figure(title: str, df: pd.DataFrame):
    df = df if df is not None and not df.empty else pd.DataFrame({"Value": ["none"]})
    widths = [max(len(str(c)), *(len(stm_renderer._cell(v)) for v in df[c])) for c in df.columns]
    fig, ax = plt.subplots(figsize=(min(30, max(11, 0.11 * sum(widths) + 2)), 0.6 + 0.36 * (len(df) + 2)))
    ax.axis("off")
    cells = [[stm_renderer._cell(v) for v in row] for row in df.astype(object).to_numpy()]
    t = ax.table(cellText=cells, rowLabels=[str(i) for i in df.index], colLabels=list(df.columns),
                 loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(7)
    t.scale(1, 1.3)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    return fig


def build_pdf(rep: CSMReport) -> bytes:
    buf = io.BytesIO()
    table_map = {key: (title, df) for key, title, df in tables(rep)}
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        lines = [
            "Cross-Sectional Momentum — Backtest Report",
            "",
            f"Model: {rep.model_name}",
            f"Period: {rep.period[0]} to {rep.period[1]}  ({rep.n_sessions} decisions)",
            f"Universe ({len(rep.assets)}): {', '.join(rep.assets)}",
            "",
            "Notes:",
        ] + [f"  • {n}" for n in rep.notes]
        ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=9, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)
        for key in ORDER:
            fig = _table_figure(*table_map[key]) if key in table_map else FIGURES[key][1](rep)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    return buf.getvalue()
