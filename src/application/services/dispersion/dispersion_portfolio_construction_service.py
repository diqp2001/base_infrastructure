"""
DispersionPortfolioConstructionService - builds the original and the model-filtered dispersion trades from the SAME
short ETF leg.

Order (the research question depends on it):
  1. full basket: every constituent's ATM call, sized by the screener's rule ETFShareOptionFactor.replicate - the
     constituent calls replicate the ETF calls' share exposure with the ETF's weights (an ETF holding w of name i
     -> calls on w of the exposure in i);
  2. N short ETF calls = the smallest whole number of ETF calls at which every constituent leg is at least one
     contract (Sizing.whole_contract_etf_calls of one ETF call: the most efficient whole-contract replication).
     N is FIXED here, from the full basket;
  3. only then the model selection removes constituents: the selected legs keep their full-basket quantities, N does
     not change, and the premium not spent is reported (never redeployed: strategy C is left open).

Cash premium of a leg = price x multiplier x contracts. ETF calls are sold at the bid, constituent calls bought at
the ask (the screener's convention; modelled legs have bid = ask).
  P_short     = N x mult x ETF bid
  P_full      = sum over ALL constituents of q_i x mult_i x ask_i       (strategy A's cost)
  P_selected  = the same over the selected constituents                (strategy B's cost)
  unused premium = net initial premium (B) = P_short - P_selected; net initial premium (A) = P_short - P_full
Payoff at expiry (ETFShareOptionFactor.payoff_at_maturity):
  short = -N x mult x max(S_T - K, 0); long = sum q_i x mult_i x max(S_i,T - K_i, 0); P&L = short + long + net premium
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Mapping, Sequence

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor,
    Leg,
    Payoff,
    Sizing,
)
from src.application.services.dispersion.model_selection import Selection

FRACTIONAL = "fractional"          # the screener's positions as computed
WHOLE = "whole"                    # nearest whole contract, at least one


@dataclass
class StrategyLegs:
    """One strategy's position: N short ETF calls and long constituent calls."""
    name: str
    etf_contracts: int
    positions: Dict[str, float]
    short_premium: float
    long_premium: float

    @property
    def net_initial_premium(self) -> float:
        return self.short_premium - self.long_premium


@dataclass
class ConstructedTrade:
    opened: date
    expiry: date
    etf: Leg
    constituents: List[Leg]                    # every constituent's ATM call (the full basket)
    etf_contracts: int                         # N, from the full basket
    original: StrategyLegs                     # A
    filtered: StrategyLegs                     # B
    selection: Selection
    raw_positions: Dict[str, float] = field(default_factory=dict)   # full-basket positions before rounding

    @property
    def short_premium(self) -> float:
        return self.original.short_premium

    @property
    def full_basket_premium(self) -> float:
        return self.original.long_premium

    @property
    def selected_basket_premium(self) -> float:
        return self.filtered.long_premium

    @property
    def unused_premium(self) -> float:
        return self.short_premium - self.selected_basket_premium

    @property
    def net_initial_premium(self) -> float:
        return self.filtered.net_initial_premium


@dataclass
class SettledStrategy:
    name: str
    payoff: Payoff                              # long_basket, short_etf, combined, pnl (incl. net premium)
    net_initial_premium: float

    @property
    def pnl(self) -> float:
        return self.payoff.pnl


class DispersionPortfolioConstructionService:

    def __init__(self, contracts: str = WHOLE):
        if contracts not in (FRACTIONAL, WHOLE):
            raise ValueError(f"contracts must be {FRACTIONAL!r} or {WHOLE!r}")
        self.contracts = contracts

    # -- step 1-2: the full basket fixes N --
    @staticmethod
    def baseline_short_contracts(etf: Leg, constituents: Sequence[Leg]) -> int:
        """N: the fewest ETF calls at which every constituent leg of the replication is >= 1 contract."""
        n = ETFShareOptionFactor.replicate(etf, constituents, 1.0).whole_contract_etf_calls
        if n is None:
            raise ValueError("no constituent position: the ETF call cannot be replicated")
        return max(1, int(n))

    def _positions(self, raw: Mapping[str, float]) -> Dict[str, float]:
        if self.contracts == FRACTIONAL:
            return dict(raw)
        return {s: float(max(1, int(math.floor(q + 0.5)))) for s, q in raw.items()}

    @staticmethod
    def _long_premium(constituents: Sequence[Leg], positions: Mapping[str, float]) -> float:
        by_symbol = {c.symbol: c for c in constituents}
        return sum(q * by_symbol[s].multiplier * by_symbol[s].ask for s, q in positions.items())

    # -- step 3: model selection on the long basket only --
    def construct(self, opened: date, expiry: date, etf: Leg, constituents: Sequence[Leg],
                  selection: Selection) -> ConstructedTrade:
        if etf.bid is None or etf.bid <= 0:
            raise ValueError(f"{etf.symbol}: the short ETF call has no bid")
        if any(c.ask is None or c.ask <= 0 for c in constituents):
            raise ValueError("every constituent call of the full basket needs an ask")
        n = self.baseline_short_contracts(etf, constituents)                       # fixed BEFORE the filter
        raw = ETFShareOptionFactor.replicate(etf, constituents, float(n)).positions
        full = self._positions(raw)
        short_premium = n * etf.multiplier * etf.bid
        original = StrategyLegs("original", n, full, short_premium, self._long_premium(constituents, full))
        known = set(full)
        unknown = [s for s in selection.selected if s not in known]
        if unknown:
            raise ValueError(f"selected constituents outside the basket: {unknown}")
        chosen = {s: full[s] for s in full if s in set(selection.selected)}
        filtered = StrategyLegs("model_filtered", n, chosen, short_premium, self._long_premium(constituents, chosen))
        return ConstructedTrade(opened, expiry, etf, list(constituents), n, original, filtered, selection, raw)

    # -- expiry --
    @staticmethod
    def settle(trade: ConstructedTrade, strategy: StrategyLegs, etf_price: float,
               prices: Mapping[str, float]) -> SettledStrategy:
        sizing = Sizing(strategy.etf_contracts, dict(strategy.positions), None, None)
        payoff = ETFShareOptionFactor.payoff_at_maturity(trade.etf, trade.constituents, sizing, etf_price,
                                                         dict(prices), strategy.net_initial_premium)
        return SettledStrategy(strategy.name, payoff, strategy.net_initial_premium)
