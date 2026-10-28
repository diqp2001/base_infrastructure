"""
StreamingMarketDataService — live quotes and trades as typed, state-aware observations (P.02).

It owns the streaming subscriptions on an IBTWSClient-like client and turns what the client captured into
``StreamingObservation`` s (domain/entities/finance/market_data/streaming_observation.py):

* subscribe / unsubscribe by instrument key; one subscription per instrument; at most ``max_lines`` concurrent lines
  (IBKR's default market-data line limit is 100) — beyond that a subscription is refused, never silently dropped;
* normalisation of IBKR ticks: bid 1 / ask 2 / last 4 and sizes 0 / 3 / 5, delayed ticks 66-71, last-trade
  timestamp (tick 45 / 88) as the trade's event time; tick-by-tick events (IBKR-stamped) when requested;
* state per subscription: IBKR marketDataType (live / frozen / delayed / delayed-frozen); an error IBKR returned for
  the request (e.g. 354 / 10089 no market data permission, 200 unknown contract) makes it NOT_ENTITLED;
* disconnection: every observation stops being current the moment the connection closes; ``resubscribe`` (after a
  reconnect) requests every subscription again under new request ids and discards the old values;
* ``assess`` = domain ``assess``: current only when entitled, live (unless the caller accepts delayed data), fresh
  and a valid two-sided quote; only that is executable.

Historical bars and factor values are untouched: this service only reads streaming state.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from src.domain.entities.factor.quote_validation import INTRADAY_LIQUID, QuotePolicy
from src.domain.entities.finance.market_data.streaming_observation import (
    Assessment,
    MarketDataState,
    ObservationType,
    StreamingObservation,
    Usability,
    assess,
)

BID, ASK, LAST, BID_SIZE, ASK_SIZE, LAST_SIZE = 1, 2, 4, 0, 3, 5
D_BID, D_ASK, D_LAST, D_BID_SIZE, D_ASK_SIZE, D_LAST_SIZE = 66, 67, 68, 69, 70, 71
DEFAULT_MAX_LINES = 95                                      # below IBKR's default 100 market-data lines


@dataclass
class Subscription:
    instrument: str
    contract: object
    req_id: int
    snapshot: bool = False
    tick_by_tick: Optional[str] = None                      # 'BidAsk' / 'AllLast' ...
    tbt_req_id: Optional[int] = None
    subscribed_at: Optional[datetime] = None
    generation: int = 0                                     # incremented by every resubscription
    history: List[str] = field(default_factory=list)


class StreamingMarketDataService:

    def __init__(self, client, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 max_lines: int = DEFAULT_MAX_LINES, policy_for: Callable[[str], QuotePolicy] = lambda _: INTRADAY_LIQUID,
                 first_request_id: int = 70_000, source: str = "IBKR"):
        self.client = client
        self.clock = clock
        self.max_lines = max_lines
        self.policy_for = policy_for
        self.source = source
        self._ids = itertools.count(first_request_id)
        self._subs: Dict[str, Subscription] = {}
        self._lock = threading.Lock()
        self.connected = bool(getattr(client, "is_connected", lambda: True)())
        self.disconnected_at: Optional[datetime] = None
        listeners = getattr(client, "connection_listeners", None)
        if listeners is not None:
            listeners.append(self._on_connection_closed)

    # -- subscriptions ----------------------------------------------------------------------------------------------
    def _lines(self) -> int:
        return sum(1 + (1 if s.tick_by_tick else 0) for s in self._subs.values() if not s.snapshot)

    def subscribe(self, instrument: str, contract, tick_by_tick: Optional[str] = None, snapshot: bool = False) -> int:
        with self._lock:
            existing = self._subs.get(instrument)
            if existing is not None:
                return existing.req_id
            needed = 0 if snapshot else (1 + (1 if tick_by_tick else 0))
            if self._lines() + needed > self.max_lines:
                raise RuntimeError(f"market-data line limit reached ({self.max_lines}): '{instrument}' not subscribed")
            sub = Subscription(instrument, contract, next(self._ids), snapshot=snapshot, tick_by_tick=tick_by_tick,
                               subscribed_at=self.clock())
            self._request(sub)
            self._subs[instrument] = sub
            return sub.req_id

    def _request(self, sub: Subscription) -> None:
        self.client.request_market_data(sub.req_id, sub.contract, snapshot=sub.snapshot)
        if sub.tick_by_tick:
            sub.tbt_req_id = next(self._ids)
            self.client.request_tick_by_tick(sub.tbt_req_id, sub.contract, sub.tick_by_tick)

    def unsubscribe(self, instrument: str) -> None:
        with self._lock:
            sub = self._subs.pop(instrument, None)
        if sub is None:
            return
        self.client.cancel_market_data(sub.req_id)
        if sub.tbt_req_id is not None:
            self.client.cancel_tick_by_tick(sub.tbt_req_id)

    def subscriptions(self) -> List[Subscription]:
        return list(self._subs.values())

    # -- connection -------------------------------------------------------------------------------------------------
    def _on_connection_closed(self) -> None:
        self.connected = False
        self.disconnected_at = self.clock()

    def resubscribe(self) -> Dict[str, int]:
        """After a reconnect: every subscription requested again under new ids; old values discarded."""
        with self._lock:
            out = {}
            for sub in self._subs.values():
                for rid in (sub.req_id, sub.tbt_req_id):
                    if rid is not None:
                        getattr(self.client, "market_data", {}).pop(rid, None)
                        getattr(self.client, "market_data_type", {}).pop(rid, None)
                        getattr(self.client, "market_data_errors", {}).pop(rid, None)
                        getattr(self.client, "tick_by_tick", {}).pop(rid, None)
                sub.history.append(f"{self.clock().isoformat()} resubscribed (was {sub.req_id})")
                sub.req_id = next(self._ids)
                sub.generation += 1
                sub.subscribed_at = self.clock()
                self._request(sub)
                out[sub.instrument] = sub.req_id
            self.connected = True
            self.disconnected_at = None
            return out

    # -- observations -----------------------------------------------------------------------------------------------
    def observation(self, instrument: str) -> Optional[StreamingObservation]:
        sub = self._subs.get(instrument)
        if sub is None:
            return None
        raw = getattr(self.client, "market_data", {}).get(sub.req_id) or {}
        prices, sizes = raw.get("prices", {}), raw.get("sizes", {})
        received, received_sizes = raw.get("received", {}), raw.get("received_sizes", {})
        state = MarketDataState.from_ibkr(getattr(self.client, "market_data_type", {}).get(sub.req_id))

        def pick(live_tick, delayed_tick, table, times):
            if live_tick in table:
                return table[live_tick], times.get(live_tick)
            if delayed_tick in table:
                return table[delayed_tick], times.get(delayed_tick)
            return None, None

        bid, bid_t = pick(BID, D_BID, prices, received)
        ask, ask_t = pick(ASK, D_ASK, prices, received)
        last, last_t = pick(LAST, D_LAST, prices, received)
        bid_size, _ = pick(BID_SIZE, D_BID_SIZE, sizes, received_sizes)
        ask_size, _ = pick(ASK_SIZE, D_ASK_SIZE, sizes, received_sizes)
        last_size, _ = pick(LAST_SIZE, D_LAST_SIZE, sizes, received_sizes)
        if state is MarketDataState.UNKNOWN and any(t in prices for t in (D_BID, D_ASK, D_LAST)):
            state = MarketDataState.DELAYED                  # delayed tick types say so even without marketDataType
        event_time = raw.get("last_trade_time")
        tbt = getattr(self.client, "tick_by_tick", {}).get(sub.tbt_req_id) if sub.tbt_req_id is not None else None
        if tbt and tbt.get("quote_received") and (bid_t is None or tbt["quote_received"] >= bid_t):
            bid, ask = tbt.get("bid"), tbt.get("ask")
            bid_size, ask_size = tbt.get("bid_size"), tbt.get("ask_size")
            bid_t = ask_t = tbt["quote_received"]
            event_time = tbt.get("quote_event_time")
        if tbt and tbt.get("trade_received") and (last_t is None or tbt["trade_received"] >= last_t):
            last, last_size, last_t = tbt.get("last"), tbt.get("last_size"), tbt["trade_received"]
            if event_time is None:
                event_time = tbt.get("trade_event_time")
        times = [t for t in (bid_t, ask_t, last_t) if t is not None]
        if not times:
            return None
        kind = (ObservationType.SNAPSHOT if sub.snapshot else
                ObservationType.QUOTE if (bid is not None or ask is not None) else ObservationType.TRADE)
        return StreamingObservation(
            instrument=instrument, observation_type=kind, source=self.source, data_state=state,
            received_at=max(times), bid=bid, ask=ask, bid_size=bid_size, ask_size=ask_size, last=last,
            last_size=last_size, bid_received_at=bid_t, ask_received_at=ask_t, last_received_at=last_t,
            event_time=event_time, request_id=sub.req_id, snapshot=sub.snapshot)

    def assess(self, instrument: str, now: Optional[datetime] = None, require_live: bool = True) -> Assessment:
        now = now or self.clock()
        sub = self._subs.get(instrument)
        if sub is None:
            return Assessment(Usability.MISSING, False, (f"'{instrument}' is not subscribed",))
        errors = getattr(self.client, "market_data_errors", {})
        error = errors.get(sub.req_id) or (errors.get(sub.tbt_req_id) if sub.tbt_req_id is not None else None)
        if not self.connected:
            return Assessment(Usability.STALE, False,
                              (f"broker connection closed at {self.disconnected_at}: data not current",))
        return assess(self.observation(instrument), now, self.policy_for(instrument), require_live=require_live,
                      entitlement_error=error)

    def status(self, now: Optional[datetime] = None) -> List[dict]:
        """One row per subscription (monitoring): state, usability, age, reasons."""
        now = now or self.clock()
        rows = []
        for sub in self._subs.values():
            obs = self.observation(sub.instrument)
            a = self.assess(sub.instrument, now)
            rows.append({"instrument": sub.instrument, "req_id": sub.req_id, "generation": sub.generation,
                         "data_state": obs.data_state.value if obs else None, "usability": a.usability.value,
                         "executable": a.executable, "age_seconds": a.age.total_seconds() if a.age else None,
                         "reasons": list(a.reasons)})
        return rows
