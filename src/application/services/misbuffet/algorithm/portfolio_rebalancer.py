"""
PortfolioRebalancer — target portfolio + current portfolio = required trades.

    TargetPortfolio (or target weights / quantities)
        -> PortfolioRebalancer.plan(..., current)  -> RebalancePlan (sells, then buys)
        -> UnifiedPortfolioManager.set_holdings executes it through TradeManager (existing path)

For every asset it is asked about:

    target_qty = target quantity when given, else int(portfolio_value x target_weight / (price x multiplier))
    order_qty  = target_qty - current_qty          > 0 BUY, < 0 SELL, 0 no order

An asset to liquidate (held, absent from the target) has target 0. A weight target inside the no-trade band
(|target weight - current weight| < min_weight_change) is not traded; quantity targets and liquidations always are.
An asset without a price is not traded.

The rebalancer only knows targets, quantities, prices and multipliers: no strategy, factor, ranking or model, and
no broker. It reads the current portfolio through the CurrentPortfolio callables the caller gives (the portfolio
manager's existing price / position / multiplier lookups), in the same order and as lazily as set_holdings always did:
the price first, then the quantity, then the multiplier (weight targets and liquidations only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Mapping, Optional, Tuple

from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio

BUY, SELL = "BUY", "SELL"
REBALANCE, LIQUIDATE = "rebalance", "liquidate"


@dataclass(frozen=True)
class TradeInstruction:
    ticker: str
    order_qty: int
    price: float
    current_qty: int
    target_qty: int
    reason: str = REBALANCE            # 'rebalance' or 'liquidate'

    @property
    def side(self) -> str:
        return BUY if self.order_qty > 0 else SELL


@dataclass(frozen=True)
class RebalancePlan:
    sells: Tuple[TradeInstruction, ...] = ()
    buys: Tuple[TradeInstruction, ...] = ()
    within_band: Tuple[str, ...] = ()          # weight targets not traded (no-trade band)
    unpriced: Tuple[str, ...] = ()             # assets without a price: not traded
    unchanged: Tuple[str, ...] = ()            # order quantity 0

    @property
    def instructions(self) -> Tuple[TradeInstruction, ...]:
        """Sells first (they free cash / reduce exposure), then buys."""
        return self.sells + self.buys

    def by_ticker(self) -> Dict[str, TradeInstruction]:
        return {i.ticker: i for i in self.instructions}


@dataclass(frozen=True)
class CurrentPortfolio:
    """What the account holds, as the rebalancer reads it: the portfolio value and, per asset, lookups of its
    price (None = no price), its held quantity and its contract multiplier (1 for a share)."""
    portfolio_value: float
    price_of: Callable[[str], Optional[float]]
    quantity_of: Callable[[str], int]
    multiplier_of: Callable[[str], float] = field(default=lambda ticker: 1)

    @classmethod
    def from_mappings(cls, portfolio_value: float, prices: Mapping[str, float],
                      quantities: Mapping[str, int], multipliers: Optional[Mapping[str, float]] = None
                      ) -> "CurrentPortfolio":
        mult = dict(multipliers or {})
        return cls(portfolio_value=float(portfolio_value), price_of=lambda t: prices.get(t),
                   quantity_of=lambda t: int(quantities.get(t, 0)), multiplier_of=lambda t: mult.get(t, 1))


class PortfolioRebalancer:

    def plan(self, current: CurrentPortfolio, target_weights: Optional[Mapping[str, float]] = None,
             target_quantities: Optional[Mapping[str, int]] = None, liquidate: Iterable[str] = (),
             min_weight_change: Optional[float] = None) -> RebalancePlan:
        weights = dict(target_weights or {})
        quantities = dict(target_quantities or {})
        to_liquidate = set(liquidate) - set(weights) - set(quantities)
        if current.portfolio_value <= 0:
            raise ValueError(f"portfolio value {current.portfolio_value} is not positive: nothing can be sized")
        pv = current.portfolio_value
        sells, buys, within_band, unpriced, unchanged = [], [], [], [], []
        for ticker in sorted(set(weights) | set(quantities) | to_liquidate):
            price = current.price_of(ticker)
            if not price:
                unpriced.append(ticker)
                continue
            current_qty = current.quantity_of(ticker)
            if ticker in quantities:
                target_qty = int(quantities[ticker])
            else:
                target_pct = weights.get(ticker, 0.0)
                # one contract of an option / future is worth price x multiplier (BI-009)
                multiplier = current.multiplier_of(ticker)
                target_qty = int(pv * target_pct / (price * multiplier))
                current_pct = current_qty * price * multiplier / pv
                if (min_weight_change and ticker not in to_liquidate
                        and abs(target_pct - current_pct) < min_weight_change):
                    within_band.append(ticker)
                    continue
            order_qty = target_qty - current_qty
            if order_qty == 0:
                unchanged.append(ticker)
                continue
            instruction = TradeInstruction(ticker, order_qty, price, current_qty, target_qty,
                                           LIQUIDATE if ticker in to_liquidate else REBALANCE)
            (sells if order_qty < 0 else buys).append(instruction)
        return RebalancePlan(tuple(sells), tuple(buys), tuple(within_band), tuple(unpriced), tuple(unchanged))

    def plan_target(self, target: TargetPortfolio, current: CurrentPortfolio, liquidate: Iterable[str] = (),
                    min_weight_change: Optional[float] = None) -> RebalancePlan:
        """The trades from ``current`` to ``target``: a position with a target quantity is sized in units, the
        others by weight; ``liquidate`` are held assets absent from the target (the caller decides which)."""
        weights, quantities = target_portfolio_targets(target)
        return self.plan(current, weights, quantities, liquidate, min_weight_change)


def target_portfolio_targets(target: TargetPortfolio) -> Tuple[Dict[str, float], Dict[str, int]]:
    """(weights, quantities) of a TargetPortfolio: a position with a target quantity is a quantity target."""
    weights = {p.symbol: p.target_weight for p in target if p.target_quantity is None}
    quantities = {p.symbol: int(p.target_quantity) for p in target if p.target_quantity is not None}
    return weights, quantities
