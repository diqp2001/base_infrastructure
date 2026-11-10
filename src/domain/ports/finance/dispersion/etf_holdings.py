"""
ETF listings and holdings snapshots read from the issuers' files - the data the holdings ports exchange (not
domain entities: the ETF is an
ETFShare, its holdings Universe / UniverseConstituent rows). The issuer adapters build these objects.

Weights are fractions (0.0886, not 8.86). A snapshot keeps every line of the issuer file (cash, FX, futures ...);
EtfUniverseService's prepare_constituents keeps the equity lines and normalises their weights to sum to 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


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
