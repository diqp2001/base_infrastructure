"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/etf_share_option/etf_share_option_factor.py

ETFShareOptionFactor - factor of an option on an ETF share. Its stored rows are the option's raw quote series (group
'price', subgroup 'quote', one series per QUOTE_FIELDS name: the broker's bid / ask, its volatilities and greeks, the
underlying's price at the quote and the contract terms), stored at the screen's quote time. The same series on the
constituents' options are CompanyShareOptionFactor rows with the same names.

It is also the parent of the ETF option dispersion strategy factors (etf_share_option_dispersion_factor.py) and holds
the strategy maths they share (owner, 2026-11-06):

Sizing: the constituent options copy the ETF's holdings. One ETF option covers m_etf ETF shares; one ETF share holds
w_i * S_etf / S_i shares of constituent i (value weights), so the option on those shares is
    contracts_i = m_etf * w_i * S_etf / S_i / m_i       (per ETF option; a fraction of a contract)
Strategy: the ETF option sold at its bid, every constituent option bought at its ask; net premium = ETF proceeds -
constituent cost (>= 0: an opportunity). Reversed (information): the ETF option bought at its ask, the constituent
options sold at their bids. Implied correlation from sigma_etf^2 = sum w_i^2 sigma_i^2 + rho sum_{i!=j} w_i w_j sigma_i
sigma_j. Payoff at maturity: European, calls max(S - K, 0), puts max(K - S, 0) (research only).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

from src.domain.entities.factor.finance.financial_assets.derivatives.option.share_option_factor import ShareOptionFactor

QUOTE_SUBGROUP = "quote"
QUOTE_FIELDS = ("bid", "ask", "iv", "bid_iv", "ask_iv", "delta", "gamma", "vega", "theta", "underlying_price",
                "strike", "multiplier")
CALL, PUT = "C", "P"
SCENARIO_MOVES = (-0.10, -0.05, 0.0, 0.05, 0.10)
SCENARIO_DISPERSION = 0.10


def right_of(option_type) -> Optional[str]:
    """'C' / 'P' from an option entity's option_type ('call' / 'put' / 'C' / 'P', any case); None otherwise."""
    return {"call": CALL, "c": CALL, "put": PUT, "p": PUT}.get(str(option_type or "").strip().lower())


@dataclass(frozen=True)
class Leg:
    """One option leg's market inputs: the ATM option on the ETF or on a constituent."""
    symbol: str
    spot: float                      # underlying price
    strike: float
    multiplier: float
    bid: Optional[float]             # the ETF leg needs its bid (sold), a constituent leg its ask (bought)
    ask: Optional[float]
    weight: float = 1.0              # constituent weight in the ETF (normalised); 1 for the ETF leg
    delta: Optional[float] = None    # broker model greeks (information)
    implied_vol: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    bid_implied_vol: Optional[float] = None    # the broker's volatility implied by the bid / the ask price
    ask_implied_vol: Optional[float] = None
    right: str = CALL

    @property
    def mid(self) -> Optional[float]:
        if self.bid is None or self.ask is None or self.bid <= 0 or self.ask <= 0:
            return None
        return (self.bid + self.ask) / 2.0

    def intrinsic(self, price: float) -> float:
        return max(price - self.strike, 0.0) if self.right == CALL else max(self.strike - price, 0.0)

    def dollar_delta(self, contracts: float) -> Optional[float]:
        return None if self.delta is None else contracts * self.multiplier * self.delta * self.spot


@dataclass
class Sizing:
    etf_contracts: float
    positions: Dict[str, float]                  # constituent -> option contracts (long), replicating the holdings
    short_dollar_delta: Optional[float]          # positive number: the short ETF options' |dollar delta|
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
        """ETF options needed for the smallest constituent position to reach one whole contract (information)."""
        smallest = min((q for q in self.positions.values() if q > 0), default=None)
        if smallest is None:
            return None
        return math.ceil(self.etf_contracts / smallest - 1e-9)


@dataclass
class Premium:
    short_proceeds: float            # ETF options sold at the bid
    long_cost: float                 # constituent options bought at the ask
    net_premium: float               # proceeds - cost: >= 0 is an opportunity
    net_premium_pct: float           # net / proceeds
    mid_net_premium: Optional[float]      # the same at mids, when every leg has both sides (information)
    transaction_cost: Optional[float]     # what the bid / ask costs against mids (information)


@dataclass
class ReversePremium:
    """The strategy reversed: the ETF options bought at the ask, the constituent options sold at the bid."""
    etf_call_cost: float
    constituent_proceeds: float
    net_premium: float               # proceeds - cost
    net_premium_pct: float           # net / ETF option cost


@dataclass
class Payoff:
    long_basket: float
    short_etf: float                 # negative: what the short ETF options pay
    combined: float
    pnl: float                       # combined + net premium


class ETFShareOptionFactor(ShareOptionFactor):
    """Factor of an option on an ETF share: the raw quote series, and the dispersion strategy maths (see the module
    docstring)."""

    def __init__(self, name: str, group: str = "price", subgroup: Optional[str] = QUOTE_SUBGROUP,
                 frequency: Optional[str] = "1d", data_type: Optional[str] = "numeric", source: Optional[str] = "ibkr",
                 definition: Optional[str] = None, factor_id: Optional[int] = None, **kwargs):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, definition=definition, factor_id=factor_id)

    # ---- legs from quote series ----
    @staticmethod
    def leg(symbol: str, quote: Mapping[str, Optional[float]], weight: float = 1.0, right: str = CALL) -> Optional[Leg]:
        """A leg from one option's quote fields; None without its underlying price, strike or multiplier."""
        spot, strike, multiplier = quote.get("underlying_price"), quote.get("strike"), quote.get("multiplier")
        if not spot or spot <= 0 or strike is None or not multiplier:
            return None
        return Leg(symbol, spot, strike, multiplier, quote.get("bid"), quote.get("ask"), weight, quote.get("delta"),
                   quote.get("iv"), quote.get("gamma"), quote.get("vega"), quote.get("theta"), quote.get("bid_iv"),
                   quote.get("ask_iv"), right)

    # ---- sizing ----
    @staticmethod
    def raw_positions(etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Dict[str, float]:
        """Contracts of each constituent that replicate etf_contracts ETF options' share count by the ETF weights."""
        shares_per_contract = etf.multiplier * etf_contracts
        return {c.symbol: shares_per_contract * c.weight * etf.spot / c.spot / c.multiplier for c in constituents}

    @classmethod
    def replicate(cls, etf: Leg, constituents: Sequence[Leg], etf_contracts: float = 1.0) -> Sizing:
        positions = cls.raw_positions(etf, constituents, etf_contracts)
        by_symbol = {c.symbol: c for c in constituents}
        short = etf.dollar_delta(etf_contracts)
        longs = [by_symbol[s].dollar_delta(q) for s, q in positions.items()]
        long = None if any(x is None for x in longs) else sum(longs)
        return Sizing(etf_contracts, positions, abs(short) if short is not None else None, long)

    # ---- premiums ----
    @staticmethod
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

    @staticmethod
    def reverse_premium(etf: Leg, constituents: Sequence[Leg], sizing: Sizing) -> Optional[ReversePremium]:
        """None when the ETF option has no ask or a constituent option no bid."""
        by_symbol = {c.symbol: c for c in constituents}
        if not etf.ask or etf.ask <= 0 or any(not by_symbol[s].bid or by_symbol[s].bid <= 0 for s in sizing.positions):
            return None
        cost = sizing.etf_contracts * etf.multiplier * etf.ask
        proceeds = sum(q * by_symbol[s].multiplier * by_symbol[s].bid for s, q in sizing.positions.items())
        return ReversePremium(cost, proceeds, proceeds - cost, (proceeds - cost) / cost)

    # ---- volatilities ----
    @staticmethod
    def implied_correlation(etf_vol: Optional[float], constituents: Sequence[Leg],
                            vol: str = "implied_vol") -> Optional[float]:
        """Weighted average implied correlation (one rho for every pair: an average, not a constant-correlation
        assumption about the pairs). vol: the constituents' volatility used - the model's ('implied_vol'), or the one
        implied by their bid / ask price."""
        vols = [(c.weight, getattr(c, vol)) for c in constituents if getattr(c, vol)]
        if not etf_vol or len(vols) < 2 or len(vols) != len(constituents):
            return None
        own = sum((w * s) ** 2 for w, s in vols)
        cross = sum(w * s for w, s in vols) ** 2 - own
        return (etf_vol ** 2 - own) / cross if cross > 0 else None

    @staticmethod
    def weighted_implied_vol(constituents: Sequence[Leg]) -> Optional[float]:
        if any(c.implied_vol is None for c in constituents):
            return None
        return sum(c.weight * c.implied_vol for c in constituents)

    # ---- payoff at maturity ----
    @staticmethod
    def payoff_at_maturity(etf: Leg, constituents: Sequence[Leg], sizing: Sizing, etf_price: float,
                           prices: Dict[str, float], net_premium: float = 0.0) -> Payoff:
        """European payoffs at expiry (American early exercise and dividends are ignored: research only)."""
        by_symbol = {c.symbol: c for c in constituents}
        long = sum(q * by_symbol[s].multiplier * by_symbol[s].intrinsic(prices[s]) for s, q in sizing.positions.items())
        short = -sizing.etf_contracts * etf.multiplier * etf.intrinsic(etf_price)
        return Payoff(long, short, long + short, long + short + net_premium)

    @staticmethod
    def etf_price_from(etf: Leg, constituents: Sequence[Leg], prices: Dict[str, float]) -> float:
        """The ETF price implied by constituent prices with the ETF's value weights (no tracking error)."""
        return etf.spot * sum(c.weight * prices[c.symbol] / c.spot for c in constituents)

    @staticmethod
    def scenario_name(kind: str, move: float) -> str:
        """'market' / 'dispersion' and a move: market_down10, dispersion_flat, market_up5, ..."""
        pct = round(move * 100)
        return f"{kind}_{'flat' if pct == 0 else ('up' if pct > 0 else 'down') + str(abs(pct))}"

    @classmethod
    def scenarios(cls, etf: Leg, constituents: Sequence[Leg], sizing: Sizing, net_premium: float,
                  moves: Sequence[float] = SCENARIO_MOVES, dispersion: float = SCENARIO_DISPERSION) -> List[Dict[str, float]]:
        """Payoff at maturity in transparent scenarios (section 18):
           - 'market m': every constituent moves by m (no dispersion: the long options roughly offset the short one);
           - 'dispersion m': the same average move m, the heavier half of the ETF weight +dispersion and the rest
             -dispersion around it (the long options gain from the spread, the ETF option sees the average only).
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
                etf_price = cls.etf_price_from(etf, constituents, prices)
                p = cls.payoff_at_maturity(etf, constituents, sizing, etf_price, prices, net_premium)
                out.append({"scenario": f"{kind} {m:+.0%}", "key": cls.scenario_name(kind, m), "etf_price": etf_price,
                            "long_basket": p.long_basket, "short_etf": p.short_etf, "combined": p.combined,
                            "pnl": p.pnl})
        return out
