"""
SPX v2 backtest report — performance of what the engine decided, built AFTER a run from its summary
(``results.json``: portfolio value and book greeks at every bar, the option entries and hedges) and its
``data_report.txt`` (missing data and why).

  metrics      total / annualised return, vol, downside deviation, max drawdown, Sharpe, Sortino, Calmar,
               hit rate, average gain / average loss (annualised with the bar frequency of the run)
  equity       portfolio value and drawdown at every bar
  greeks       book delta / gamma at every bar, hedges and option entries
  trades       the option entries and hedge orders
  data issues  the failed start checks and the greeks that did not resolve (from data_report.txt), and the
               bars whose value did not move (a stale valuation, usually a missing option price)

Built from files only, so the report of any past run can be rebuilt (see spx_report_store).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252
METRIC_COLUMNS = ["Total Return", "E[Return] (ann.)", "Vol. (ann.)", "Downside Deviation", "MDD", "Sharpe",
                  "Sortino", "Calmar", "Hit Rate", "Ave. P / Ave. L"]


@dataclass
class SPXReport:
    project: str
    period: tuple
    n_bars: int
    initial_value: float
    final_value: float
    equity: pd.Series                   # time -> portfolio value
    returns: pd.Series                  # time -> bar return
    drawdown: pd.Series                 # time -> drawdown from the running peak (<= 0)
    greeks: pd.DataFrame                # time x [delta, gamma, positions, hedge, entry]
    trades: pd.DataFrame                # one row per option entry / hedge order / step error
    metrics: pd.DataFrame               # strategy x METRIC_COLUMNS
    periods_per_year: float
    data_issues: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    execution_time_s: Optional[float] = None
    saved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def periods_per_year(index: pd.DatetimeIndex) -> float:
    """Bars per year: 252 trading days x bars per trading day observed in the run."""
    if len(index) < 2:
        return float(TRADING_DAYS)
    per_day = len(index) / max(1, len(pd.Index(index.normalize()).unique()))
    return TRADING_DAYS * per_day


def performance_metrics(returns: pd.Series, ppy: float) -> Dict[str, float]:
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 2:
        return {c: float("nan") for c in METRIC_COLUMNS}
    wealth = np.concatenate([[1.0], np.cumprod(1.0 + r.to_numpy())])
    mean_ann = float(r.mean() * ppy)
    vol = float(r.std(ddof=1) * math.sqrt(ppy))
    downside = float(math.sqrt(np.mean(np.minimum(r, 0.0) ** 2)) * math.sqrt(ppy))
    mdd = float(-np.min(wealth / np.maximum.accumulate(wealth) - 1.0))
    gains, losses = r[r > 0], r[r < 0]
    return {
        "Total Return": float(wealth[-1] - 1.0),
        "E[Return] (ann.)": mean_ann,
        "Vol. (ann.)": vol,
        "Downside Deviation": downside,
        "MDD": mdd,
        "Sharpe": mean_ann / vol if vol > 0 else float("nan"),
        "Sortino": mean_ann / downside if downside > 0 else float("nan"),
        "Calmar": mean_ann / mdd if mdd > 0 else float("nan"),
        "Hit Rate": float((r > 0).mean()),
        "Ave. P / Ave. L": float(gains.mean() / abs(losses.mean())) if len(gains) and len(losses) else float("nan"),
    }


# ---------------------------------------------------------------------------
# Building blocks from results.json
# ---------------------------------------------------------------------------

def _equity(summary: Dict[str, Any]) -> pd.Series:
    rows = [(pd.Timestamp(p["time"]), float(p["value"])) for p in summary.get("portfolio_values") or []
            if p.get("value") is not None]
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series([v for _, v in rows], index=pd.DatetimeIndex([t for t, _ in rows]), name="Portfolio")
    return s[~s.index.duplicated(keep="last")].sort_index()


def _order(order: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """{'CompanyShare': {...}} -> {..., 'asset_type': 'CompanyShare'}; {} for no order."""
    if not order:
        return {}
    asset_type, detail = next(iter(order.items()))
    return dict(detail or {}, asset_type=asset_type)


def _greeks_and_trades(summary: Dict[str, Any]):
    greek_rows, trade_rows = [], []
    for step in summary.get("steps") or []:
        t = pd.Timestamp(step["time"])
        entry, hedge = _order(step.get("option_order")), _order(step.get("hedge_order"))
        greek_rows.append({"time": t, "delta": step.get("portfolio_delta"), "gamma": step.get("portfolio_gamma"),
                           "positions": step.get("positions"), "hedge": bool(hedge), "entry": bool(entry)})
        if entry:
            trade_rows.append({"time": t, "kind": "option entry", "instrument": entry.get("name"),
                               "size": entry.get("weight"), "unit": "weight", "spot": step.get("hedge_spot"),
                               "book delta": step.get("portfolio_delta"), "note": step.get("note") or ""})
        if hedge:
            trade_rows.append({"time": t, "kind": "delta hedge", "instrument": hedge.get("name"),
                               "size": hedge.get("quantity"), "unit": "shares", "spot": step.get("hedge_spot"),
                               "book delta": step.get("portfolio_delta"), "note": step.get("note") or ""})
        if step.get("error"):
            trade_rows.append({"time": t, "kind": "step error", "instrument": "", "size": None, "unit": "",
                               "spot": None, "book delta": None, "note": str(step["error"])})
    columns = ["delta", "gamma", "positions", "hedge", "entry"]
    greeks = pd.DataFrame(greek_rows).set_index("time")[columns] if greek_rows else pd.DataFrame(columns=columns)
    trades = pd.DataFrame(trade_rows, columns=["time", "kind", "instrument", "size", "unit", "spot", "book delta",
                                               "note"])
    return greeks, trades


_MISS = re.compile(r"^  - (?P<symbol>.+?)  (?P<greek>\w+): (?P<count>\d+) bar\(s\), (?P<first>.+?) \.\. (?P<last>.+)$")
_CAUSE = re.compile(r"^    root cause: (?P<cause>.*)$")
_CHECK_OR_HEADING = re.compile(r"^(\d\. [A-Z].*|  \[MISSING\].*|        missing.*)$")
_BAR = re.compile(r"no usable observation at [^:]+:\d\d:\d\d: ")


def unresolved_greeks(text: Optional[str]) -> List[Dict[str, Any]]:
    """Section 2 of data_report.txt grouped by option and root cause:
    [{'symbol', 'cause', 'greeks', 'bars': [first bar of each occurrence], 'count'}]."""
    groups: Dict[tuple, Dict[str, Any]] = {}
    miss = None
    for line in (text or "").splitlines():
        m = _MISS.match(line.rstrip())
        if m:
            miss = m.groupdict()
            continue
        c = _CAUSE.match(line.rstrip())
        if c and miss:
            cause = _BAR.sub("no usable observation: ", c["cause"])          # the bar is in 'bars'
            g = groups.setdefault((miss["symbol"], cause), {"symbol": miss["symbol"], "cause": cause,
                                                            "greeks": [], "bars": [], "count": 0})
            if miss["greek"] not in g["greeks"]:
                g["greeks"].append(miss["greek"])
            if miss["first"] not in g["bars"]:
                g["bars"].append(miss["first"])
            g["count"] += int(miss["count"])
            miss = None
    return list(groups.values())


def data_issues_from_text(text: Optional[str]) -> List[str]:
    """Failed start checks and the unresolved greeks of data_report.txt, grouped by root cause
    (the per-bar detail and dependency trees stay in data_report.txt)."""
    if not text:
        return []
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("2. "):
            lines.append(line)
            for g in unresolved_greeks(text):
                bars = sorted(g["bars"])
                lines.append(f"  - {g['symbol']}: {', '.join(g['greeks'])} missing on {len(bars)} bar(s) "
                             f"({bars[0]} .. {bars[-1]})")
                lines.append(f"    root cause: {g['cause']}")
        elif line.startswith("3. ") or (_CHECK_OR_HEADING.match(line) and not line.startswith("2. ")):
            lines.append(line)
    return lines


def build_report(summary: Dict[str, Any], data_report_text: Optional[str] = None) -> Optional[SPXReport]:
    """The report of a run from its results.json summary; None when the run stored no portfolio value."""
    equity = _equity(summary)
    if equity.empty:
        return None
    returns = equity.pct_change().dropna()
    drawdown = equity / equity.cummax() - 1.0
    ppy = periods_per_year(equity.index)
    metrics = pd.DataFrame({"SPX call spread v2": performance_metrics(returns, ppy)}).T[METRIC_COLUMNS]
    greeks, trades = _greeks_and_trades(summary)

    notes = [
        f"{int(summary.get('option_entries') or 0)} option entries, {int(summary.get('hedges') or 0)} hedges, "
        f"{len(summary.get('step_errors') or [])} step errors over {len(equity)} bars.",
        f"Metrics annualised with {ppy:.0f} bars per year (bar frequency observed in the run).",
    ]
    flat = int((returns == 0).sum())
    if flat:
        notes.append(f"Portfolio value unchanged on {flat} of {len(returns)} bars: usually a stale valuation "
                     f"(an option price not stored for that bar, see Data issues), not a flat book.")
    missing_bars = sorted({b for g in unresolved_greeks(data_report_text) for b in g["bars"]})
    if missing_bars:
        notes.append(f"Greeks did not resolve on {len(missing_bars)} bar(s) ({missing_bars[0]} .. {missing_bars[-1]}): "
                     f"those positions count as delta / gamma 0, so the book delta shown there is not the real one "
                     f"and no hedge was sent.")
    if len(returns) < 60:
        notes.append(f"Only {len(returns)} returns: the annualised ratios (Sharpe, Sortino, Calmar) are not "
                     f"meaningful.")

    period = tuple(summary.get("period") or (str(equity.index[0]), str(equity.index[-1])))
    return SPXReport(
        project=summary.get("project", "market_making_spx_call_spread_v2"), period=period, n_bars=len(equity),
        initial_value=float(equity.iloc[0]), final_value=float(equity.iloc[-1]), equity=equity, returns=returns,
        drawdown=drawdown, greeks=greeks, trades=trades, metrics=metrics, periods_per_year=ppy,
        data_issues=data_issues_from_text(data_report_text), notes=notes,
        execution_time_s=summary.get("execution_time_s"), saved_at=summary.get("saved_at"))
