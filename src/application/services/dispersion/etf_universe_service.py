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
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from src.domain.ports.finance.dispersion.etf_holdings import ConstituentWeights, EtfHoldingsSnapshot, EtfListing
from src.application.services.dispersion.screen_config import DispersionScreenConfig
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


# ---- screening rules for an ETF listing and its holdings file ----

def listing_rejections(listing: EtfListing, config: DispersionScreenConfig) -> List[str]:
    """Why an ETF is out before its holdings are read (asset class, leverage, inverse, synthetic)."""
    reasons = []
    if (listing.asset_class or "").strip().lower() not in ("equity", ""):
        reasons.append(f"asset class {listing.asset_class}")
    if listing.leverage_factor < 0:
        reasons.append("inverse")
    elif abs(listing.leverage_factor) > 1:
        reasons.append(f"leveraged x{listing.leverage_factor:g}")
    name = f" {listing.name.upper()} "
    marker = next((m for m in config.leveraged_name_markers if m in name), None)
    if marker:
        reasons.append(f"leveraged / inverse name ({marker.strip()})")
    if (listing.replication or "").lower() == "synthetic":
        reasons.append("synthetic replication")
    return reasons


def prepare_constituents(snapshot: EtfHoldingsSnapshot, config: DispersionScreenConfig,
                         screening_date: date) -> ConstituentWeights:
    """Equity constituents and their normalised weights, or the reasons the ETF cannot be screened."""
    reasons = []
    age = (screening_date - snapshot.as_of).days
    if age < 0:
        reasons.append(f"holdings dated {snapshot.as_of} are after the screening date {screening_date}")
    elif age > config.max_holdings_age_days:
        reasons.append(f"holdings {age} days old (max {config.max_holdings_age_days})")

    equities = snapshot.equity_lines()
    missing = [line.ticker for line in equities if line.weight is None]
    if missing:
        reasons.append(f"no weight for {len(missing)} equity line(s): {', '.join(missing[:5])}")
    blank = [line.name for line in equities if not line.ticker or line.ticker == "-"]
    if blank:
        reasons.append(f"{len(blank)} equity line(s) without a ticker: {', '.join(blank[:3])}")

    weights: Dict[str, float] = {}
    for line in equities:
        if line.weight is not None and line.ticker and line.ticker != "-":
            weights[line.ticker] = weights.get(line.ticker, 0.0) + line.weight   # share classes listed twice
    equity_share = sum(weights.values())
    if equity_share < config.min_equity_weight:
        reasons.append(f"equities are {equity_share:.1%} of the fund (min {config.min_equity_weight:.0%}): "
                       f"derivatives / cash / synthetic exposure")
    if any(w < 0 for w in weights.values()):
        reasons.append("negative equity weight (short position)")
    all_weights = [line.weight for line in snapshot.lines if line.weight is not None]
    if all_weights and abs(sum(all_weights) - 1.0) > config.weight_sum_tolerance:
        reasons.append(f"file weights sum to {sum(all_weights):.1%}")
    n = len(weights)
    if n < config.min_constituents:
        reasons.append(f"{n} equity constituent(s) (min {config.min_constituents})")
    if n > config.max_constituents:
        reasons.append(f"{n} equity constituents (max {config.max_constituents})")

    if reasons or equity_share <= 0:
        return ConstituentWeights(snapshot.etf_ticker, snapshot.as_of, {}, equity_share, reasons or ["no equity"],
                                  snapshot.source)
    normalised = {t: w / equity_share for t, w in sorted(weights.items(), key=lambda kv: -kv[1])}
    return ConstituentWeights(snapshot.etf_ticker, snapshot.as_of, normalised, equity_share, [], snapshot.source)
