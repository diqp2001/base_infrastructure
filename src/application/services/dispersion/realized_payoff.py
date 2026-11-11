"""
Realized historical payoff of the dispersion structure (pure): at every past observation date t, the ATM ETF call and
the ATM constituent calls of the screen were opened and held to their expiry T; what did each side pay at T?

    DispersionPayoff_t            = Payoff_Basket,t - Payoff_ETF,t                   (per short ETF call, dollars)
    Payoff_ETF,t                  = m_etf * max(S_ETF,T - K_ETF,t, 0),     K_ETF,t = S_ETF,t
    Payoff_Basket,t               = sum_i q_i * m_i * max(S_i,T - K_i,t, 0), K_i,t = S_i,t
    q_i                           = the screen's replicate(): m_etf * w_i,t * S_ETF,t / S_i,t / m_i
    NormalizedDispersionPayoff_t  = DispersionPayoff_t / (m_etf * K_ETF,t)           (per dollar of ETF notional)
    DispersionPayoffReturn_t      = DispersionPayoff_t / Payoff_ETF,t                (None when Payoff_ETF,t = 0)

Expiry: the screen's rule on the standard monthly expiries (third Fridays): select_expiry with TARGET_DTE inside
[MIN_DTE, MAX_DTE] (DispersionScreenConfig) - the expiry the live screen picks, which most constituents list.
Settlement: the close of the last trading day on or before T (an expiry on an exchange holiday settles the day
before). No option prices, no implied volatility: realized payoffs only.

Call-payoff replication (returns, no option price): over the same trade's holding period t -> T,
    r                   = (P_T - P_t) / P_t
    ETFCallPayoff_t     = max(r_ETF, 0)                              (an ATM call's payoff / strike)
    BasketCallPayoff_t  = sum_i w_i,t * max(r_i, 0)                  (a portfolio of calls, NOT max(sum_i w_i r_i, 0))
    ReplicationDiff_t   = BasketCallPayoff_t - ETFCallPayoff_t
w_i,t = the holdings' value weights at t (weights_at). With replicate()'s sizing this equals NormalizedDispersionPayoff
(q_i m_i (S_i,T - K_i)+ = m_etf w_i S_ETF,t (r_i)+, divided by m_etf K_ETF,t = m_etf S_ETF,t).
Positive: the constituent calls paid more than the ETF call (favours long constituent calls / short ETF call).

Rolling statistics as of a date d (no look-ahead): the observations initiated in (d - 6 calendar months, d] whose
settlement day is <= d (completed), and that are complete (every price present). Unexpired and incomplete ones are
counted, never included. Missing prices never become zero.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor as Strategy, Leg,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_factor import (
    ShareOptionFactor,
)
from src.application.services.dispersion.screen_config import DispersionScreenConfig

Closes = Mapping[date, float]                 # trading day -> close (split-adjusted)
SETTLEMENT_SEARCH_DAYS = 4                    # an expiry settles on the last close at most this many days before it
MULTIPLIER = 100.0                            # standard US equity / ETF option (the screen's standard class)


def third_fridays(start: date, end: date) -> List[date]:
    """The standard monthly option expiries (third Friday of each month) between start and end."""
    out, year, month = [], start.year, start.month
    while (year, month) <= (end.year, end.month):
        first = date(year, month, 1)
        friday = first + timedelta(days=(4 - first.weekday()) % 7 + 14)
        if start <= friday <= end:
            out.append(friday)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def expiry_for(initiated: date, config: DispersionScreenConfig) -> Optional[date]:
    """The screen's expiry rule at an observation date."""
    return ShareOptionFactor.select_expiry(third_fridays(initiated, initiated + timedelta(days=config.max_dte)),
                                           initiated, config.target_dte, config.min_dte, config.max_dte)


def settlement_day(closes: Closes, expiry: date) -> Optional[date]:
    """The last trading day (with a close) on or before the expiry, within SETTLEMENT_SEARCH_DAYS."""
    for back in range(SETTLEMENT_SEARCH_DAYS + 1):
        day = expiry - timedelta(days=back)
        if day in closes:
            return day
    return None


def call_payoff(r: float) -> float:
    """An ATM call's payoff per unit of strike: the positive part of the return."""
    return max(r, 0.0)


def basket_call_payoff(weights: Mapping[str, float], start: Mapping[str, float], end: Mapping[str, float]) -> float:
    """sum_i w_i * max((P_i,T - P_i,t) / P_i,t, 0): each constituent's own call, weighted (not a call on the basket)."""
    return sum(w * call_payoff((end[s] - start[s]) / start[s]) for s, w in weights.items())


def months_before(d: date, months: int) -> date:
    year, month = divmod(d.year * 12 + d.month - 1 - months, 12)
    month += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError(d)


@dataclass(frozen=True)
class HoldingsSnapshot:
    """The ETF's holdings as of a date, as share counts per ETF share (from the value weights and that day's closes)."""
    as_of: date
    shares: Dict[str, float]          # constituent -> shares held per ETF share
    point_in_time: bool               # False: a later snapshot back-cast to an earlier date (membership not historical)


def shares_from_weights(weights: Mapping[str, float], etf_close: float,
                        closes: Mapping[str, float]) -> Dict[str, float]:
    """Value weights -> shares per ETF share at the snapshot date: n_i = w_i * S_ETF / S_i."""
    return {s: w * etf_close / closes[s] for s, w in weights.items()}


def weights_at(snapshot: HoldingsSnapshot, closes_at: Mapping[str, float]) -> Dict[str, float]:
    """The snapshot's share counts valued at another date's closes: w_i,t = n_i S_i,t / sum_j n_j S_j,t."""
    values = {s: n * closes_at[s] for s, n in snapshot.shares.items()}
    total = sum(values.values())
    return {s: v / total for s, v in values.items()}


@dataclass
class Observation:
    initiated: date
    expiry: Optional[date]
    settled: Optional[date] = None
    etf_strike: Optional[float] = None
    etf_settle: Optional[float] = None
    etf_payoff: Optional[float] = None
    basket_payoff: Optional[float] = None
    holdings_as_of: Optional[date] = None
    point_in_time: bool = False
    etf_return: Optional[float] = None             # (S_ETF,T - S_ETF,t) / S_ETF,t over the holding period
    basket_call_return: Optional[float] = None     # sum_i w_i,t * max(r_i, 0)
    problem: Optional[str] = None     # why the observation is incomplete (excluded); None = complete

    @property
    def complete(self) -> bool:
        return self.problem is None and self.basket_payoff is not None and self.etf_payoff is not None

    @property
    def dte(self) -> Optional[int]:
        return (self.expiry - self.initiated).days if self.expiry else None

    @property
    def dispersion_payoff(self) -> Optional[float]:
        return self.basket_payoff - self.etf_payoff if self.complete else None

    @property
    def normalized(self) -> Optional[float]:
        d = self.dispersion_payoff
        return None if d is None else d / (MULTIPLIER * self.etf_strike)

    @property
    def payoff_return(self) -> Optional[float]:
        d = self.dispersion_payoff
        return None if d is None or not self.etf_payoff else d / self.etf_payoff

    @property
    def etf_call_return(self) -> Optional[float]:
        """ETFCallPayoff_t = max(r_ETF, 0)."""
        return call_payoff(self.etf_return) if self.complete and self.etf_return is not None else None

    @property
    def replication_difference(self) -> Optional[float]:
        """BasketCallPayoff_t - ETFCallPayoff_t (positive: the constituent calls paid more)."""
        e = self.etf_call_return
        return None if e is None or self.basket_call_return is None else self.basket_call_return - e



def observe(initiated: date, etf_closes: Closes, constituent_closes: Mapping[str, Closes],
            snapshot: HoldingsSnapshot, config: DispersionScreenConfig, as_of: date) -> Observation:
    """One ATM-calls trade opened at `initiated` and held to its expiry. Uses no price after `as_of`: an expiry
    later than as_of leaves the observation open (problem 'not expired')."""
    expiry = expiry_for(initiated, config)
    obs = Observation(initiated, expiry, holdings_as_of=snapshot.as_of, point_in_time=snapshot.point_in_time)
    if expiry is None:
        obs.problem = "no monthly expiry within the DTE range"
        return obs
    if initiated not in etf_closes:
        obs.problem = f"no ETF close on {initiated}"
        return obs
    start = {}
    for symbol in snapshot.shares:
        close = constituent_closes.get(symbol, {}).get(initiated)
        if close is None:
            obs.problem = f"no {symbol} close on {initiated}"
            return obs
        start[symbol] = close
    if expiry > as_of:
        obs.problem = "not expired"
        return obs
    visible = {d: c for d, c in etf_closes.items() if d <= as_of}
    settled = settlement_day(visible, expiry)
    if settled is None:
        obs.problem = f"no ETF close at the {expiry} expiry"
        return obs
    end = {}
    for symbol in snapshot.shares:
        close = constituent_closes.get(symbol, {}).get(settled)
        if close is None:
            obs.problem = f"no {symbol} close on {settled} (expiry)"
            return obs
        end[symbol] = close
    weights = weights_at(snapshot, start)
    etf = Leg("ETF", etf_closes[initiated], etf_closes[initiated], MULTIPLIER, None, None)
    legs = [Leg(s, start[s], start[s], MULTIPLIER, None, None, weights[s]) for s in snapshot.shares]
    pay = Strategy.payoff_at_maturity(etf, legs, Strategy.replicate(etf, legs), etf_closes[settled], end)
    obs.settled, obs.etf_strike, obs.etf_settle = settled, etf_closes[initiated], etf_closes[settled]
    obs.etf_payoff, obs.basket_payoff = -pay.short_etf, pay.long_basket
    obs.etf_return = (etf_closes[settled] - etf_closes[initiated]) / etf_closes[initiated]
    obs.basket_call_return = basket_call_payoff(weights, start, end)
    return obs


@dataclass
class RollingStats:
    as_of: date
    window_start: date                # exclusive
    n: int                            # completed, complete observations in the window (included)
    n_open: int                       # initiated in the window, not expired by as_of (excluded)
    n_incomplete: int                 # missing data (excluded)
    mean: Optional[float] = None
    median: Optional[float] = None
    cumulative: Optional[float] = None
    positive_rate: Optional[float] = None
    normalized_mean: Optional[float] = None
    normalized_median: Optional[float] = None
    normalized_cumulative: Optional[float] = None
    normalized_positive_rate: Optional[float] = None
    return_mean: Optional[float] = None   # mean of DispersionPayoffReturn over the observations where it exists
    etf_call_mean: Optional[float] = None             # mean ETFCallPayoff
    basket_call_mean: Optional[float] = None          # mean BasketCallPayoff
    replication_mean: Optional[float] = None          # mean ReplicationDiff (the primary metric)
    replication_median: Optional[float] = None
    replication_cumulative: Optional[float] = None
    replication_positive_rate: Optional[float] = None     # the constituent calls paid more
    replication_negative_rate: Optional[float] = None     # the ETF call paid more
    problems: List[str] = field(default_factory=list)


def in_window(observations: Sequence[Observation], as_of: date, months: int = 6) -> List[Observation]:
    start = months_before(as_of, months)
    return [o for o in observations if start < o.initiated <= as_of]


def included(o: Observation, as_of: date) -> bool:
    return o.complete and o.settled is not None and o.settled <= as_of


def rolling_stats(observations: Sequence[Observation], as_of: date, months: int = 6) -> RollingStats:
    window = in_window(observations, as_of, months)
    done = [o for o in window if included(o, as_of)]
    open_ = [o for o in window if o.problem == "not expired" or (o.complete and o.settled and o.settled > as_of)]
    incomplete = [o for o in window if not o.complete and o.problem != "not expired"]
    stats = RollingStats(as_of, months_before(as_of, months), len(done), len(open_), len(incomplete))
    stats.problems = sorted({o.problem for o in incomplete})[:10]
    if not done:
        return stats
    diffs = [o.dispersion_payoff for o in done]
    norms = [o.normalized for o in done]
    returns = [o.payoff_return for o in done if o.payoff_return is not None]
    stats.mean, stats.median, stats.cumulative = statistics.fmean(diffs), statistics.median(diffs), sum(diffs)
    stats.positive_rate = sum(1 for d in diffs if d > 0) / len(diffs)
    stats.normalized_mean, stats.normalized_median = statistics.fmean(norms), statistics.median(norms)
    stats.normalized_cumulative = sum(norms)
    stats.normalized_positive_rate = sum(1 for d in norms if d > 0) / len(norms)
    stats.return_mean = statistics.fmean(returns) if returns else None
    calls = [o for o in done if o.replication_difference is not None]
    if not calls:
        return stats
    replication = [o.replication_difference for o in calls]
    stats.etf_call_mean = statistics.fmean(o.etf_call_return for o in calls)
    stats.basket_call_mean = statistics.fmean(o.basket_call_return for o in calls)
    stats.replication_mean, stats.replication_median = statistics.fmean(replication), statistics.median(replication)
    stats.replication_cumulative = sum(replication)
    stats.replication_positive_rate = sum(1 for d in replication if d > 0) / len(replication)
    stats.replication_negative_rate = sum(1 for d in replication if d < 0) / len(replication)
    return stats


def cumulative_series(observations: Sequence[Observation], as_of: date,
                      months: int = 6) -> List[Tuple[date, float, float]]:
    """(settlement day, cumulative DispersionPayoff, cumulative normalized) of the included observations, in the
    order they settled: the chart of the latest 6 months."""
    done = sorted((o for o in in_window(observations, as_of, months) if included(o, as_of)),
                  key=lambda o: (o.settled, o.initiated))
    out, total, total_norm = [], 0.0, 0.0
    for o in done:
        total += o.dispersion_payoff
        total_norm += o.normalized
        out.append((o.settled, total, total_norm))
    return out


def replication_series(observations: Sequence[Observation], as_of: date,
                       months: int = 6) -> List[Tuple[date, float, float, float]]:
    """(observation date, ETFCallPayoff, BasketCallPayoff, ReplicationDiff) of the included observations: the chart
    of the latest 6 months."""
    return sorted((o.initiated, o.etf_call_return, o.basket_call_return, o.replication_difference)
                  for o in in_window(observations, as_of, months)
                  if included(o, as_of) and o.replication_difference is not None)


# --- fixed holding periods: consecutive, non-overlapping periods of `step` months covering the window ---------------

PERIOD_STEPS = (1, 2, 3)                       # months per holding period: 6, 3 and 2 periods over 6 months


def period_bounds(as_of: date, step: int, window_months: int = 6) -> List[Tuple[date, date]]:
    """[(start, end)] oldest first: the last period ends at as_of, each one `step` calendar months long."""
    ends = [months_before(as_of, k * step) for k in range(window_months // step)]
    return sorted((months_before(e, step), e) for e in ends)


@dataclass
class Period:
    start: date                       # period boundary (calendar)
    end: date
    start_day: Optional[date] = None  # the trading day whose close opens the trade (last close on or before start)
    end_day: Optional[date] = None    # the trading day whose close settles it
    etf_return: Optional[float] = None
    basket_call_return: Optional[float] = None     # sum_i w_i,start * max(r_i, 0)
    holdings_as_of: Optional[date] = None
    point_in_time: bool = False
    problem: Optional[str] = None

    @property
    def etf_call_return(self) -> Optional[float]:
        return None if self.problem or self.etf_return is None else call_payoff(self.etf_return)

    @property
    def replication_difference(self) -> Optional[float]:
        e = self.etf_call_return
        return None if e is None or self.basket_call_return is None else self.basket_call_return - e


def observe_period(start: date, end: date, etf_closes: Closes, constituent_closes: Mapping[str, Closes],
                   snapshot: HoldingsSnapshot) -> Period:
    """ATM ETF call vs ATM constituent calls opened at the start close and settled at the end close (no price after
    `end`: callers pass end <= as_of). A missing close leaves the period incomplete, never zero."""
    p = Period(start, end, holdings_as_of=snapshot.as_of, point_in_time=snapshot.point_in_time)
    p.start_day, p.end_day = settlement_day(etf_closes, start), settlement_day(etf_closes, end)
    if p.start_day is None or p.end_day is None or p.start_day >= p.end_day:
        p.problem = f"no ETF close at {start if p.start_day is None else end}"
        return p
    first, last = {}, {}
    for symbol in snapshot.shares:
        a = constituent_closes.get(symbol, {}).get(p.start_day)
        b = constituent_closes.get(symbol, {}).get(p.end_day)
        if a is None or b is None:
            p.problem = f"no {symbol} close on {p.start_day if a is None else p.end_day}"
            return p
        first[symbol], last[symbol] = a, b
    p.etf_return = (etf_closes[p.end_day] - etf_closes[p.start_day]) / etf_closes[p.start_day]
    p.basket_call_return = basket_call_payoff(weights_at(snapshot, first), first, last)
    return p


@dataclass
class PeriodStats:
    step: int
    n: int                            # complete periods
    n_incomplete: int
    etf_call_mean: Optional[float] = None
    basket_call_mean: Optional[float] = None
    mean: Optional[float] = None      # mean replication difference
    cumulative: Optional[float] = None
    positive_rate: Optional[float] = None


def period_stats(step: int, periods: Sequence[Period]) -> PeriodStats:
    done = [p for p in periods if p.replication_difference is not None]
    s = PeriodStats(step, len(done), len(periods) - len(done))
    if done:
        diffs = [p.replication_difference for p in done]
        s.etf_call_mean = statistics.fmean(p.etf_call_return for p in done)
        s.basket_call_mean = statistics.fmean(p.basket_call_return for p in done)
        s.mean, s.cumulative = statistics.fmean(diffs), sum(diffs)
        s.positive_rate = sum(1 for d in diffs if d > 0) / len(diffs)
    return s
