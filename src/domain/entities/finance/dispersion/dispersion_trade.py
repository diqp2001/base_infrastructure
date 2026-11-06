"""
P.05 – P.06 of the dispersion screen (pure): dollar-delta-neutral sizing of the long constituent calls against the
short ETF call, the premium comparison on executable prices, diagnostics, and the payoff at maturity.

Units. Weights are value weights: one ETF share holds w_i * S_etf / S_i shares of constituent i. Per short ETF call
contract (m_etf ETF shares) the raw constituent position is m_etf * w_i * S_etf / S_i shares, i.e. that / m_i
contracts. Neutrality is on DOLLAR delta (contracts * multiplier * delta * underlying price): every leg's delta is
the option's own (IBKR model) delta, never an assumed 0.5.

Sizing. Fractional sizing scales the raw positions so the long dollar delta equals the short one exactly (the
economic reference). Listed options trade in whole contracts, so the executable sizing tries N = 1 ..
max_etf_contracts short ETF calls, rounds every constituent to whole contracts and keeps the first N whose
|net dollar delta| / short dollar delta <= delta_tolerance (and, by default, every constituent >= 1 contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig


@dataclass(frozen=True)
class Leg:
    """One option leg's market inputs: an ATM call on the ETF or on a constituent."""
    symbol: str
    spot: float                      # underlying price
    strike: float
    multiplier: float
    delta: float                     # option delta (per share)
    bid: float
    ask: float
    weight: float = 1.0              # constituent weight in the ETF (normalised); 1 for the ETF leg
    implied_vol: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    def dollar_delta(self, contracts: float) -> float:
        return contracts * self.multiplier * self.delta * self.spot


@dataclass
class Sizing:
    etf_contracts: float
    positions: Dict[str, float]                  # constituent -> contracts (long)
    short_dollar_delta: float                    # positive number: the short ETF call's |dollar delta|
    long_dollar_delta: float
    net_dollar_delta: float                      # long - short
    whole_contracts: bool
    zero_positions: List[str] = field(default_factory=list)

    @property
    def relative_net_delta(self) -> float:
        return self.net_dollar_delta / self.short_dollar_delta if self.short_dollar_delta else float("inf")


def raw_positions(etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Dict[str, float]:
    """Contracts of each constituent that replicate etf_contracts ETF calls' share count by the ETF weights."""
    shares_per_contract = etf.multiplier * etf_contracts
    return {c.symbol: shares_per_contract * c.weight * etf.spot / c.spot / c.multiplier for c in constituents}


def size_fractional(etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Sizing:
    raw = raw_positions(etf, constituents, etf_contracts)
    by_symbol = {c.symbol: c for c in constituents}
    short = abs(etf.dollar_delta(etf_contracts))
    basket = sum(by_symbol[s].dollar_delta(q) for s, q in raw.items())
    if basket <= 0:
        raise ValueError("the constituent calls have no positive dollar delta")
    ratio = short / basket
    positions = {s: q * ratio for s, q in raw.items()}
    long = sum(by_symbol[s].dollar_delta(q) for s, q in positions.items())
    return Sizing(etf_contracts, positions, short, long, long - short, whole_contracts=False)


def size_whole_contracts(etf: Leg, constituents: Sequence[Leg], config: DispersionScreenConfig) -> Sizing:
    """First N (1 .. max_etf_contracts) whose rounded basket is delta neutral within tolerance; else the N with the
    smallest relative net delta (the caller sees it is outside the tolerance)."""
    by_symbol = {c.symbol: c for c in constituents}

    def rank(z: Sizing):
        return (not (z.zero_positions and config.require_every_constituent), -abs(z.relative_net_delta))

    best: Optional[Sizing] = None
    for n in range(1, config.max_etf_contracts + 1):
        exact = size_fractional(etf, constituents, n)
        positions = {s: float(round(q)) for s, q in exact.positions.items()}
        zeros = [s for s, q in positions.items() if q < 1]
        long = sum(by_symbol[s].dollar_delta(q) for s, q in positions.items())
        sizing = Sizing(n, positions, exact.short_dollar_delta, long, long - exact.short_dollar_delta,
                        whole_contracts=True, zero_positions=zeros)
        usable = not (zeros and config.require_every_constituent)
        if usable and abs(sizing.relative_net_delta) <= config.delta_tolerance:
            return sizing
        if best is None or rank(sizing) > rank(best):
            best = sizing
    return best


@dataclass
class Premium:
    short_proceeds: float            # ETF calls sold at the bid
    long_cost: float                 # constituent calls bought at the ask
    net_premium: float               # proceeds - cost
    net_premium_pct: float           # net / proceeds
    mid_net_premium: float           # same at mids (diagnostic)
    transaction_cost: float          # half-spread paid on every leg vs mids


def premium(etf: Leg, constituents: Sequence[Leg], sizing: Sizing) -> Premium:
    by_symbol = {c.symbol: c for c in constituents}
    proceeds = sizing.etf_contracts * etf.multiplier * etf.bid
    cost = sum(q * by_symbol[s].multiplier * by_symbol[s].ask for s, q in sizing.positions.items())
    mid_proceeds = sizing.etf_contracts * etf.multiplier * etf.mid
    mid_cost = sum(q * by_symbol[s].multiplier * by_symbol[s].mid for s, q in sizing.positions.items())
    net = proceeds - cost
    return Premium(proceeds, cost, net, net / proceeds if proceeds else float("-inf"), mid_proceeds - mid_cost,
                   (mid_proceeds - proceeds) + (cost - mid_cost))


@dataclass
class WeightedComparison:
    """Section 9 diagnostic (not a trade test): the ETF call vs the ETF-weighted constituent calls, per ETF share."""
    etf_call_value: float
    weighted_constituent_call_value: float
    dispersion_premium: float        # etf - weighted
    relative_premium: float          # etf / weighted - 1


def weighted_comparison(etf: Leg, constituents: Sequence[Leg]) -> WeightedComparison:
    weighted = sum(c.weight * etf.spot / c.spot * c.mid for c in constituents)
    return WeightedComparison(etf.mid, weighted, etf.mid - weighted,
                              etf.mid / weighted - 1.0 if weighted else float("inf"))


def implied_correlation(etf_vol: Optional[float], constituents: Sequence[Leg]) -> Optional[float]:
    """Weighted average implied correlation from
        sigma_etf^2 = sum w_i^2 sigma_i^2 + rho * sum_{i != j} w_i w_j sigma_i sigma_j
    (one rho for every pair: an average, not a constant-correlation assumption about the pairs)."""
    vols = [(c.weight, c.implied_vol) for c in constituents if c.implied_vol]
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
