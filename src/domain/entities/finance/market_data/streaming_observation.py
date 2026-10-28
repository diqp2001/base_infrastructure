"""
Streaming market observations and whether they may be used as CURRENT market data (pure; no I/O).

An observation records what a data source reported for one instrument:

    observation_type   QUOTE (bid / ask / sizes), TRADE (last price / size), BAR, SNAPSHOT (one-off request)
    data_state         LIVE, FROZEN (last value outside market hours), DELAYED, DELAYED_FROZEN, UNKNOWN
                       (IBKR marketDataType 1 / 2 / 3 / 4)
    receipt times      when each side reached us (per field); ``event_time`` when the source stamps the event
                       (IBKR tick-by-tick, or the last-trade timestamp tick), otherwise None — a receipt time is
                       never presented as an exchange time

``assess`` decides, for a decision at ``now``, whether the observation is current: entitled, live (unless the use
accepts delayed data), fresh, and a valid two-sided quote (quote_validation.validate_quote: missing side, zero,
crossed, spread, stale). Only a CURRENT, LIVE, valid two-sided quote may price an execution; a midpoint is never an
executable price by itself, and a TRADES history says nothing about quote permissions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.domain.entities.factor.quote_validation import INTRADAY_LIQUID, Quote, QuotePolicy, validate_quote


class ObservationType(str, Enum):
    QUOTE = "quote"
    TRADE = "trade"
    BAR = "bar"
    SNAPSHOT = "snapshot"


class MarketDataState(str, Enum):
    LIVE = "live"
    FROZEN = "frozen"
    DELAYED = "delayed"
    DELAYED_FROZEN = "delayed_frozen"
    UNKNOWN = "unknown"

    @classmethod
    def from_ibkr(cls, market_data_type: Optional[int]) -> "MarketDataState":
        return {1: cls.LIVE, 2: cls.FROZEN, 3: cls.DELAYED, 4: cls.DELAYED_FROZEN}.get(market_data_type, cls.UNKNOWN)


@dataclass(frozen=True)
class StreamingObservation:
    instrument: str                                # instrument key (e.g. 'STK:JPM', 'OPT:SPY   261120C00650000')
    observation_type: ObservationType
    source: str                                    # e.g. 'IBKR'
    data_state: MarketDataState
    received_at: datetime                          # latest receipt time of any field (UTC, aware)
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    last: Optional[float] = None
    last_size: Optional[float] = None
    bid_received_at: Optional[datetime] = None
    ask_received_at: Optional[datetime] = None
    last_received_at: Optional[datetime] = None
    event_time: Optional[datetime] = None          # source-stamped time of the event, when provided
    request_id: Optional[int] = None
    snapshot: bool = False

    @property
    def quote_time(self) -> Optional[datetime]:
        """The OLDER side of the quote: a quote is only as fresh as its stalest side."""
        times = [t for t in (self.bid_received_at, self.ask_received_at) if t is not None]
        return min(times) if times else None

    @property
    def midpoint(self) -> Optional[float]:
        """Indicative only (never an executable price)."""
        if self.bid is None or self.ask is None or self.bid <= 0 or self.ask <= 0:
            return None
        return (self.bid + self.ask) / 2.0


class Usability(str, Enum):
    CURRENT = "current"                # may be used as current market data
    STALE = "stale"
    DELAYED = "delayed"                # delayed / frozen data where live data is required
    INVALID = "invalid"                # quote rules failed (missing side, zero, crossed, spread ...)
    NOT_ENTITLED = "not_entitled"      # the source refused the subscription (permissions)
    MISSING = "missing"                # nothing received yet


@dataclass(frozen=True)
class Assessment:
    usability: Usability
    executable: bool                   # a current, live, valid two-sided quote: may price an order
    reasons: Tuple[str, ...] = field(default_factory=tuple)
    age: Optional[timedelta] = None

    @property
    def current(self) -> bool:
        return self.usability is Usability.CURRENT


def _utc(t: datetime) -> datetime:
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def assess(observation: Optional[StreamingObservation], now: datetime, policy: QuotePolicy = INTRADAY_LIQUID,
           require_live: bool = True, entitlement_error: Optional[Tuple[int, str]] = None) -> Assessment:
    """Whether ``observation`` is current market data for a decision at ``now`` (see module doc)."""
    if entitlement_error is not None:
        code, message = entitlement_error
        return Assessment(Usability.NOT_ENTITLED, False, (f"source refused the data ({code}): {message}",))
    if observation is None:
        return Assessment(Usability.MISSING, False, ("no observation received",))
    now = _utc(now)
    reasons: List[str] = []
    if require_live and observation.data_state is not MarketDataState.LIVE:
        return Assessment(Usability.DELAYED, False,
                          (f"data state is {observation.data_state.value}: live data required",))
    if observation.observation_type is ObservationType.TRADE or (observation.bid is None and observation.ask is None):
        t = observation.last_received_at or observation.received_at
        age = now - _utc(t)
        if policy.max_age is not None and age > policy.max_age:
            return Assessment(Usability.STALE, False, (f"last trade received {age} ago > {policy.max_age}",), age)
        if observation.last is None or not observation.last > 0:
            return Assessment(Usability.INVALID, False, ("no positive last price",), age)
        return Assessment(Usability.CURRENT, False, ("a last trade is not a quote: not executable",), age)
    observed = observation.quote_time or observation.received_at
    age = now - _utc(observed)
    results = validate_quote(Quote(observation.bid, observation.ask, _utc(observed)), policy, decision_time=now)
    failed = [r for r in results if not r.passed]
    stale = [r for r in failed if r.rule == "fresh"]
    invalid = [r for r in failed if r.rule != "fresh"]
    if invalid:
        return Assessment(Usability.INVALID, False, tuple(r.reason for r in invalid), age)
    if stale:
        return Assessment(Usability.STALE, False, tuple(r.reason for r in stale), age)
    executable = observation.data_state is MarketDataState.LIVE
    if not executable:
        reasons.append(f"{observation.data_state.value} data: never executable")
    return Assessment(Usability.CURRENT, executable, tuple(reasons), age)


def to_dict(observation: StreamingObservation) -> Dict:
    d = {k: getattr(observation, k) for k in observation.__dataclass_fields__}
    d["observation_type"] = observation.observation_type.value
    d["data_state"] = observation.data_state.value
    return d
