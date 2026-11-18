"""
Report of a decile research run (any score; STMDecileTradingCycle in this repository), per model variant:

    predictions.csv               rebalance, variant, symbol, score, rank, percentile, decile, model trained at,
                                  next period's return
    decile_returns_<gross|net>.csv  holding-period returns D1..Dn and LS (Dn - D1), one row per period end, per variant
    cumulative_<gross|net>.csv    prod(1 + R) - 1 of the same columns
    turnover.csv                  one-way turnover of every decile at every rebalance
    summary.json                  statistics of every decile and LS (gross and net), monotonicity, the variants'
                                  LS side by side, the settings
    deciles_cumulative.png        the cumulative performance of every decile through time and LS, one row per variant
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, Dict, Mapping

import pandas as pd

from src.application.services.portfolio_research.decile_portfolios import (
    DecileResearch,
    cumulative,
    monotonicity,
    statistics,
)

# deciles as an ordered magnitude: a diverging ordinal pair - red arm for the low deciles (D1 darkest), blue arm for
# the high ones (Dn darkest); each arm validated as an ordinal ramp on the light surface (dataviz validate_palette)
LOW_ARM = ["#842a2a", "#b13938", "#e34948", "#e8706f", "#ee9a99"]
HIGH_ARM = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, INK_SECONDARY, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def decile_colors(n: int):
    if n == 10:
        return LOW_ARM + HIGH_ARM
    half = n // 2
    return (LOW_ARM[:half] + HIGH_ARM[-(n - half):]) if n <= 10 else None


def summarise(research: DecileResearch) -> Dict[str, Any]:
    cfg = research.config
    out: Dict[str, Any] = {"periods": sum(1 for p in research.periods if p.settled)}
    turnover = research.turnover_frame()
    for kind in ("gross", "net"):
        frame = research.returns_frame(kind)
        if frame.empty:
            continue
        stats = {}
        for col in frame.columns:
            t = turnover[col] if col in turnover else None
            if col == "LS" and not turnover.empty:
                t = (turnover[f"D{cfg.n_deciles}"] + turnover["D1"]) / 2.0
            stats[col] = statistics(frame[col], cfg.periods_per_year, t)
        out[kind] = {"statistics": stats, "monotonicity": monotonicity(frame, cfg.n_deciles)}
    return out


def write_report(cycle, folder: str, settings: Mapping[str, Any]) -> Dict[str, Any]:
    os.makedirs(folder, exist_ok=True)
    pd.DataFrame([asdict(p) for p in cycle.predictions]).to_csv(os.path.join(folder, "predictions.csv"), index=False)
    summary: Dict[str, Any] = {"variants": {}, "skipped": {str(k.date()): v for k, v in cycle.skipped.items()},
                               "traded": cycle.traded, "settings": dict(settings)}
    for kind in ("gross", "net"):
        frames, cums = [], []
        for name, research in cycle.research.items():
            r = research.returns_frame(kind)
            if r.empty:
                continue
            frames.append(r.assign(variant=name))
            cums.append(cumulative(r).assign(variant=name))
        if frames:
            pd.concat(frames).rename_axis("period_end").to_csv(os.path.join(folder, f"decile_returns_{kind}.csv"))
            pd.concat(cums).rename_axis("period_end").to_csv(os.path.join(folder, f"cumulative_{kind}.csv"))
    turnovers = [r.turnover_frame().assign(variant=n) for n, r in cycle.research.items() if r.periods]
    if turnovers:
        pd.concat(turnovers).rename_axis("rebalance").to_csv(os.path.join(folder, "turnover.csv"))
    for name, research in cycle.research.items():
        summary["variants"][name] = summarise(research)
    summary["long_short_comparison"] = {
        name: {k: s.get("gross", {}).get("statistics", {}).get("LS", {}).get(k)
               for k in ("cumulative_return", "annualized_return", "sharpe_ratio", "max_drawdown", "win_rate")}
        | {"average_spread": s.get("gross", {}).get("monotonicity", {}).get("average_spread"),
           "spearman_decile_vs_average_return":
               s.get("gross", {}).get("monotonicity", {}).get("spearman_decile_vs_average_return")}
        for name, s in summary["variants"].items()}
    with open(os.path.join(folder, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    try:
        plot_cumulative(cycle, os.path.join(folder, "deciles_cumulative.png"))
    except Exception as e:                       # a chart failure never loses the numbers
        summary["chart_error"] = repr(e)
    return summary


def plot_cumulative(cycle, path: str) -> None:
    """Per variant: every decile's cumulative return through time (ordinal colours, D1 / Dn labelled at the line
    end) and the Dn - D1 long-short in its own panel (one axis each, shared time axis)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    names = [n for n, r in cycle.research.items() if not r.returns_frame().empty]
    if not names:
        return
    n = cycle.config.n_deciles
    colors = decile_colors(n)
    fig, axes = plt.subplots(len(names), 2, figsize=(13, 4.2 * len(names)), squeeze=False,
                             gridspec_kw={"width_ratios": [2.2, 1]}, facecolor=SURFACE)
    for row, name in enumerate(names):
        cum = cumulative(cycle.research[name].returns_frame("gross")) * 100.0
        ax, ax_ls = axes[row]
        for d in range(1, n + 1):
            col = f"D{d}"
            ax.plot(cum.index, cum[col], color=colors[d - 1] if colors else None, linewidth=2 if d in (1, n) else 1.2,
                    label=col)
            if d in (1, n):
                ax.annotate(col, (cum.index[-1], cum[col].iloc[-1]), xytext=(4, 0), textcoords="offset points",
                            color=INK, fontsize=9, va="center")
        ax_ls.plot(cum.index, cum["LS"], color=INK, linewidth=2)
        ax_ls.axhline(0, color=INK_SECONDARY, linewidth=0.8)
        ax.set_title(f"Variant {name}: cumulative return by decile (%) - D1 lowest score, D{n} highest",
                     color=INK, fontsize=10, loc="left")
        ax_ls.set_title(f"Variant {name}: D{n} - D1 long-short (%)", color=INK, fontsize=10, loc="left")
        for a in (ax, ax_ls):
            a.set_facecolor(SURFACE)
            a.grid(True, color=GRID, linewidth=0.6)
            for side in ("top", "right"):
                a.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                a.spines[side].set_color(GRID)
            a.tick_params(colors=INK_SECONDARY, labelsize=8)
            locator = mdates.AutoDateLocator(maxticks=6 if a is ax else 4)
            a.xaxis.set_major_locator(locator)
            a.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.legend(ncol=5, fontsize=8, frameon=False, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def decile_status(results_dir: str, step: str, on_month=None):
    """RunStatus (results_dir/status.json, the dispersion page's format) with a decile progress hook."""
    from src.application.services.dispersion.dispersion_progress import RunStatus

    class DecileRunStatus(RunStatus):
        def on_rebalance(self, cycle, result, portfolio_value=None) -> None:
            fields = {"months_done": len({p.rebalance for r in cycle.research.values() for p in r.periods}),
                      "last_month": str(result.rebalance.date()),
                      "portfolio_value": float(portfolio_value) if portfolio_value is not None else None}
            for name, research in cycle.research.items():
                frame = research.returns_frame()
                if not frame.empty:
                    fields[f"cumulative_ls_{name}"] = float((1 + frame["LS"].fillna(0)).prod() - 1)
            if self.on_month is not None:
                self.on_month(cycle)
            self.update(**fields)

    return DecileRunStatus(results_dir, step, on_month=on_month)
