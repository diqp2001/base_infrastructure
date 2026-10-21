"""
BarHistoryUpdater — keeps INTRADAY bars (default 10 minutes) of the universe in factor_values up to date through
the Misbuffet MarketDataService (IBKR TRADES bars, max_import).

It only WRITES data. Every read made for a decision goes through the MarketDataHistoryService frontier, so bars
imported beyond the simulated time are never visible to the model (backtest) and do not exist yet (live).

IBKR constraints: request end dates must lie within the last 6 months, so requests end now with a duration
reaching back to the history start; 10-minute TRADES bars are served for at least 3 months in one request
(measured 2026-10-21: JPM "3 M" -> 2 455 bars, ~39 per session).
"""

import logging
import math
from typing import Dict, List, Optional

import pandas as pd

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class BarHistoryUpdater:

    def __init__(self, market_data_service, tickers: List[str], history_start, bar_size_setting: str = "10 mins",
                 bar_minutes: int = 10, refresh_duration: str = "1 D"):
        self.market_data_service = market_data_service
        self.tickers = list(tickers)
        self.history_start = pd.Timestamp(history_start)
        self.bar_size_setting = bar_size_setting
        self.bar_minutes = int(bar_minutes)
        self.refresh_duration = refresh_duration
        self._imported_through: Optional[pd.Timestamp] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def duration_for(start, end) -> str:
        """Whole weeks covering [start, end] (IBKR duration string for intraday bars)."""
        weeks = max(1, math.ceil((pd.Timestamp(end) - pd.Timestamp(start)).days / 7))
        return f"{weeks} W"

    def ensure_entities(self) -> Dict[str, int]:
        """CompanyShare entities via the engine's path; returns {ticker: entity_id} in configured order."""
        found: Dict[str, int] = {}
        for ticker in self.tickers:
            entity = self.market_data_service._get_entity_by_ticker(ticker, CompanyShare)
            if entity is not None and getattr(entity, "id", None) is not None:
                found[ticker] = int(entity.id)
            else:
                self.logger.warning(f"Could not create/get CompanyShare '{ticker}'")
        return found

    def _import(self, duration: str) -> Dict[str, bool]:
        request_end = pd.Timestamp.now().floor(f"{self.bar_minutes}min").to_pydatetime()
        status = {}
        for ticker in self.tickers:
            try:
                result = self.market_data_service._get_point_in_time_data(
                    ticker=ticker, entity_class=CompanyShare, point_in_time=request_end,
                    bar_size_setting=self.bar_size_setting, duration_str=duration,
                )
                status[ticker] = result is not None
            except Exception as e:
                self.logger.warning(f"{self.bar_size_setting} bar import failed for {ticker}: {e}")
                status[ticker] = False
        return status

    def __call__(self, now) -> Optional[Dict[str, bool]]:
        """Import once (full history), then again only when real time has moved past the last import by a bar."""
        current = pd.Timestamp.now().floor(f"{self.bar_minutes}min")
        if self._imported_through is None:
            status = self._import(self.duration_for(self.history_start, current))
            self._imported_through = current
            return status
        if pd.Timestamp(now) >= self._imported_through + pd.Timedelta(minutes=self.bar_minutes):   # live: new bar
            status = self._import(self.refresh_duration)
            self._imported_through = pd.Timestamp(now).floor(f"{self.bar_minutes}min")
            return status
        return None
