"""
IBKR as the dispersion screener's OptionMarketDataPort (P.03). READ-ONLY: contract details, option chains
(reqSecDefOptParams) and streaming market data with IBKR's option model greeks (tickOptionComputation). This class
has no order method; run it on its own client id.

Cost: streaming market data for instruments covered by the account's subscriptions is free; regulatory snapshots
(snapshot=True on a non-subscribed instrument) are charged, so this adapter never requests snapshots: it streams,
waits for the fields it needs (or a timeout) and cancels. At most `max_lines` subscriptions at a time (IBKR's
default is 100 lines per login, shared with every other client of that login, e.g. the trader).

Market data type 2 (frozen) is requested: IBKR sends live data when the market is open and the last values when it
is closed. Each quote carries the type IBKR reported (1 live, 2 frozen, 3 / 4 delayed) so the screen can refuse
frozen or delayed prices instead of mixing them with live ones.

Only the current day exists here: any other screening date raises HistoricalDataUnavailable.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from ibapi.contract import Contract

from src.domain.entities.finance.dispersion.option_data import (
    Greeks, OptionChain, OptionContractSpec, OptionQuote, Quote, Underlying, UnderlyingQuote,
)
from src.domain.ports.finance.dispersion.option_market_data_port import (
    HistoricalDataUnavailable, MarketDataUnavailable, OptionMarketDataPort,
)

logger = logging.getLogger(__name__)

US_EXCHANGES = {"NYSE", "NASDAQ", "ARCA", "AMEX", "BATS", "IEX", "NYSE ARCA", "CBOE", "PINK"}
BID, ASK, LAST, CLOSE = 1, 2, 4, 9
DELAYED_BID, DELAYED_ASK, DELAYED_LAST, DELAYED_CLOSE = 66, 67, 68, 75
BID_SIZE, ASK_SIZE, VOLUME = 0, 3, 8
CALL_OPEN_INTEREST, PUT_OPEN_INTEREST = 27, 28
MODEL_GREEKS, DELAYED_MODEL_GREEKS = 13, 83
BID_COMPUTATION, ASK_COMPUTATION = (10, 80), (11, 81)   # IBKR's model on the bid / ask price (live, delayed)
FROZEN = 2


def ib_symbol(symbol: str) -> str:
    """Issuer tickers write share classes with a dot (BRK.B); IBKR with a space (BRK B)."""
    return symbol.replace(".", " ").replace("/", " ").strip().upper()


def _value(x, low=-math.inf, high=math.inf) -> Optional[float]:
    """IBKR's 'not computed' values (None, -1 / -2 sentinels, DBL_MAX) -> None."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or abs(x) >= 1e100 or not (low <= x <= high):
        return None
    return x


def _side_vol(option_ticks: dict, ticks: tuple) -> Optional[float]:
    for tick in ticks:
        if tick in option_ticks:
            return _value(option_ticks[tick].get('implied_vol'), 1e-6, 20.0)
    return None


def greeks_from(option_ticks: dict, source_prefix: str = "IBKR") -> Greeks:
    tick = MODEL_GREEKS if MODEL_GREEKS in option_ticks else DELAYED_MODEL_GREEKS
    g = option_ticks.get(tick)
    bid_iv, ask_iv = _side_vol(option_ticks, BID_COMPUTATION), _side_vol(option_ticks, ASK_COMPUTATION)
    if not g:
        return Greeks(source="none", bid_implied_vol=bid_iv, ask_implied_vol=ask_iv)
    return Greeks(
        implied_vol=_value(g.get('implied_vol'), 1e-6, 20.0),
        delta=_value(g.get('delta'), -1.0, 1.0),
        gamma=_value(g.get('gamma'), 0.0),
        vega=_value(g.get('vega'), 0.0),
        theta=_value(g.get('theta'), high=1e6),
        underlying_price=_value(g.get('underlying_price'), 1e-9),
        model_price=_value(g.get('price'), 0.0),
        greeks_time=g.get('received'),
        source=f"{source_prefix} model ({tick})",
        bid_implied_vol=bid_iv, ask_implied_vol=ask_iv)


def quote_from(data: dict, market_data_type: Optional[int], error: Optional[str]) -> Quote:
    prices, sizes = data.get('prices', {}), data.get('sizes', {})
    received = data.get('received', {})

    def price(live, delayed):
        v = _value(prices.get(live))
        return v if v is not None else _value(prices.get(delayed))

    times = [received.get(t) for t in (BID, ASK, DELAYED_BID, DELAYED_ASK) if received.get(t)]
    return Quote(
        bid=price(BID, DELAYED_BID), ask=price(ASK, DELAYED_ASK), last=price(LAST, DELAYED_LAST),
        close=price(CLOSE, DELAYED_CLOSE), bid_size=_value(sizes.get(BID_SIZE)), ask_size=_value(sizes.get(ASK_SIZE)),
        volume=_value(sizes.get(VOLUME)), quote_time=max(times) if times else None,
        market_data_type=market_data_type, error=error)


class IBKROptionMarketData(OptionMarketDataPort):

    def __init__(self, client, today: Callable[[], date] = date.today, max_lines: int = 40,
                 timeout_seconds: float = 12.0, lookup_timeout_seconds: float = 15.0,
                 first_req_id: int = 700_000, market_data_type: int = FROZEN, poll_seconds: float = 0.1,
                 pause_seconds: float = 0.2, message_seconds: float = 0.04):
        self.client = client
        self._today = today
        self.max_lines = max_lines
        self.timeout_seconds = timeout_seconds
        self.lookup_timeout_seconds = lookup_timeout_seconds
        self._next_req_id = first_req_id
        self.poll_seconds = poll_seconds
        self.pause_seconds = pause_seconds        # between two lookups / quote batches: a gentle pace for a shared gateway
        self._last_request = 0.0
        self.message_seconds = message_seconds    # between two subscribe / cancel messages: IBKR allows ~50 per s
        self.market_data_type = market_data_type
        self._type_requested = False

    # ---- helpers ----
    def _req_id(self) -> int:
        self._next_req_id += 1
        return self._next_req_id

    def _check_date(self, screening_date: date) -> None:
        if screening_date != self._today():
            raise HistoricalDataUnavailable(
                f"IBKR serves current option data only (screening date {screening_date}, today {self._today()})")

    def _wait(self, done: Callable[[], bool], timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if done():
                return True
            time.sleep(self.poll_seconds)
        return done()

    def _pace(self) -> None:
        wait = self._last_request + self.pause_seconds - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _await_lookup(self, req: int, done: set, what: str) -> None:
        """A lookup ends with its End callback or an error; neither within the timeout = the gateway did not answer
        (raised, so a silent gateway never turns into "not found")."""
        if not self._wait(lambda: req in done, self.lookup_timeout_seconds):
            raise MarketDataUnavailable(f"IBKR did not answer the {what} request within "
                                        f"{self.lookup_timeout_seconds:g} s")

    def _ensure_data_type(self) -> None:
        if not self._type_requested:
            self.client.request_market_data_type(self.market_data_type)
            self._type_requested = True

    # ---- port ----
    def resolve_underlyings(self, symbols: Sequence[str], screening_date: date) -> Dict[str, Optional[Underlying]]:
        self._check_date(screening_date)
        out: Dict[str, Optional[Underlying]] = {}
        for symbol in symbols:
            contract = Contract()
            contract.symbol, contract.secType, contract.exchange, contract.currency = ib_symbol(symbol), "STK", "SMART", "USD"
            req = self._req_id()
            self._pace()
            self.client.request_contract_details(req, contract)
            self._await_lookup(req, self.client.contract_details_done, f"{symbol} contract details")
            details = [d for d in self.client.contract_details.get(req, []) if d.get('currency') == "USD"]
            us = [d for d in details if (d.get('primary_exchange') or "").upper() in US_EXCHANGES] or details
            if not us:
                error = self.client.request_errors.get(req)
                logger.info("%s: no US share at IBKR (%s)", symbol, error[1] if error else "no contract")
                out[symbol] = None
                continue
            d = us[0]
            out[symbol] = Underlying(symbol=symbol, con_id=int(d['contract_id']), sec_type="STK", currency="USD",
                                     primary_exchange=d.get('primary_exchange'), stock_type=d.get('stock_type') or None,
                                     long_name=d.get('long_name') or None)
        return out

    def option_chains(self, underlying: Underlying, screening_date: date) -> List[OptionChain]:
        self._check_date(screening_date)
        req = self._req_id()
        self._pace()
        self.client.request_option_chain(req, ib_symbol(underlying.symbol), underlying.sec_type, underlying.con_id)
        self._await_lookup(req, self.client.option_chains_done, f"{underlying.symbol} option chain")
        chains = []
        for row in self.client.option_chains.get(req, []):
            if row.get('exchange') != "SMART":
                continue
            try:
                multiplier = float(row.get('multiplier') or 0)
            except ValueError:
                continue
            expirations = tuple(sorted(datetime.strptime(e, "%Y%m%d").date() for e in row.get('expirations', [])))
            chains.append(OptionChain(underlying=underlying.symbol, trading_class=row.get('trading_class') or "",
                                      multiplier=multiplier, expirations=expirations,
                                      strikes=tuple(sorted(float(k) for k in row.get('strikes', []))),
                                      exchange="SMART", source="IBKR reqSecDefOptParams"))
        return chains

    def listed_strikes(self, chain: OptionChain, expiry: date, right: str, screening_date: date) -> Sequence[float]:
        """Contract details of every option of one expiry / right / trading class (one request)."""
        self._check_date(screening_date)
        c = Contract()
        c.symbol, c.secType, c.exchange, c.currency = ib_symbol(chain.underlying), "OPT", "SMART", "USD"
        c.lastTradeDateOrContractMonth, c.right = expiry.strftime("%Y%m%d"), right
        c.tradingClass, c.multiplier = chain.trading_class, f"{chain.multiplier:g}"
        req = self._req_id()
        self._pace()
        self.client.request_contract_details(req, c)
        self._await_lookup(req, self.client.contract_details_done, f"{chain.underlying} {expiry} strikes")
        return tuple(sorted({float(d['strike']) for d in self.client.contract_details.pop(req, [])
                             if d.get('strike') is not None}))

    def underlying_quotes(self, underlyings: Sequence[Underlying], screening_date: date) -> Dict[str, UnderlyingQuote]:
        self._check_date(screening_date)

        def contract_of(u: Underlying) -> Contract:
            c = Contract()
            c.conId, c.symbol, c.secType, c.exchange, c.currency = u.con_id, ib_symbol(u.symbol), "STK", "SMART", "USD"
            return c

        raw = self._stream([(u.symbol, contract_of(u)) for u in underlyings], generic_ticks="",
                           complete=lambda data: BID in data.get('prices', {}) and ASK in data.get('prices', {}))
        by_symbol = {u.symbol: u for u in underlyings}
        return {s: UnderlyingQuote(by_symbol[s], quote_from(data, mdt, err), source="IBKR")
                for s, (data, mdt, err) in raw.items()}

    def option_quotes(self, contracts: Sequence[OptionContractSpec], screening_date: date) -> Dict[str, OptionQuote]:
        self._check_date(screening_date)

        def contract_of(spec: OptionContractSpec) -> Contract:
            c = Contract()
            c.symbol, c.secType, c.exchange, c.currency = ib_symbol(spec.underlying), "OPT", "SMART", "USD"
            c.lastTradeDateOrContractMonth = spec.expiry.strftime("%Y%m%d")
            c.strike, c.right, c.multiplier = float(spec.strike), spec.right, f"{spec.multiplier:g}"
            c.tradingClass = spec.trading_class
            return c

        def complete(data):
            prices, option = data.get('prices', {}), data.get('option', {})
            # each quoted side also brings the broker's volatility for that price (ticks 10 / 11)
            sides = [ticks for side, ticks in ((BID, BID_COMPUTATION), (ASK, ASK_COMPUTATION))
                     if (_value(prices.get(side), 0.0) or 0) > 0]
            return (BID in prices and ASK in prices and MODEL_GREEKS in option
                    and all(any(t in option for t in ticks) for ticks in sides))

        raw = self._stream([(spec.key, contract_of(spec)) for spec in contracts], generic_ticks="100,101",
                           complete=complete)
        by_key = {spec.key: spec for spec in contracts}
        out = {}
        for key, (data, mdt, err) in raw.items():
            spec = by_key[key]
            sizes = data.get('sizes', {})
            oi = _value(sizes.get(CALL_OPEN_INTEREST if spec.right == "C" else PUT_OPEN_INTEREST), 0.0)
            out[key] = OptionQuote(contract=spec, quote=quote_from(data, mdt, err),
                                   greeks=greeks_from(data.get('option', {})), open_interest=oi, source="IBKR")
        return out

    # ---- streaming in batches ----
    def _stream(self, items: Iterable, generic_ticks: str, complete: Callable[[dict], bool]) -> Dict[str, tuple]:
        """Subscribe up to max_lines at a time, wait until each is complete (or the batch timeout), cancel."""
        self._ensure_data_type()
        items = list(items)
        out: Dict[str, tuple] = {}
        for start in range(0, len(items), self.max_lines):
            self._pace()
            batch = [(key, contract, self._req_id()) for key, contract in items[start:start + self.max_lines]]
            for key, contract, req in batch:
                self.client.request_market_data(req, contract, snapshot=False, generic_tick_list=generic_ticks)
                time.sleep(self.message_seconds)

            def finished():
                return all(complete(self.client.market_data.get(req, {})) or req in self.client.market_data_errors
                           for _, _, req in batch)

            self._wait(finished, self.timeout_seconds)
            for key, _, req in batch:
                error = self.client.market_data_errors.get(req)             # read first: cancel drops the data
                out[key] = (dict(self.client.market_data.get(req, {})), self.client.market_data_type.get(req),
                            f"{error[0]}: {error[1]}" if error else None)
                try:
                    self.client.cancel_market_data(req)
                except Exception as e:
                    logger.debug("cancel %s failed: %s", req, e)
                time.sleep(self.message_seconds)
        return out
