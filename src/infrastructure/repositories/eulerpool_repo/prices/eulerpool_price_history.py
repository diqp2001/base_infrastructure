"""
Eulerpool daily closes as a PriceHistoryPort (the port the dispersion research reads).

Endpoint: GET /charting/ohlcv/{identifier}?resolution=D&from=<unix s>&to=<unix s> -> {t, o, h, l, c, v} arrays.
Probe 2026-11-16: daily bars back to 1989 (JPM 9 571 bars), split-adjusted, not dividend-adjusted (the port's
contract). A bar's stamp is the session's open (14:30 UTC recently, 00:00 UTC on old bars): the trading day is the
stamp's UTC date, never a local-time conversion (00:00 UTC would fall on the previous New York day).

Nothing is written to the database. Wrap it in CachedPriceHistory for a file cache (one request per symbol).
A source that does not answer raises MarketDataUnavailable; an unknown symbol returns {} (never zeros).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Dict

from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort
from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import (
    EulerpoolClient,
    EulerpoolError,
    EulerpoolNotFound,
    identifier_path,
)


def _unix(d: date, end_of_day: bool = False) -> int:
    moment = datetime.combine(d, time(23, 59, 59) if end_of_day else time(0, 0), tzinfo=timezone.utc)
    return int(moment.timestamp())


def closes_from_ohlcv(payload) -> Dict[date, float]:
    """{UTC date of the bar: close} of an OHLCV response; bars without a positive close are left out."""
    if not isinstance(payload, dict):
        return {}
    stamps, closes = payload.get("t") or [], payload.get("c") or []
    out: Dict[date, float] = {}
    for t, c in zip(stamps, closes):
        if t is None or c is None:
            continue
        try:
            value = float(c)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out[datetime.fromtimestamp(int(t), tz=timezone.utc).date()] = value
    return out


class EulerpoolPriceHistory(PriceHistoryPort):

    def __init__(self, client: EulerpoolClient):
        self.client = client

    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        path = f"charting/ohlcv/{identifier_path(underlying.symbol)}"
        try:
            payload = self.client.get(path, resolution="D", **{"from": _unix(start), "to": _unix(end, True)})
        except EulerpoolNotFound:
            return {}
        except EulerpoolError as e:
            raise MarketDataUnavailable(f"Eulerpool daily closes {underlying.symbol}: {e}") from e
        return {d: c for d, c in closes_from_ohlcv(payload).items() if start <= d <= end}

    @staticmethod
    def underlying(symbol: str) -> Underlying:
        """A plain US share for the port (Eulerpool needs the symbol only)."""
        return Underlying(symbol=symbol, con_id=0, sec_type="STK", currency="USD")

