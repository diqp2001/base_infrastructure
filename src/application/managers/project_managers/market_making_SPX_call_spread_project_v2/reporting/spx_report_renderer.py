"""
Rendering of the SPX v2 backtest report: matplotlib figures, HTML tables (Flask results page) and a
multi-page PDF (matplotlib PdfPages, no extra dependency) — same layout as the Spatio-Temporal Momentum report.
"""

from __future__ import annotations

import base64
import io
from typing import Callable, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting.spx_report import (  # noqa: E402
    SPXReport,
)

PERCENT_METRICS = {"Total Return", "E[Return] (ann.)", "Vol. (ann.)", "Downside Deviation", "MDD", "Hit Rate"}


def _dates(ax):
    ax.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax.xaxis.get_major_locator()))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_equity(rep: SPXReport):
    """Portfolio value and drawdown at every bar."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    ax1.plot(rep.equity.index, rep.equity.values, color="#1f77b4", linewidth=1.5, marker="o", markersize=3)
    ax1.axhline(rep.initial_value, color="grey", linewidth=0.7, linestyle="--")
    entries = rep.greeks.index[rep.greeks["entry"].astype(bool)] if not rep.greeks.empty else []
    for t in entries:
        ax1.axvline(t, color="#2ca02c", linewidth=0.8, alpha=0.7)
    ax1.set_ylabel("Portfolio value (USD)")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.set_title("Figure 1: Portfolio Value (green lines: option entries) and Drawdown")
    ax2.fill_between(rep.drawdown.index, rep.drawdown.values * 100, 0, color="#d62728", alpha=0.4, step="post")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True, linestyle="--", alpha=0.5)
    _dates(ax2)
    fig.tight_layout()
    return fig


def fig_returns(rep: SPXReport):
    """Bar P&L in USD and the return distribution."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
    pnl = rep.equity.diff().dropna()
    ax1.bar(pnl.index, pnl.values, color=["#2ca02c" if v >= 0 else "#d62728" for v in pnl.values], width=0.8)
    ax1.axhline(0, color="grey", linewidth=0.7)
    ax1.set_ylabel("P&L per bar (USD)")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.5)
    _dates(ax1)
    ax1.set_title("P&L per bar")
    ax2.hist(rep.returns.values * 100, bins=max(5, min(40, len(rep.returns) // 2)), color="#1f77b4", alpha=0.8)
    ax2.axvline(0, color="grey", linewidth=0.7)
    ax2.set_xlabel("Bar return (%)")
    ax2.set_ylabel("Bars")
    ax2.set_title("Return distribution")
    fig.suptitle("Figure 2: P&L and Returns")
    fig.tight_layout()
    return fig


def fig_greeks(rep: SPXReport):
    """Book delta and gamma at every bar, with the bars where a hedge was sent."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    g = rep.greeks
    if g.empty:
        ax1.text(0.5, 0.5, "No book greeks recorded", ha="center", transform=ax1.transAxes)
        return fig
    delta = pd.to_numeric(g["delta"], errors="coerce")
    gamma = pd.to_numeric(g["gamma"], errors="coerce")
    ax1.plot(g.index, delta, color="#1f77b4", linewidth=1.3, marker="o", markersize=3, label="book delta")
    hedged = g["hedge"].astype(bool)
    ax1.scatter(g.index[hedged], delta[hedged], color="#ff7f0e", zorder=3, s=40, label="hedge sent")
    ax1.axhline(0, color="grey", linewidth=0.7)
    ax1.set_ylabel("Delta (shares)")
    ax1.legend(loc="best", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.set_title("Figure 3: Book Greeks before the hedge decision")
    ax2.plot(g.index, gamma, color="#9467bd", linewidth=1.3, marker="o", markersize=3)
    ax2.axhline(0, color="grey", linewidth=0.7)
    ax2.set_ylabel("Gamma")
    ax2.grid(True, linestyle="--", alpha=0.5)
    _dates(ax2)
    fig.tight_layout()
    return fig


FIGURES: Dict[str, Tuple[str, Callable]] = {
    "figure1": ("Figure 1: Portfolio Value and Drawdown", fig_equity),
    "figure2": ("Figure 2: P&L and Returns", fig_returns),
    "figure3": ("Figure 3: Book Greeks and Hedges", fig_greeks),
}


def figure_png(rep: SPXReport, name: str) -> bytes:
    fig = FIGURES[name][1](rep)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def figure_base64(rep: SPXReport, name: str) -> str:
    return base64.b64encode(figure_png(rep, name)).decode()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def metrics_display(rep: SPXReport) -> pd.DataFrame:
    """Metrics as strings: percentages for returns / vol / drawdown / hit rate, ratios with 2 decimals."""
    out = rep.metrics.copy().astype(object)
    for col in out.columns:
        out[col] = [("–" if pd.isna(v) else (f"{v:.2%}" if col in PERCENT_METRICS else f"{v:.2f}"))
                    for v in rep.metrics[col]]
    return out


def summary_table(rep: SPXReport) -> pd.DataFrame:
    rows = {
        "Period": f"{rep.period[0]} to {rep.period[1]}",
        "Bars": rep.n_bars,
        "Initial value": f"{rep.initial_value:,.2f}",
        "Final value": f"{rep.final_value:,.2f}",
        "P&L": f"{rep.final_value - rep.initial_value:+,.2f}",
        "Option entries": int((rep.trades["kind"] == "option entry").sum()),
        "Hedges": int((rep.trades["kind"] == "delta hedge").sum()),
        "Step errors": int((rep.trades["kind"] == "step error").sum()),
        "Run time": f"{rep.execution_time_s:.0f} s" if rep.execution_time_s else "–",
        "Saved at": rep.saved_at or "–",
    }
    return pd.DataFrame({"Value": rows})


def trades_display(rep: SPXReport) -> pd.DataFrame:
    t = rep.trades.copy()
    if t.empty:
        return pd.DataFrame({"": ["no orders"]})
    t["time"] = t["time"].astype(str)
    t["size"] = [("" if pd.isna(v) else (f"{v:+.2f}" if u == "weight" else f"{v:+,.1f}"))
                 for v, u in zip(t["size"], t["unit"])]
    for col in ("spot", "book delta"):
        t[col] = ["" if pd.isna(v) else f"{v:,.2f}" for v in t[col]]
    return t.drop(columns=["unit"]).set_index("time")


def tables(rep: SPXReport) -> List[Tuple[str, str, pd.DataFrame]]:
    return [
        ("summary", "Run Summary", summary_table(rep)),
        ("table1", "Table 1: Performance Metrics", metrics_display(rep)),
        ("table2", "Table 2: Orders (option entries, delta hedges, step errors)", trades_display(rep)),
    ]


def table_html(df: pd.DataFrame) -> str:
    return df.to_html(classes="table table-sm table-dark table-striped", border=0, na_rep="–")


def _table_figure(title: str, df: pd.DataFrame, rows_per_page: int = 30):
    figs = []
    for start in range(0, max(1, len(df)), rows_per_page):
        part = df.iloc[start:start + rows_per_page]
        fig, ax = plt.subplots(figsize=(11, 0.6 + 0.36 * (len(part) + 2)))
        ax.axis("off")
        cells = [["–" if (not isinstance(v, str) and pd.isna(v)) else str(v) for v in row] for row in part.to_numpy()]
        t = ax.table(cellText=cells or [[""] * len(df.columns)], rowLabels=[str(i) for i in part.index] or [""],
                     colLabels=list(df.columns), loc="center", cellLoc="center")
        t.auto_set_font_size(False)
        t.set_fontsize(8)
        t.scale(1, 1.3)
        ax.set_title(title + (f" (continued)" if start else ""), fontsize=10)
        fig.tight_layout()
        figs.append(fig)
    return figs


def _text_page(title: str, lines: List[str], fontsize: int = 9):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.text(0.01, 0.99, "\n".join([title, ""] + lines), va="top", ha="left", fontsize=fontsize,
            family="monospace" if fontsize < 9 else None, wrap=True)
    return fig


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

ORDER = ["summary", "table1", "figure1", "figure2", "figure3", "table2"]


def build_pdf(rep: SPXReport) -> bytes:
    buf = io.BytesIO()
    table_map = {key: (title, df) for key, title, df in tables(rep)}
    with PdfPages(buf) as pdf:
        cover = [
            f"Project: {rep.project}",
            f"Period: {rep.period[0]} to {rep.period[1]}  ({rep.n_bars} bars)",
            f"Portfolio: {rep.initial_value:,.2f} -> {rep.final_value:,.2f}  "
            f"({rep.final_value / rep.initial_value - 1:+.2%})",
            "",
            "Notes:",
        ] + [f"  • {n}" for n in rep.notes]
        fig = _text_page("SPX Call Spread Market Maker (v2) — Backtest Report", cover, fontsize=11)
        pdf.savefig(fig)
        plt.close(fig)
        for key in ORDER:
            figs = _table_figure(*table_map[key]) if key in table_map else [FIGURES[key][1](rep)]
            for fig in figs:
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
        issues = rep.data_issues or ["No data issues recorded (data_report.txt missing or clean)."]
        for start in range(0, len(issues), 55):
            fig = _text_page("Data issues (from data_report.txt)" + (" (continued)" if start else ""),
                             issues[start:start + 55], fontsize=7)
            pdf.savefig(fig)
            plt.close(fig)
    return buf.getvalue()
