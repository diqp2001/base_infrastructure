"""
BarHistoryUpdater — keeps the INTRADAY bars (default 10 minutes) of every series the run reads in factor_values up
to date through the Misbuffet MarketDataService (IBKR repositories, max_import): the shares' TRADES bars and the
extra series (benchmarks, the shares' implied volatility).

It only WRITES data. Every read made for a decision goes through the MarketDataHistoryService frontier, so bars
imported beyond the simulated time are never visible to the model (backtest) and do not exist yet (live).

IBKR constraints: request end dates must lie within the last 6 months, so requests end now with a duration reaching
back to the history start; 10-minute TRADES bars are served for at least 3 months in one request.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class BarHistoryUpdater:

    def __init__(self, market_data_service, tickers: List[str], history_start, bar_size_setting: str = "10 mins",
                 bar_minutes: int = 10, refresh_duration: str = "1 D",
                 extra_series: Optional[List[Tuple[type, str, str]]] = None):
        """``extra_series`` = [(entity class, symbol, whatToShow)] imported besides the shares' TRADES bars, e.g.
        (CompanyShare, 'JPM', 'OPTION_IMPLIED_VOLATILITY') or (Index, 'IRX', 'TRADES')."""
        self.market_data_service = market_data_service
        self.tickers = list(tickers)
        self.extra_series = list(extra_series or [])
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
        """Entities via the engine's path; returns {symbol: entity_id} (shares in configured order, then the
        entities of the extra series)."""
        found: Dict[str, int] = {}
        wanted = [(CompanyShare, t) for t in self.tickers]
        wanted += [(cls, sym) for cls, sym, _ in self.extra_series if sym not in self.tickers]
        for cls, ticker in wanted:
            if ticker in found:
                continue
            entity = self.market_data_service._get_entity_by_ticker(ticker, cls)
            if entity is not None and getattr(entity, "id", None) is not None:
                found[ticker] = int(entity.id)
            else:
                self.logger.warning(f"Could not create/get {cls.__name__} '{ticker}'")
        return found

    def _import(self, duration: str) -> Dict[str, bool]:
        request_end = pd.Timestamp.now().floor(f"{self.bar_minutes}min").to_pydatetime()
        status = {}
        series = [(CompanyShare, t, "TRADES") for t in self.tickers] + self.extra_series
        for cls, ticker, what_to_show in series:
            key = ticker if what_to_show == "TRADES" else f"{ticker}:{what_to_show}"
            try:
                result = self.market_data_service._get_point_in_time_data(
                    ticker=ticker, entity_class=cls, point_in_time=request_end,
                    bar_size_setting=self.bar_size_setting, duration_str=duration, what_to_show=what_to_show,
                )
                status[key] = result is not None
            except Exception as e:
                self.logger.warning(f"{self.bar_size_setting} {what_to_show} import failed for {ticker}: {e}")
                status[key] = False
        return status

    def mark_imported(self, through=None) -> None:
        """The full history was imported elsewhere (BacktestDataPreloadService): only new bars from now on."""
        self._imported_through = pd.Timestamp(through or pd.Timestamp.now()).floor(f"{self.bar_minutes}min")

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
