"""
Split guard (P.08.03): a stock split leaves a jump in a stored close series.

Bars are stored get-or-create (never overwritten) and IBKR serves history adjusted for splits as of the request
date. After a split the stored bars (old scale) and newly imported bars (new scale) mix in one series: one bar shows
a -50 % (2:1) or +900 % (1:10 reverse) "return" — at the ex-date or wherever stored and new bars meet. Fed to the
features it is a huge false signal; trained on, it distorts the model.

split_like_jumps(closes) finds, per ticker, the bars whose move from the previous close is a common split ratio
(within a tolerance). The trading cycle excludes those tickers from the eligible assets: the model is retrained
without them (or, live, the decision is not traded while missing_asset_patience runs) until the series is
re-imported. A real crash of exactly such a size is excluded too — the safe side.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd

# forward splits (k:1) — reverse splits (1:k) are their inverses
SPLIT_RATIOS: Tuple[float, ...] = (1.25, 4 / 3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 50.0)


@dataclass(frozen=True)
class SplitJump:
    ticker: str
    bar: pd.Timestamp
    ratio: float                     # previous close / close: 2.0 = 2-for-1 split, 0.1 = 1-for-10 reverse split

    def describe(self) -> str:
        return f"{self.ticker} at {self.bar} (previous close / close = {self.ratio:.4g})"


@dataclass(frozen=True)
class SplitGuardConfig:
    tolerance: float                 # relative distance to a split ratio, e.g. 0.03
    ratios: Tuple[float, ...] = SPLIT_RATIOS

    @classmethod
    def from_config(cls, cfg: Optional[dict]) -> Optional["SplitGuardConfig"]:
        """{'tolerance': 0.03} (project config 'split_guard'); None / missing = no guard."""
        if not cfg:
            return None
        return cls(tolerance=float(cfg["tolerance"]), ratios=tuple(cfg.get("ratios", SPLIT_RATIOS)))


def split_like_jumps(closes: pd.DataFrame, guard: SplitGuardConfig,
                     tickers: Optional[Iterable[str]] = None) -> Dict[str, SplitJump]:
    """{ticker: newest SplitJump} over the whole panel (index = bars, columns = tickers, NaN = no bar)."""
    smallest = min(guard.ratios)
    out: Dict[str, SplitJump] = {}
    for ticker in (tickers if tickers is not None else closes.columns):
        if ticker not in closes.columns:
            continue
        series = closes[ticker].dropna()
        series = series[series > 0]
        if len(series) < 2:
            continue
        ratio = (series.shift(1) / series).iloc[1:]
        size = np.maximum(ratio, 1.0 / ratio)                  # >= 1 whatever the direction
        candidates = size[size >= smallest * (1 - guard.tolerance)]
        for bar in reversed(candidates.index):                 # the newest one is reported
            if any(abs(size[bar] / k - 1.0) <= guard.tolerance for k in guard.ratios):
                out[ticker] = SplitJump(ticker, pd.Timestamp(bar), float(ratio[bar]))
                break
    return out
