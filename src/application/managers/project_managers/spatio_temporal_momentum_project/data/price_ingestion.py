"""
DailyHistoryUpdater — keeps daily closes in factor_values up to date through
the Misbuffet MarketDataService (IBKR repositories, max_import).

It only WRITES data.  Every read made for a decision goes through the
MarketDataHistoryService frontier, so bars imported beyond the simulated time
are never visible to the model (backtest) and simply do not exist yet (live).

Constraint: the IBKR broker only accepts request end dates within the last
6 months, so requests always end today with a duration reaching back to the
history start.
"""

import logging
import math
from typing import Dict, List, Optional

import pandas as pd

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class DailyHistoryUpdater:

    def __init__(self, market_data_service, tickers: List[str], history_start, refresh_duration: str = "1 M"):
        self.market_data_service = market_data_service
        self.tickers = list(tickers)
        self.history_start = pd.Timestamp(history_start)
        self.refresh_duration = refresh_duration
        self._imported_through: Optional[pd.Timestamp] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def duration_for(start, end) -> str:
        years = max(1, math.ceil((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25))
        return f"{years} Y"

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
        request_end = pd.Timestamp.now().normalize().to_pydatetime()
        status = {}
        for ticker in self.tickers:
            try:
                result = self.market_data_service._get_point_in_time_data(
                    ticker=ticker, entity_class=CompanyShare, point_in_time=request_end,
                    bar_size_setting="1 day", duration_str=duration,
                )
                status[ticker] = result is not None
            except Exception as e:
                self.logger.warning(f"Daily close import failed for {ticker}: {e}")
                status[ticker] = False
        return status

    def __call__(self, now) -> Optional[Dict[str, bool]]:
        """Import once (full history), then only when real time has moved past the last import."""
        today = pd.Timestamp.now().normalize()
        if self._imported_through is None:
            status = self._import(self.duration_for(self.history_start, today))
            self._imported_through = today
            return status
        if pd.Timestamp(now).normalize() > self._imported_through:     # live: a new day has started
            status = self._import(self.refresh_duration)
            self._imported_through = pd.Timestamp(now).normalize()
            return status
        return None
