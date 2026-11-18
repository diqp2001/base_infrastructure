"""
Results of the monthly model-filtered dispersion backtest (DispersionTradingCycle.months): one row per trade (premiums, counts, P&L of A and B, incremental P&L), one row per
constituent and trade (weight, contracts, premium, score, rank, selected / why not), and the summary statistics of
A, B and B - A over the settled trades. Every premium is a MODELLED premium (``price_source``).
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd

from src.application.services.dispersion.dispersion_trading_cycle import MonthResult
from src.application.services.dispersion.modelled_option_pricing import PRICE_SOURCE

PERIODS_PER_YEAR = 12


def trade_rows(results: Sequence[MonthResult]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for r in results:
        row: Dict[str, Any] = {"opened": r.opened, "expiry": r.expiry, "settled_on": r.settled_on,
                               "problem": r.problem, "replication_ratio": r.replication_ratio}
        t = r.trade
        if t is not None:
            n_all, n_sel = len(t.original.positions), len(t.filtered.positions)
            scores = list(t.selection.scores.values())
            row.update({
                "etf_contracts_short": t.etf_contracts,
                "etf_spot": t.etf.spot, "etf_strike": t.etf.strike, "etf_call_price": t.etf.bid,
                "etf_vol": t.etf.implied_vol,
                "short_premium": t.short_premium,
                "full_basket_premium": t.full_basket_premium,
                "selected_basket_premium": t.selected_basket_premium,
                "unused_premium": t.unused_premium,
                "net_initial_premium_original": t.original.net_initial_premium,
                "net_initial_premium_filtered": t.net_initial_premium,
                "n_constituents": n_all, "n_selected": n_sel,
                "pct_selected": n_sel / n_all if n_all else float("nan"),
                "n_scored": len(scores),
                "mean_model_score": float(np.mean(scores)) if scores else float("nan"),
                "mean_selected_score": (float(np.mean([t.selection.scores[s] for s in t.filtered.positions
                                                       if s in t.selection.scores]))
                                        if any(s in t.selection.scores for s in t.filtered.positions)
                                        else float("nan")),
                "model_retrained": r.scores.retrained if r.scores else None,
            })
        for name, s in (("original", r.original), ("filtered", r.filtered)):
            if s is not None:
                row.update({f"{name}_short_payoff": s.payoff.short_etf, f"{name}_long_payoff": s.payoff.long_basket,
                            f"{name}_pnl": s.pnl})
        if r.complete:
            row["incremental_pnl"] = r.filtered.pnl - r.original.pnl
        rows.append(row)
    return pd.DataFrame(rows)


def constituent_rows(results: Sequence[MonthResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        t = r.trade
        if t is None:
            continue
        unscored = r.scores.unscored if r.scores else {}
        for leg in t.constituents:
            s = leg.symbol
            rows.append({
                "opened": r.opened, "expiry": r.expiry, "symbol": s, "weight": leg.weight, "spot": leg.spot,
                "strike": leg.strike, "vol": leg.implied_vol, "call_price": leg.ask,
                "raw_contracts": t.raw_positions.get(s), "contracts": t.original.positions.get(s),
                "premium": t.original.positions.get(s, 0.0) * leg.multiplier * leg.ask,
                "model_score": t.selection.scores.get(s), "rank": t.selection.ranks.get(s),
                "selected": s in t.filtered.positions,
                "reason": t.selection.rejected.get(s) or (f"unscored, kept: {unscored[s]}" if s in unscored else ""),
            })
    return pd.DataFrame(rows)


def pnl_stats(pnl: Sequence[float]) -> Dict[str, float]:
    x = np.asarray([v for v in pnl if v is not None and np.isfinite(v)], dtype=float)
    if not len(x):
        return {"trades": 0}
    cumulative = np.cumsum(x)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cumulative]))[1:]
    std = float(x.std(ddof=1)) if len(x) > 1 else float("nan")
    return {
        "trades": int(len(x)),
        "total_pnl": float(cumulative[-1]),
        "average_pnl": float(x.mean()),
        "median_pnl": float(np.median(x)),
        "pnl_std": std,
        "sharpe_annualised": (float(x.mean() / std * math.sqrt(PERIODS_PER_YEAR))
                              if std and np.isfinite(std) and std > 0 else float("nan")),
        "max_drawdown": float((cumulative - peak).min()),          # in dollars, of the cumulative P&L
        "win_rate": float((x > 0).mean()),
        "positive_trade_frequency": float((x > 0).sum() / len(x)),
        "best": float(x.max()), "worst": float(x.min()),
    }


def summary(trades: pd.DataFrame) -> Dict[str, Any]:
    settled = trades[trades.get("incremental_pnl").notna()] if "incremental_pnl" in trades else trades.iloc[0:0]
    out: Dict[str, Any] = {
        "price_source": PRICE_SOURCE,
        "trades_settled": int(len(settled)),
        "months_skipped": int(trades["problem"].notna().sum()) if "problem" in trades else 0,
    }
    if len(settled):
        out["original"] = pnl_stats(settled["original_pnl"])
        out["model_filtered"] = pnl_stats(settled["filtered_pnl"])
        out["incremental"] = pnl_stats(settled["incremental_pnl"])
        for col in ("short_premium", "full_basket_premium", "selected_basket_premium", "unused_premium",
                    "net_initial_premium_original", "n_constituents", "n_selected", "pct_selected",
                    "mean_model_score"):
            out[f"average_{col}"] = float(settled[col].mean())
    return out


def write_report(results: Sequence[MonthResult], folder: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(folder, exist_ok=True)
    trades = trade_rows(results)
    trades.to_csv(os.path.join(folder, "trades.csv"), index=False)
    constituent_rows(results).to_csv(os.path.join(folder, "constituents.csv"), index=False)
    s = summary(trades)
    s["settings"] = settings
    with open(os.path.join(folder, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, default=str)
    return s


PUBLISHED_COLUMNS = ("original_pnl", "filtered_pnl", "incremental_pnl", "short_premium", "full_basket_premium",
                     "selected_basket_premium", "unused_premium", "n_selected", "pct_selected", "mean_model_score")


def publish_research(results: Sequence[MonthResult], results_service, run_id: int) -> int:
    """Publish the settled months to the run registry (ResearchResultService): one series per P&L / premium column,
    dated at the expiry (group 'dispersion'), and the A / B / incremental P&L statistics as metrics."""
    trades = trade_rows(results)
    if trades.empty or "incremental_pnl" not in trades:
        return 0
    settled = trades[trades["incremental_pnl"].notna()].copy()
    if settled.empty:
        return 0
    settled.index = pd.to_datetime(settled["expiry"])
    frame = settled[[c for c in PUBLISHED_COLUMNS if c in settled]].astype(float)
    points = results_service.publish_frame(run_id, frame, group="dispersion")
    stats = summary(trades)
    for scope in ("original", "model_filtered", "incremental"):
        if isinstance(stats.get(scope), dict):
            results_service.publish_metrics(run_id, stats[scope], scope=scope)
    results_service.publish_metrics(run_id, {k: v for k, v in stats.items() if not isinstance(v, dict)},
                                    scope="dispersion")
    return points
