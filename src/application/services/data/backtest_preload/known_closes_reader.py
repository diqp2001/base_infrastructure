"""
KnownClosesReader - daily closes KNOWN at a time (dates x symbols), for trading cycles that read a whole panel at
each engine step: the series stored in the database through the MarketDataHistoryService frontier (a daily close dated
D is known from D+1 00:00), plus symbols the engine cannot import from a PriceHistoryPort (file caches) clipped with
the same rule. Used by DispersionTradingCycle and STMDecileTradingCycle.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Mapping, Optional, Sequence, Tuple

import pandas as pd

from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort


def known_through(now) -> date:
    """The last close date known at ``now``: a daily close dated D is known from D+1 00:00."""
    return (pd.Timestamp(now) - pd.Timedelta(days=1)).date()


class KnownClosesReader:
    """Daily closes known at a time, dates x symbols.

    frontier: [(reader, {symbol: entity_id})] - the series stored in the database, each read through the
              MarketDataHistoryService frontier (an STMFrontierPriceReader per factor type: the members'
              company_share_factor closes, the ETF's etf_share_factor closes); the frontier is set to the step time.
    fallback: the symbols the engine cannot import (a member delisted since, no longer listed at IBKR), from a
              PriceHistoryPort (file caches), clipped with the same rule.
    """

    def __init__(self, start: date, frontier: Sequence[Tuple[object, Mapping[str, int]]] = (),
                 fallback: Optional[PriceHistoryPort] = None, fallback_symbols: Sequence[str] = ()):
        self.start = start
        self.frontier = [(reader, dict(ids)) for reader, ids in frontier if ids]
        self.fallback = fallback
        self.fallback_symbols = list(fallback_symbols)
        self._fallback_cache: Dict[str, pd.Series] = {}

    def _fallback_series(self, symbol: str) -> pd.Series:
        if symbol not in self._fallback_cache:
            closes = self.fallback.daily_closes(
                Underlying(symbol=symbol, con_id=0, sec_type="STK", currency="USD"), self.start, date.today())
            self._fallback_cache[symbol] = pd.Series({pd.Timestamp(d): float(c) for d, c in closes.items()},
                                                     dtype=float).sort_index()
        return self._fallback_cache[symbol]

    def closes(self, now) -> pd.DataFrame:
        last = pd.Timestamp(known_through(now))
        columns: Dict[str, pd.Series] = {}
        for reader, ids in self.frontier:
            history = getattr(reader, "history_service", None)
            if history is not None:
                history.set_frontier(pd.Timestamp(now).to_pydatetime())      # nothing after `now` is readable
            panel = reader.load_close_panel({i: s for s, i in ids.items()}, start=self.start)
            for s in panel.columns:
                columns[s] = panel[s].dropna()
        if self.fallback is not None:
            for s in self.fallback_symbols:
                if s not in columns or columns[s].empty:
                    columns[s] = self._fallback_series(s)
        frame = pd.DataFrame(columns).sort_index()
        frame.index = pd.DatetimeIndex(frame.index).normalize()
        return frame[frame.index <= last]
