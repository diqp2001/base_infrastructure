"""
Dispersion screener P.02: the ETF universe of one screening date — every issuer's ETFs, the listing filters (asset
class, leverage, inverse, synthetic), then the holdings rules (equities only, 2 .. max_constituents, fresh holdings,
normalised weights). Sources are ports (issuer adapters); nothing here calls an API or a database.

Optionable (the ETF has listed options) and tradeable constituents are checked in P.03 on IBKR.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from src.domain.entities.finance.dispersion.etf_holdings import (
    ConstituentWeights, EtfListing, listing_rejections, prepare_constituents,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.domain.ports.finance.dispersion.etf_holdings_ports import EtfHoldingsPort, EtfUniversePort

logger = logging.getLogger(__name__)


@dataclass
class UniverseEntry:
    listing: EtfListing
    status: str                                   # "eligible" | "listing rejected" | "holdings rejected" | "no holdings"
    reasons: List[str] = field(default_factory=list)
    constituents: Optional[ConstituentWeights] = None


@dataclass
class UniverseResult:
    screening_date: date
    entries: List[UniverseEntry]

    @property
    def eligible(self) -> List[UniverseEntry]:
        return [e for e in self.entries if e.status == "eligible"]

    def counts(self) -> dict:
        out: dict = {}
        for e in self.entries:
            out[e.status] = out.get(e.status, 0) + 1
        return out


class EtfUniverseService:

    def __init__(self, sources: Sequence[Tuple[EtfUniversePort, EtfHoldingsPort]], config: DispersionScreenConfig):
        self.sources = list(sources)
        self.config = config

    def build(self, screening_date: date, tickers: Optional[Iterable[str]] = None,
              progress: Callable[[str], None] = lambda message: None) -> UniverseResult:
        """Every listed ETF with its status; `tickers` restricts the run (a re-check), never extends it."""
        wanted = {t.upper() for t in tickers} if tickers else None
        entries, seen = [], set()
        for universe, holdings in self.sources:
            for listing in universe.list_etfs(screening_date):
                if listing.ticker in seen or (wanted is not None and listing.ticker not in wanted):
                    continue
                seen.add(listing.ticker)
                entries.append(self._entry(listing, holdings, screening_date))
                progress(f"{listing.ticker}: {entries[-1].status}")
        return UniverseResult(screening_date, entries)

    def _entry(self, listing: EtfListing, holdings: EtfHoldingsPort, screening_date: date) -> UniverseEntry:
        reasons = listing_rejections(listing, self.config)
        if reasons:
            return UniverseEntry(listing, "listing rejected", reasons)
        snapshot = holdings.get_holdings(listing, screening_date)
        if snapshot is None:
            return UniverseEntry(listing, "no holdings", ["holdings file unavailable for this date"])
        constituents = prepare_constituents(snapshot, self.config, screening_date)
        if not constituents.ok:
            return UniverseEntry(listing, "holdings rejected", constituents.reasons, constituents)
        return UniverseEntry(listing, "eligible", [], constituents)
