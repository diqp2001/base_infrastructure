"""
Fund issuers' public holdings files as EtfUniversePort / EtfHoldingsPort (dispersion screener, P.02).

Issuers publish only their LATEST holdings, so every downloaded file is archived as it came
(<archive_dir>/<issuer>/<TICKER>/<as_of>.<ext>, git-ignored under results/). A screen for an earlier date reads the
archive (the newest file dated on or before that date); a screen for today downloads and archives. The fund lists
are current lists only (an ETF closed since a past date is missing from a historical screen: survivorship, named
in the results).

A subclass gives: ISSUER, FILE_EXT, fetch_listings(), holdings_url(listing), parse_holdings(raw, listing, source,
retrieved_at). Downloads go through `fetch` (injectable for tests), one at a time, `min_interval_seconds` apart.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import abstractmethod
from datetime import date, datetime
from typing import Callable, Dict, List, Optional

from src.domain.entities.finance.dispersion.etf_holdings import EtfHoldingsSnapshot, EtfListing
from src.domain.ports.finance.dispersion.etf_holdings_ports import EtfHoldingsPort, EtfUniversePort

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) base_infrastructure-holdings/1.0"


def http_get(url: str, timeout: float = 30.0) -> bytes:
    import requests
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.content


class IssuerHoldingsSource(EtfUniversePort, EtfHoldingsPort):
    ISSUER: str = ""
    FILE_EXT: str = ""

    def __init__(self, archive_dir: str, fetch: Callable[[str], bytes] = http_get,
                 today: Callable[[], date] = date.today, min_interval_seconds: float = 1.0):
        self.archive_dir = archive_dir
        self._fetch = fetch
        self._today = today
        self.min_interval_seconds = min_interval_seconds
        self._last_fetch = 0.0
        self._listings: Dict[date, List[EtfListing]] = {}

    # ---- subclass contract ----
    @abstractmethod
    def fetch_listings(self) -> List[EtfListing]:
        """The issuer's current ETF list."""

    @abstractmethod
    def holdings_url(self, listing: EtfListing) -> str:
        """URL of the listing's latest holdings file."""

    @abstractmethod
    def parse_holdings(self, raw: bytes, listing: EtfListing, source: str,
                       retrieved_at: datetime) -> EtfHoldingsSnapshot:
        """Parse one holdings file (raises ValueError when it is not a holdings file)."""

    # ---- ports ----
    def list_etfs(self, screening_date: date) -> List[EtfListing]:
        today = self._today()
        if today not in self._listings:
            self._listings = {today: self.fetch_listings()}
        return list(self._listings[today])

    def get_holdings(self, listing: EtfListing, screening_date: date) -> Optional[EtfHoldingsSnapshot]:
        if screening_date >= self._today():
            snapshot = self.download(listing)
            if snapshot is not None and snapshot.as_of <= screening_date:
                return snapshot
        return self.from_archive(listing, screening_date)

    # ---- download / archive ----
    def fetch(self, url: str) -> bytes:
        wait = self.min_interval_seconds - (time.monotonic() - self._last_fetch)
        if wait > 0:
            time.sleep(wait)
        try:
            return self._fetch(url)
        finally:
            self._last_fetch = time.monotonic()

    def download(self, listing: EtfListing) -> Optional[EtfHoldingsSnapshot]:
        url = self.holdings_url(listing)
        try:
            raw = self.fetch(url)
            snapshot = self.parse_holdings(raw, listing, url, datetime.now())
        except Exception as e:
            logger.warning("%s holdings of %s unavailable (%s): %s", self.ISSUER, listing.ticker, url, e)
            return None
        path = self._archive_path(listing.ticker, snapshot.as_of)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(raw)
            with open(path + ".meta.json", "w", encoding="utf-8") as f:
                json.dump({"url": url, "retrieved_at": str(snapshot.retrieved_at), "as_of": str(snapshot.as_of)}, f)
        return snapshot

    def from_archive(self, listing: EtfListing, screening_date: date) -> Optional[EtfHoldingsSnapshot]:
        folder = os.path.join(self.archive_dir, self.ISSUER, listing.ticker)
        if not os.path.isdir(folder):
            return None
        dated = []
        for name in os.listdir(folder):
            if name.endswith(self.FILE_EXT):
                try:
                    dated.append((date.fromisoformat(name[:-len(self.FILE_EXT)]), name))
                except ValueError:
                    continue
        dated = sorted(d for d in dated if d[0] <= screening_date)
        if not dated:
            return None
        path = os.path.join(folder, dated[-1][1])
        retrieved_at = datetime.fromtimestamp(os.path.getmtime(path))
        try:
            meta = json.load(open(path + ".meta.json", encoding="utf-8"))
            retrieved_at = datetime.fromisoformat(meta["retrieved_at"])
        except Exception:
            pass
        with open(path, "rb") as f:
            return self.parse_holdings(f.read(), listing, path, retrieved_at)

    def _archive_path(self, ticker: str, as_of: date) -> str:
        return os.path.join(self.archive_dir, self.ISSUER, ticker, f"{as_of.isoformat()}{self.FILE_EXT}")


# ---- parsing helpers shared by the issuers ----
def number(text) -> Optional[float]:
    """'823,589,227.23' -> 823589227.23; '-' / '' / None -> None."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).strip().replace(",", "").replace("%", "")
    if s in ("", "-", "--", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def clean_text(text) -> str:
    """Issuer names carry ®/™ (sometimes mangled into U+FFFD) and padding."""
    s = "" if text is None else str(text)
    for ch in ("�", "®", "™"):
        s = s.replace(ch, "")
    return " ".join(s.split())
