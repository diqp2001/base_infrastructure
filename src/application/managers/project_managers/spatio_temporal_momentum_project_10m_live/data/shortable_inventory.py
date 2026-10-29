"""
ShortableInventory — which names IBKR can lend today, from IBKR's public short-stock file (read once per day).

IBKR publishes its US borrow inventory at ftp://ftp2.interactivebrokers.com/usa.txt (user "shortstock", no password):
one line per security ``SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|``, AVAILABLE in shares (">10000000"
when larger). The API's shortable ticks (generic tick 236) need a real-time US-equity subscription, which the
account does not have (B2) — the file is the same inventory without it.

A name that is not listed or has 0 shares available is not shortable: its short targets are cut to 0 before
set_holdings (an existing short in it is bought back). When the file cannot be read and no earlier copy of the day
is loaded, nothing is restricted (logged): IBKR still rejects a short sale it cannot borrow for.
"""

import logging
import urllib.request
from datetime import date
from typing import Callable, Dict, Optional, Tuple

SHORTSTOCK_URL = "ftp://shortstock:@ftp2.interactivebrokers.com/usa.txt"


def fetch_shortstock_file(url: str = SHORTSTOCK_URL, timeout: float = 60.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("latin-1")


def parse_shortstock_file(text: str, currency: str = "USD") -> Dict[str, Tuple[int, float, float]]:
    """{symbol: (shares available, borrow fee % / year, rebate % / year)}; the first line of a symbol wins."""
    out: Dict[str, Tuple[int, float, float]] = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 8 or parts[1] != currency or parts[0] in out:
            continue
        try:
            available = int(parts[7].lstrip(">").strip() or 0)
            out[parts[0]] = (available, float(parts[6] or 0), float(parts[5] or 0))
        except ValueError:
            continue
    return out


class ShortableInventory:

    def __init__(self, fetch: Callable[[], str] = fetch_shortstock_file, today: Callable[[], date] = date.today,
                 logger=None):
        self._fetch = fetch
        self._today = today
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.inventory: Optional[Dict[str, Tuple[int, float, float]]] = None
        self.loaded_on: Optional[date] = None

    def refresh(self) -> bool:
        """Load today's file once; returns whether an inventory (today's or an earlier one) is available."""
        today = self._today()
        if self.loaded_on == today:
            return True
        try:
            self.inventory = parse_shortstock_file(self._fetch())
            self.loaded_on = today
            self.logger.info(f"IBKR short-stock file loaded: {len(self.inventory)} US securities")
        except Exception as e:
            self.logger.warning(f"IBKR short-stock file not read ({e!r}): "
                                + ("keeping the previous one" if self.inventory is not None else
                                   "shorts not restricted, IBKR rejects what it cannot borrow"))
        return self.inventory is not None

    def available(self, symbol: str) -> Optional[int]:
        """Shares IBKR can lend (0 when not listed); None when no inventory could be loaded."""
        if self.inventory is None:
            return None
        return self.inventory.get(symbol, (0, 0.0, 0.0))[0]

    def restrict(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, Optional[int]]]:
        """Short targets of names IBKR cannot lend are cut to 0. Returns (weights, {cut symbol: available})."""
        if not self.refresh():
            return dict(weights), {}
        cut = {t: self.available(t) for t, w in weights.items() if w < 0 and not self.available(t)}
        return {t: (0.0 if t in cut else w) for t, w in weights.items()}, cut
