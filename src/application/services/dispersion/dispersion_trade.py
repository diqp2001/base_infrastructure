"""
P.05 – P.06 of the dispersion screen (pure): the long constituent calls that replicate the ETF's holdings under
one short ETF call, the strategy's cost on the broker's prices, diagnostics, and the payoff at maturity.

Sizing (owner, 2026-11-06): the long calls copy the ETF's holdings. One short ETF call covers m_etf ETF shares; one
ETF share holds w_i * S_etf / S_i shares of constituent i (value weights), so the call on those shares is
    contracts_i = m_etf * w_i * S_etf / S_i / m_i       (per short ETF call; a fraction of a contract)
e.g. an ETF holding 5 shares of A and 5 of B per share: 5 A calls and 5 B calls per ETF call (100 shares each).

Cost (owner, 2026-11-06): the broker's prices as quoted - the ETF call sold at its bid, every constituent call
bought at its ask - summed with those contract counts; the strategy is an opportunity when the net premium
(ETF proceeds - constituent cost) is >= 0. Dollar delta, greeks and mids are information only.

Information (owner, 2026-11-06): the reversed strategy (ETF call bought at its ask, constituent calls sold at their
bids) and the implied correlation on each side's prices - from the broker's volatility implied by the ETF call bid
and the constituent asks (this strategy), and by the ETF call ask and the constituent bids (reversed).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class Leg:
    """One option leg's market inputs: an ATM call on the ETF or on a constituent."""
    symbol: str
    spot: float                      # underlying price
    strike: float
    multiplier: float
    bid: Optional[float]             # the ETF leg needs its bid (sold), a constituent leg its ask (bought)
    ask: Optional[float]
    weight: float = 1.0              # constituent weight in the ETF (normalised); 1 for the ETF leg
    delta: Optional[float] = None    # IBKR model greeks (information)
    implied_vol: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    bid_implied_vol: Optional[float] = None    # the broker's volatility implied by the bid / the ask price
    ask_implied_vol: Optional[float] = None

    @property
    def mid(self) -> Optional[float]:
        if self.bid is None or self.ask is None or self.bid <= 0 or self.ask <= 0:
            return None
        return (self.bid + self.ask) / 2.0

    def dollar_delta(self, contracts: float) -> Optional[float]:
        return None if self.delta is None else contracts * self.multiplier * self.delta * self.spot


@dataclass
class Sizing:
    etf_contracts: float
    positions: Dict[str, float]                  # constituent -> call contracts (long), replicating the holdings
    short_dollar_delta: Optional[float]          # positive number: the short ETF calls' |dollar delta|
    long_dollar_delta: Optional[float]

    @property
    def net_dollar_delta(self) -> Optional[float]:
        if self.short_dollar_delta is None or self.long_dollar_delta is None:
            return None
        return self.long_dollar_delta - self.short_dollar_delta

    @property
    def relative_net_delta(self) -> Optional[float]:
        net = self.net_dollar_delta
        return None if net is None or not self.short_dollar_delta else net / self.short_dollar_delta

    @property
    def whole_contract_etf_calls(self) -> Optional[int]:
        """ETF calls needed for the smallest constituent position to reach one whole contract (information)."""
        smallest = min((q for q in self.positions.values() if q > 0), default=None)
        if smallest is None:
            return None
        return math.ceil(self.etf_contracts / smallest - 1e-9)


def raw_positions(etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Dict[str, float]:
    """Contracts of each constituent that replicate etf_contracts ETF calls' share count by the ETF weights."""
    shares_per_contract = etf.multiplier * etf_contracts
    return {c.symbol: shares_per_contract * c.weight * etf.spot / c.spot / c.multiplier for c in constituents}


def replicate(etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Sizing:
    positions = raw_positions(etf, constituents, etf_contracts)
    by_symbol = {c.symbol: c for c in constituents}
    short = etf.dollar_delta(etf_contracts)
    longs = [by_symbol[s].dollar_delta(q) for s, q in positions.items()]
    long = None if any(x is None for x in longs) else sum(longs)
    return Sizing(etf_contracts, positions, abs(short) if short is not None else None, long)


@dataclass
class Premium:
    short_proceeds: float            # ETF calls sold at the bid
    long_cost: float                 # constituent calls bought at the ask
    net_premium: float               # proceeds - cost: >= 0 is an opportunity
    net_premium_pct: float           # net / proceeds
    mid_net_premium: Optional[float]      # the same at mids, when every leg has both sides (information)
    transaction_cost: Optional[float]     # what the bid / ask costs against mids (information)


def premium(etf: Leg, constituents: Sequence[Leg], sizing: Sizing) -> Premium:
    by_symbol = {c.symbol: c for c in constituents}
    proceeds = sizing.etf_contracts * etf.multiplier * etf.bid
    cost = sum(q * by_symbol[s].multiplier * by_symbol[s].ask for s, q in sizing.positions.items())
    net = proceeds - cost
    mids = [etf.mid] + [by_symbol[s].mid for s in sizing.positions]
    if any(m is None for m in mids):
        mid_net = transaction = None
    else:
        mid_proceeds = sizing.etf_contracts * etf.multiplier * etf.mid
        mid_cost = sum(q * by_symbol[s].multiplier * by_symbol[s].mid for s, q in sizing.positions.items())
        mid_net, transaction = mid_proceeds - mid_cost, (mid_proceeds - proceeds) + (cost - mid_cost)
    return Premium(proceeds, cost, net, net / proceeds if proceeds else float("-inf"), mid_net, transaction)


@dataclass
class ReversePremium:
    """The strategy reversed: the ETF calls bought at the ask, the constituent calls sold at the bid (information)."""
    etf_call_cost: float
    constituent_proceeds: float
    net_premium: float               # proceeds - cost
    net_premium_pct: float           # net / ETF call cost


def reverse_premium(etf: Leg, constituents: Sequence[Leg], sizing: Sizing) -> Optional[ReversePremium]:
    """None when the ETF call has no ask or a constituent call no bid."""
    by_symbol = {c.symbol: c for c in constituents}
    if not etf.ask or etf.ask <= 0 or any(not by_symbol[s].bid or by_symbol[s].bid <= 0 for s in sizing.positions):
        return None
    cost = sizing.etf_contracts * etf.multiplier * etf.ask
    proceeds = sum(q * by_symbol[s].multiplier * by_symbol[s].bid for s, q in sizing.positions.items())
    return ReversePremium(cost, proceeds, proceeds - cost, (proceeds - cost) / cost)


def implied_correlation(etf_vol: Optional[float], constituents: Sequence[Leg],
                        vol: str = "implied_vol") -> Optional[float]:
    """Weighted average implied correlation from
        sigma_etf^2 = sum w_i^2 sigma_i^2 + rho * sum_{i != j} w_i w_j sigma_i sigma_j
    (one rho for every pair: an average, not a constant-correlation assumption about the pairs). vol: the
    constituents' volatility used - the model's ('implied_vol'), or the one implied by their bid / ask price."""
    vols = [(c.weight, getattr(c, vol)) for c in constituents if getattr(c, vol)]
    if not etf_vol or len(vols) < 2 or len(vols) != len(constituents):
        return None
    own = sum((w * s) ** 2 for w, s in vols)
    cross = sum(w * s for w, s in vols) ** 2 - own
    return (etf_vol ** 2 - own) / cross if cross > 0 else None


def weighted_implied_vol(constituents: Sequence[Leg]) -> Optional[float]:
    if any(c.implied_vol is None for c in constituents):
        return None
    return sum(c.weight * c.implied_vol for c in constituents)


@dataclass
class Payoff:
    long_basket: float
    short_etf: float                 # negative: what the short ETF call pays
    combined: float
    pnl: float                       # combined + net premium


def payoff_at_maturity(etf: Leg, constituents: Sequence[Leg], sizing: Sizing, etf_price: float,
                       prices: Dict[str, float], net_premium: float = 0.0) -> Payoff:
    """European payoffs at expiry (American early exercise and dividends are ignored: research only)."""
    by_symbol = {c.symbol: c for c in constituents}
    long = sum(q * by_symbol[s].multiplier * max(prices[s] - by_symbol[s].strike, 0.0)
               for s, q in sizing.positions.items())
    short = -sizing.etf_contracts * etf.multiplier * max(etf_price - etf.strike, 0.0)
    return Payoff(long, short, long + short, long + short + net_premium)


def etf_price_from(etf: Leg, constituents: Sequence[Leg], prices: Dict[str, float]) -> float:
    """The ETF price implied by constituent prices with the ETF's value weights (no tracking error)."""
    return etf.spot * sum(c.weight * prices[c.symbol] / c.spot for c in constituents)


SCENARIO_MOVES = (-0.10, -0.05, 0.0, 0.05, 0.10)


def scenarios(etf: Leg, constituents: Sequence[Leg], sizing: Sizing, net_premium: float,
              moves: Sequence[float] = SCENARIO_MOVES, dispersion: float = 0.10) -> List[Dict[str, float]]:
    """Payoff at maturity in transparent scenarios (section 18):
       - 'market m': every constituent moves by m (no dispersion: the long calls roughly offset the short call);
       - 'dispersion m': the same average move m, the heavier half of the ETF weight +dispersion and the rest
         -dispersion around it (the long calls gain from the spread, the ETF call sees the average only).
    The ETF price follows the constituents with the ETF weights."""
    ordered = sorted(constituents, key=lambda c: -c.weight)
    half, acc = set(), 0.0
    for c in ordered:
        if acc >= 0.5:
            break
        half.add(c.symbol)
        acc += c.weight
    up_w = sum(c.weight for c in constituents if c.symbol in half)
    down_w = 1.0 - up_w
    out = []
    for m in moves:
        for kind in ("market", "dispersion"):
            if kind == "market":
                prices = {c.symbol: c.spot * (1 + m) for c in constituents}
            else:
                # +d on the up half, -d * up_w / down_w on the rest: the weighted average move stays m
                down = dispersion * up_w / down_w if down_w > 0 else 0.0
                prices = {c.symbol: c.spot * (1 + m + (dispersion if c.symbol in half else -down))
                          for c in constituents}
            etf_price = etf_price_from(etf, constituents, prices)
            p = payoff_at_maturity(etf, constituents, sizing, etf_price, prices, net_premium)
            out.append({"scenario": f"{kind} {m:+.0%}", "etf_price": etf_price, "long_basket": p.long_basket,
                        "short_etf": p.short_etf, "combined": p.combined, "pnl": p.pnl})
    return out
