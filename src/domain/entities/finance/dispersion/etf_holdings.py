"""
ETF listings and holdings snapshots (value objects) and the rules that turn a snapshot into screenable constituent
weights. Pure: the issuer adapters build these objects, nothing here does I/O.

Weights are fractions (0.0886, not 8.86). A snapshot keeps every line of the issuer file (cash, FX, futures ...);
`prepare_constituents` keeps the equity lines and normalises their weights to sum to 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig

EQUITY = "equity"
NON_EQUITY_CLASSES = ("cash", "fx", "future", "money_market", "other")


@dataclass(frozen=True)
class EtfListing:
    """An ETF as an issuer lists it (discovery, no holdings yet)."""
    ticker: str
    name: str
    issuer: str
    asset_class: Optional[str] = None        # issuer's asset class ("Equity", "Fixed Income" ...); None = unknown
    sub_asset_class: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    product_ref: Optional[str] = None        # issuer-specific key to its holdings file (page path, fund uri ...)
    total_net_assets: Optional[float] = None
    leverage_factor: float = 1.0
    replication: Optional[str] = None


@dataclass(frozen=True)
class HoldingLine:
    ticker: str
    name: str
    weight: Optional[float]                  # fraction of the fund; None = the file gives none
    asset_class: str                         # EQUITY or one of NON_EQUITY_CLASSES
    sector: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    market_value: Optional[float] = None
    quantity: Optional[float] = None
    identifier: Optional[str] = None         # CUSIP / SEDOL / ISIN when the file gives one


@dataclass(frozen=True)
class EtfHoldingsSnapshot:
    etf_ticker: str
    issuer: str
    as_of: date                              # the issuer's "holdings as of" date
    lines: Tuple[HoldingLine, ...]
    source: str                              # URL (or archive path) of the file
    retrieved_at: datetime
    fund_name: Optional[str] = None

    def equity_lines(self) -> List[HoldingLine]:
        return [line for line in self.lines if line.asset_class == EQUITY]


@dataclass(frozen=True)
class ConstituentWeights:
    """Result of `prepare_constituents`: usable (ok) or rejected with the reasons."""
    etf_ticker: str
    as_of: date
    weights: Dict[str, float]                # ticker -> normalised weight (sum 1); empty when rejected
    equity_share: float                      # sum of the raw equity weights (fraction of the fund)
    reasons: List[str] = field(default_factory=list)
    source: str = ""

    @property
    def ok(self) -> bool:
        return not self.reasons

    @property
    def count(self) -> int:
        return len(self.weights)


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
