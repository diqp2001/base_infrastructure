"""
Market data exchanged through OptionMarketDataPort / PriceHistoryPort: listed-option chains, option quotes with the
broker's model greeks, and underlying quotes. Data carriers of the ports, not domain entities (the instruments are
ETFShare / CompanyShare / ETFShareOption / CompanyShareOption); adapters fill them, the screen never sees a broker API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class Underlying:
    """A tradeable listed share (stock or ETF) resolved at the broker."""
    symbol: str
    con_id: int
    sec_type: str                         # STK
    currency: str
    primary_exchange: Optional[str] = None
    stock_type: Optional[str] = None      # COMMON, ETF, ADR, REIT ... (broker classification)
    long_name: Optional[str] = None


@dataclass(frozen=True)
class OptionChain:
    """One trading class of the options listed on an underlying."""
    underlying: str
    trading_class: str
    multiplier: float
    expirations: Tuple[date, ...]
    strikes: Tuple[float, ...]
    exchange: str = "SMART"
    source: str = ""


@dataclass(frozen=True)
class OptionContractSpec:
    underlying: str
    expiry: date
    strike: float
    right: str                            # "C" / "P"
    multiplier: float
    trading_class: str

    @property
    def key(self) -> str:
        return f"{self.underlying} {self.expiry:%Y%m%d} {self.right} {self.strike:g} x{self.multiplier:g}"


@dataclass(frozen=True)
class Quote:
    """Bid / ask / last with the time each was received and the broker's data type (live, frozen, delayed)."""
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    close: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    volume: Optional[float] = None
    quote_time: Optional[datetime] = None         # latest bid / ask update
    market_data_type: Optional[int] = None        # 1 live, 2 frozen, 3 delayed, 4 delayed frozen
    error: Optional[str] = None

    @property
    def two_sided(self) -> bool:
        return self.bid is not None and self.ask is not None and self.bid > 0 and self.ask > 0 and self.ask >= self.bid

    @property
    def mid(self) -> Optional[float]:
        return (self.bid + self.ask) / 2.0 if self.two_sided else None

    @property
    def spread_pct(self) -> Optional[float]:
        """(ask - bid) / mid."""
        mid = self.mid
        return (self.ask - self.bid) / mid if mid else None


@dataclass(frozen=True)
class Greeks:
    implied_vol: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    underlying_price: Optional[float] = None
    model_price: Optional[float] = None
    greeks_time: Optional[datetime] = None
    source: str = ""                              # e.g. "IBKR model (13)"
    bid_implied_vol: Optional[float] = None       # the volatility the broker's model implies from the bid price
    ask_implied_vol: Optional[float] = None       # ... from the ask price

    @property
    def complete(self) -> bool:
        return None not in (self.implied_vol, self.delta, self.gamma, self.vega, self.theta)


@dataclass(frozen=True)
class OptionQuote:
    contract: OptionContractSpec
    quote: Quote
    greeks: Greeks
    open_interest: Optional[float] = None
    source: str = ""


@dataclass(frozen=True)
class UnderlyingQuote:
    underlying: Underlying
    quote: Quote
    source: str = ""

    @property
    def price(self) -> Optional[float]:
        """Mid when two-sided, else last, else close (the screen records which it used through the quote)."""
        return self.quote.mid or self.quote.last or self.quote.close
