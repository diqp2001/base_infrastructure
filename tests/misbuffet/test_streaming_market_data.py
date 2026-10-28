"""P.02 — streaming market data: typed, timestamped, state-aware observations (fakes only; no IBKR connection)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.application.services.misbuffet.data.streaming_market_data import StreamingMarketDataService
from src.domain.entities.finance.market_data.streaming_observation import (
    MarketDataState,
    ObservationType,
    StreamingObservation,
    Usability,
    assess,
)

T0 = datetime(2026, 10, 28, 14, 30, tzinfo=timezone.utc)


class FakeClient:
    """The attributes IBTWSClient fills from its callbacks, and the request methods the service calls."""

    def __init__(self):
        self.market_data, self.market_data_type, self.market_data_errors, self.tick_by_tick = {}, {}, {}, {}
        self.connection_listeners = []
        self.requests, self.cancelled, self.tbt_requests, self.tbt_cancelled = [], [], [], []

    def is_connected(self):
        return True

    def request_market_data(self, req_id, contract, snapshot=False):
        self.requests.append((req_id, contract, snapshot))

    def request_tick_by_tick(self, req_id, contract, tick_type):
        self.tbt_requests.append((req_id, tick_type))

    def cancel_market_data(self, req_id):
        self.cancelled.append(req_id)

    def cancel_tick_by_tick(self, req_id):
        self.tbt_cancelled.append(req_id)

    def tick(self, req_id, tick_type, price, at):
        d = self.market_data.setdefault(req_id, {"prices": {}, "sizes": {}, "generic": {}, "strings": {}})
        d["prices"][tick_type] = price
        d.setdefault("received", {})[tick_type] = at

    def size(self, req_id, tick_type, value, at):
        d = self.market_data.setdefault(req_id, {"prices": {}, "sizes": {}, "generic": {}, "strings": {}})
        d["sizes"][tick_type] = value
        d.setdefault("received_sizes", {})[tick_type] = at


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def env():
    client, clock = FakeClient(), Clock(T0)
    return SimpleNamespace(client=client, clock=clock, svc=StreamingMarketDataService(client, clock=clock))


def _quote(env, req, bid=100.0, ask=100.05, at=T0, state=1):
    env.client.tick(req, 1, bid, at)
    env.client.tick(req, 2, ask, at)
    env.client.size(req, 0, 300, at)
    env.client.size(req, 3, 200, at)
    if state is not None:
        env.client.market_data_type[req] = state


def test_live_quote_ticks_become_a_current_executable_quote_observation(env):
    req = env.svc.subscribe("STK:JPM", "contract")
    assert env.svc.observation("STK:JPM") is None and env.svc.assess("STK:JPM").usability is Usability.MISSING
    _quote(env, req)
    obs = env.svc.observation("STK:JPM")
    assert (obs.observation_type, obs.data_state, obs.source) == (ObservationType.QUOTE, MarketDataState.LIVE, "IBKR")
    assert (obs.bid, obs.ask, obs.bid_size, obs.ask_size) == (100.0, 100.05, 300, 200)
    assert obs.bid_received_at == T0 and obs.event_time is None          # receipt time is never an exchange time
    a = env.svc.assess("STK:JPM", T0 + timedelta(seconds=5))
    assert a.current and a.executable and a.age == timedelta(seconds=5)


def test_a_quote_is_only_as_fresh_as_its_older_side(env):
    req = env.svc.subscribe("STK:JPM", "c")
    _quote(env, req)
    env.client.tick(req, 2, 100.06, T0 + timedelta(minutes=30))         # only the ask keeps updating
    a = env.svc.assess("STK:JPM", T0 + timedelta(minutes=31))
    assert a.usability is Usability.STALE and not a.executable and "stale" in a.reasons[0]


def test_delayed_and_frozen_data_are_never_current_where_live_is_required(env):
    req = env.svc.subscribe("STK:BAC", "c")
    _quote(env, req, state=3)
    assert env.svc.assess("STK:BAC").usability is Usability.DELAYED
    relaxed = env.svc.assess("STK:BAC", require_live=False)
    assert relaxed.current and not relaxed.executable                    # usable for display, never for execution
    req2 = env.svc.subscribe("STK:C", "c")
    env.client.tick(req2, 66, 50.0, T0)                                  # delayed bid / ask tick types, no type yet
    env.client.tick(req2, 67, 50.1, T0)
    assert env.svc.observation("STK:C").data_state is MarketDataState.DELAYED
    req3 = env.svc.subscribe("STK:WFC", "c")
    _quote(env, req3, state=2)
    assert env.svc.assess("STK:WFC").usability is Usability.DELAYED      # frozen


def test_an_entitlement_error_makes_the_subscription_not_entitled(env):
    req = env.svc.subscribe("STK:MSFT", "c")
    _quote(env, req)
    env.client.market_data_errors[req] = (354, "Requested market data is not subscribed")
    a = env.svc.assess("STK:MSFT")
    assert a.usability is Usability.NOT_ENTITLED and "354" in a.reasons[0] and not a.executable


@pytest.mark.parametrize("bid,ask,word", [(100.1, 100.0, "crossed"), (0.0, 100.0, "positive"), (None, 100.0, "missing")])
def test_invalid_quotes_never_count_as_current(env, bid, ask, word):
    req = env.svc.subscribe("STK:X", "c")
    if bid is not None:
        env.client.tick(req, 1, bid, T0)
    env.client.tick(req, 2, ask, T0)
    env.client.market_data_type[req] = 1
    a = env.svc.assess("STK:X")
    assert a.usability is Usability.INVALID and word in " ".join(a.reasons)


def test_a_last_trade_alone_is_current_but_never_executable_and_keeps_its_exchange_time(env):
    req = env.svc.subscribe("STK:Y", "c")
    env.client.tick(req, 4, 42.0, T0)
    env.client.market_data[req]["last_trade_time"] = T0 - timedelta(seconds=3)
    env.client.market_data_type[req] = 1
    obs = env.svc.observation("STK:Y")
    assert obs.observation_type is ObservationType.TRADE and obs.event_time == T0 - timedelta(seconds=3)
    a = env.svc.assess("STK:Y")
    assert a.current and not a.executable


def test_tick_by_tick_events_replace_older_ticks_and_carry_the_event_time(env):
    env.svc.subscribe("STK:Z", "c", tick_by_tick="BidAsk")
    sub = env.svc.subscriptions()[0]
    _quote(env, sub.req_id, at=T0 - timedelta(seconds=10))
    env.client.tick_by_tick[sub.tbt_req_id] = {"bid": 10.0, "ask": 10.02, "bid_size": 5.0, "ask_size": 7.0,
                                              "quote_event_time": T0 - timedelta(seconds=1), "quote_received": T0}
    obs = env.svc.observation("STK:Z")
    assert (obs.bid, obs.ask, obs.event_time) == (10.0, 10.02, T0 - timedelta(seconds=1))
    assert env.client.tbt_requests == [(sub.tbt_req_id, "BidAsk")]


def test_a_disconnection_stops_current_data_and_a_resubscription_starts_clean(env):
    req = env.svc.subscribe("STK:JPM", "c")
    _quote(env, req)
    for listener in env.client.connection_listeners:
        listener()                                                        # IBTWSClient.connectionClosed
    a = env.svc.assess("STK:JPM")
    assert a.usability is Usability.STALE and "connection closed" in a.reasons[0]
    new = env.svc.resubscribe()
    assert new["STK:JPM"] != req and req not in env.client.market_data   # old values discarded
    assert env.svc.assess("STK:JPM").usability is Usability.MISSING       # nothing new yet: not current
    _quote(env, new["STK:JPM"])
    assert env.svc.assess("STK:JPM").executable and env.svc.subscriptions()[0].generation == 1


def test_the_line_limit_refuses_new_subscriptions_and_unsubscribe_cancels(env):
    svc = StreamingMarketDataService(env.client, clock=env.clock, max_lines=3)
    svc.subscribe("A", "c")
    svc.subscribe("B", "c", tick_by_tick="AllLast")                       # two lines
    assert svc.subscribe("A", "c") == svc.subscriptions()[0].req_id       # one subscription per instrument
    with pytest.raises(RuntimeError):
        svc.subscribe("C", "c")
    b = [s for s in svc.subscriptions() if s.instrument == "B"][0]
    svc.unsubscribe("B")
    assert b.req_id in env.client.cancelled and b.tbt_req_id in env.client.tbt_cancelled
    svc.subscribe("C", "c")


def test_the_status_rows_report_state_and_reasons(env):
    req = env.svc.subscribe("STK:JPM", "c")
    _quote(env, req, state=3)
    row = env.svc.status()[0]
    assert row["data_state"] == "delayed" and row["usability"] == "delayed" and row["reasons"]


def test_midpoint_is_indicative_only():
    obs = StreamingObservation("STK:Q", ObservationType.QUOTE, "IBKR", MarketDataState.DELAYED, T0, bid=9.9, ask=10.1,
                               bid_received_at=T0, ask_received_at=T0)
    assert obs.midpoint == pytest.approx(10.0)
    assert not assess(obs, T0, require_live=False).executable


# ── the real IBTWSClient callbacks (never connected) ─────────────────────────────────────────────────────────────

def test_the_ibkr_client_records_state_errors_receipt_and_trade_times():
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    c = IBTWSClient("127.0.0.1", 7497, 99)
    c.market_data_subscriptions.add(5)
    c.tickPrice(5, 1, 99.5, None)
    assert c.market_data[5]["received"][1].tzinfo is not None
    c.marketDataType(5, 3)
    assert c.market_data_type[5] == 3
    c.tickString(5, 45, "1793000000")
    assert c.market_data[5]["last_trade_time"] == datetime.fromtimestamp(1793000000, tz=timezone.utc)
    c.error(5, 10167, "Displaying delayed market data")                   # a notice, not an error
    assert 5 not in c.market_data_errors
    c.error(5, 354, "Requested market data is not subscribed")
    assert c.market_data_errors[5][0] == 354
    c.error(777, 354, "not a market-data request")                        # other requests are untouched
    assert 777 not in c.market_data_errors
    closed = []
    c.connection_listeners.append(lambda: closed.append(True))
    c.connectionClosed()
    assert closed == [True] and not c.connected_flag
    c.tickByTickBidAsk(6, 1793000001, 10.0, 10.1, 3, 4, None)
    assert c.tick_by_tick[6]["quote_event_time"] == datetime.fromtimestamp(1793000001, tz=timezone.utc)
    c.cancel_market_data(5)                                               # disconnected: state still cleared
    assert 5 not in c.market_data_type and 5 not in c.market_data_errors
