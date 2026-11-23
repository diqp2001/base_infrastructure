"""
Delta-hedge overlay — the hedge leg of an option book, as a construction step on ACTUAL holdings.

    open option positions (greeks x signed contracts)  -> aggregate_book_greeks -> BookGreeks
    a no-trade band half-width (a hedging model: Whalley-Wilmott, Zakamouline, a learned policy ... — supplied by the
    caller, these models are not domain rules)
      -> delta_hedge_decision: |book delta + current hedge| inside the band -> no trade; outside -> hedge all the way
         to delta 0 (target hedge = -book delta)
      -> hedge_target_portfolio: the hedge instrument at that quantity (a TargetPortfolio) -> rebalancing -> execution

The arithmetic is the SPX call-spread market maker's (Strategy.evaluate_portfolio_delta_hedge before 2026-11-23):
position delta / gamma = greek x signed size, summed; the implied vol and the time to expiry of the band are |gamma|
weighted averages over the positions (no gamma -> no implied vol, 30 calendar days).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio, TargetPortfolioPosition

DEFAULT_TIME_TO_EXPIRY = 30.0 / 365.25          # years, when a position does not carry its own


@dataclass(frozen=True)
class OptionExposure:
    """One open option position: its per-contract greeks and its signed size (negative = short)."""
    delta: float
    gamma: float
    size: float
    implied_vol: Optional[float] = None
    time_to_expiry: float = DEFAULT_TIME_TO_EXPIRY


@dataclass(frozen=True)
class BookGreeks:
    delta: float                       # sum of delta x size
    gamma: float                       # sum of gamma x size (signed)
    implied_vol: Optional[float]       # |gamma|-weighted average, None when no position carries one
    time_to_expiry: float              # |gamma|-weighted average (years)
    position_count: int


def aggregate_book_greeks(exposures: Iterable[OptionExposure]) -> BookGreeks:
    delta = gamma = total_weight = weighted_iv = weighted_tau = 0.0
    count = 0
    for e in exposures:
        count += 1
        p_delta = e.delta * e.size
        p_gamma = e.gamma * e.size
        weight = abs(p_gamma)
        delta += p_delta
        gamma += p_gamma
        total_weight += weight
        if e.implied_vol is not None:
            weighted_iv += weight * float(e.implied_vol)
        weighted_tau += weight * e.time_to_expiry
    if total_weight > 0:
        implied_vol = weighted_iv / total_weight if weighted_iv > 0 else None
        time_to_expiry = weighted_tau / total_weight
    else:
        implied_vol, time_to_expiry = None, DEFAULT_TIME_TO_EXPIRY
    return BookGreeks(delta, gamma, implied_vol, time_to_expiry, count)


@dataclass(frozen=True)
class DeltaHedgeDecision:
    should_hedge: bool
    book_delta: float
    current_hedge: float
    half_width: float
    net_residual: float                       # book delta + current hedge
    target_hedge: Optional[float] = None      # hedge-instrument delta to hold (= -book delta) when hedging
    trade: Optional[float] = None             # target - current (signed) when hedging

    @property
    def direction(self) -> Optional[str]:
        if self.trade is None:
            return None
        return 'buy' if self.trade > 0 else 'sell'


def delta_hedge_decision(book_delta: float, current_hedge: float, half_width: float) -> DeltaHedgeDecision:
    """No trade while |book delta + current hedge| <= half_width; outside the band, hedge back to delta 0."""
    net = book_delta + current_hedge
    if abs(net) <= half_width:
        return DeltaHedgeDecision(False, book_delta, current_hedge, half_width, net)
    target = -book_delta
    return DeltaHedgeDecision(True, book_delta, current_hedge, half_width, net, target, target - current_hedge)


def hedge_target_portfolio(symbol: str, quantity: float, as_of: Optional[datetime] = None,
                           asset_type: str = "CompanyShare", strategy_name: Optional[str] = None) -> TargetPortfolio:
    """The hedge instrument held at ``quantity`` units (a quantity target: the rebalancer trades the difference with
    the current holding). Its weight is not known here (0.0: information only, the quantity is the target)."""
    return TargetPortfolio(as_of=as_of, positions=(TargetPortfolioPosition(
        symbol=symbol, target_weight=0.0, asset_type=asset_type, target_quantity=float(quantity)),),
        strategy_name=strategy_name, construction="delta_hedge")
