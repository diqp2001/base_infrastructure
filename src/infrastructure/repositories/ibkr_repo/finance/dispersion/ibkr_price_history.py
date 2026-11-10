"""
Daily closes from IBKR (reqHistoricalData, TRADES, regular hours, 1 day bars): split-adjusted by IBKR, not dividend-
adjusted. READ-ONLY on the screener's own client. One request per symbol, paced (pause_seconds) on the shared gateway.
"""

import logging
import math
import time
from datetime import date, datetime
from typing import Dict

from ibapi.contract import Contract

from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort

logger = logging.getLogger(__name__)


class IBKRPriceHistory(PriceHistoryPort):

    def __init__(self, client, timeout_seconds: float = 60.0, pause_seconds: float = 1.5, first_req_id: int = 750_000):
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.pause_seconds = pause_seconds
        self._next_req_id = first_req_id
        self._last_request = 0.0

    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        wait = self._last_request + self.pause_seconds - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        c = Contract()
        c.conId, c.symbol, c.secType, c.exchange, c.currency = (underlying.con_id, underlying.symbol.replace(".", " "),
                                                                 "STK", "SMART", underlying.currency)
        days = (date.today() - start).days + 1
        duration = f"{math.ceil(days / 365)} Y" if days > 365 else f"{days} D"
        self._next_req_id += 1
        req = self._next_req_id
        self.client.request_historical_data(req, c, "", duration, "1 day", "TRADES", use_rth=True, format_date=1)
        done = self.client.historical_data_done.get(req)
        finished = done is not None and done.wait(self.timeout_seconds)
        bars = list(self.client.historical_data.get(req, []))
        error = self.client.historical_data_errors.get(req)
        for store in (self.client.historical_data, self.client.historical_data_errors, self.client.historical_data_done):
            store.pop(req, None)
        if error is not None:
            logger.info("%s: no daily history (%s %s)", underlying.symbol, error[0], error[1])
            return {}
        if not finished:
            raise MarketDataUnavailable(f"IBKR did not answer the {underlying.symbol} daily history request within "
                                        f"{self.timeout_seconds:g} s")
        out = {}
        for bar in bars:
            day = datetime.strptime(str(bar["date"])[:8], "%Y%m%d").date()
            if start <= day <= end and bar["close"] and bar["close"] > 0:
                out[day] = float(bar["close"])
        return out
