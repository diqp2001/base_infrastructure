"""
A file cache in front of a PriceHistoryPort: one JSON file per symbol (folder/<SYMBOL>.json) holding the closes and
the last day they were fetched for. A request is served from the file when the file already covers [start, end];
otherwise the source is asked once and the file replaced. The closes are the source's: nothing is computed here.
"""

import json
import os
from datetime import date
from typing import Dict

from src.domain.ports.finance.dispersion.option_data import Underlying
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort


class CachedPriceHistory(PriceHistoryPort):

    def __init__(self, source: PriceHistoryPort, folder: str):
        self.source = source
        self.folder = folder

    def _path(self, symbol: str) -> str:
        return os.path.join(self.folder, f"{symbol.replace('/', '_').replace(' ', '_')}.json")

    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        path = self._path(underlying.symbol)
        try:
            with open(path, encoding="utf-8") as f:
                cached = json.load(f)
            if cached["start"] <= start.isoformat() and cached["fetched_for"] >= end.isoformat():
                return {date.fromisoformat(d): c for d, c in cached["closes"].items()
                        if start.isoformat() <= d <= end.isoformat()}
        except (OSError, ValueError, KeyError):
            pass
        closes = self.source.daily_closes(underlying, start, end)
        os.makedirs(self.folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"symbol": underlying.symbol, "start": start.isoformat(), "fetched_for": end.isoformat(),
                       "closes": {d.isoformat(): c for d, c in sorted(closes.items())}}, f)
        return closes
