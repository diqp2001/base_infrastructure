"""
Daily closes of the monthly dispersion backtest.

1. The members' (CompanyShare) and the ETF's (ETFShare) daily IBKR TRADES bars go into factor_values through the
   Misbuffet MarketDataService, as in the STM projects (DailyHistoryUpdater: write-only; BacktestDataPreloadService
   loads the whole history before the first bar). The trading cycle reads them through the frontier.
2. A member IBKR no longer lists (WBA, delisted 2025) is read from FILE CACHES (never the database), with the same
   frontier rule (KnownClosesReader): results/etf_dispersion_stm/price_history/<source>/<SYMBOL>.json:
     ibkr       IBKR closes fetched read-only through the screener's history connection (``prices`` command);
     eulerpool  Eulerpool closes. Checked 2026-11-16 against IBKR over 13 months: same close on most days, off by
                0.1-5.8 % on scattered days - a fallback only.
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare
from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort


class DailyHistoryUpdater:
    """Keeps the members' daily closes in factor_values up to date through the MarketDataService (IBKR,
    max_import). It only WRITES; every read for a decision goes through the frontier. IBKR request end dates must lie
    within the last 6 months: requests end today with a duration reaching back to the history start."""

    def __init__(self, market_data_service, tickers: List[str], history_start, refresh_duration: str = "1 M",
                 etf: Optional[str] = None):
        self.market_data_service = market_data_service
        self.tickers = list(tickers)
        self.etf = etf                                 # the ETF (ETFShare entity, IBKRETFShareRepository)
        self.history_start = pd.Timestamp(history_start)
        self.refresh_duration = refresh_duration
        self._imported_through: Optional[pd.Timestamp] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def duration_for(start, end) -> str:
        years = max(1, math.ceil((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25))
        return f"{years} Y"

    def ensure_entities(self) -> Dict[str, int]:
        """CompanyShare entities via the engine's path; {ticker: entity_id} of those that exist at the broker."""
        found: Dict[str, int] = {}
        for ticker in self.tickers:
            entity = self.market_data_service._get_entity_by_ticker(ticker, CompanyShare)
            if entity is not None and getattr(entity, "id", None) is not None:
                found[ticker] = int(entity.id)
            else:
                self.logger.warning(f"Could not create/get CompanyShare '{ticker}'")
        return found

    def ensure_etf_entity(self) -> Optional[int]:
        """The ETF's ETFShare entity id (created from IBKR's contract details when missing)."""
        entity = self.market_data_service._get_entity_by_ticker(self.etf, ETFShare) if self.etf else None
        return int(entity.id) if entity is not None and getattr(entity, "id", None) is not None else None

    def _import(self, duration: str) -> Dict[str, bool]:
        request_end = pd.Timestamp.now().normalize().to_pydatetime()
        status = {}
        series = [(t, CompanyShare) for t in self.tickers] + ([(self.etf, ETFShare)] if self.etf else [])
        for ticker, entity_class in series:
            try:
                result = self.market_data_service._get_point_in_time_data(
                    ticker=ticker, entity_class=entity_class, point_in_time=request_end,
                    bar_size_setting="1 day", duration_str=duration)
                status[ticker] = result is not None
            except Exception as e:
                self.logger.warning(f"Daily close import failed for {ticker}: {e}")
                status[ticker] = False
        return status

    def mark_imported(self, through=None) -> None:
        """The full history was imported elsewhere (BacktestDataPreloadService): only new days from now on."""
        self._imported_through = pd.Timestamp(through or pd.Timestamp.now()).normalize()

    def __call__(self, now) -> Optional[Dict[str, bool]]:
        """Import once (full history), then only when real time has moved past the last import (live)."""
        today = pd.Timestamp.now().normalize()
        if self._imported_through is None:
            status = self._import(self.duration_for(self.history_start, today))
            self._imported_through = today
            return status
        if pd.Timestamp(now).normalize() > self._imported_through:
            status = self._import(self.refresh_duration)
            self._imported_through = pd.Timestamp(now).normalize()
            return status
        return None


# ---- file caches (the ETF and the members the engine cannot import) ----

def cache_path(folder: str, symbol: str) -> str:
    return os.path.join(folder, f"{symbol.replace('/', '_').replace(' ', '_')}.json")


class CacheFileReader(PriceHistoryPort):
    """The closes a CachedPriceHistory file holds, whatever window it was fetched for (no source behind it)."""

    def __init__(self, folder: str):
        self.folder = folder

    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        try:
            with open(cache_path(self.folder, underlying.symbol), encoding="utf-8") as f:
                closes = json.load(f)["closes"]
        except (OSError, ValueError, KeyError):
            return {}
        return {date.fromisoformat(d): float(c) for d, c in closes.items()
                if start.isoformat() <= d <= end.isoformat()}


class PreferredPrices(PriceHistoryPort):
    """The first source with closes for a symbol; ``served`` records which (name) served each symbol."""

    def __init__(self, sources: Sequence[Tuple[str, PriceHistoryPort]]):
        self.sources = list(sources)
        self.served: Dict[str, str] = {}

    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        for name, source in self.sources:
            closes = source.daily_closes(underlying, start, end)
            if closes:
                self.served[underlying.symbol] = name
                return closes
        self.served[underlying.symbol] = "none"
        return {}


def fetch_eulerpool(symbols: List[str], start: date, end: date, folder: str) -> Dict[str, str]:
    from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import EulerpoolClient
    from src.infrastructure.repositories.eulerpool_repo.prices.eulerpool_price_history import EulerpoolPriceHistory
    from src.infrastructure.repositories.ibkr_repo.finance.dispersion.cached_price_history import CachedPriceHistory
    client = EulerpoolClient.from_environment()
    if client is None:
        raise RuntimeError("no Eulerpool key (EULERPOOL_API_KEY or EULERPOOL_CREDENTIALS_FILE)")
    prices = CachedPriceHistory(EulerpoolPriceHistory(client), folder)
    problems = {}
    for s in symbols:
        if not prices.daily_closes(EulerpoolPriceHistory.underlying(s), start, end):
            problems[s] = "no Eulerpool closes"
    return problems
