"""
PortfolioConstructionMethod — one strategy's way of turning scores into a TargetPortfolio:
selection -> weighting -> adjustments (steps.py).

    method = PortfolioConstructionMethod("q5_q1", Buckets({5}, {1}), EqualWeighting(), (NormaliseSides(0.5, 0.5),))
    target = method.build(ConstructionInputs(scores={...}), as_of=t)

The ready-made methods below are compositions of the generic steps; two of them reproduce rules that live inside
trading cycles today (pinned by tests/strategy/test_portfolio_construction.py), so a cycle can move to this layer
without a change in weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Tuple

from src.domain.entities.finance.portfolio.construction.steps import (
    Adjustment,
    AllAssets,
    Buckets,
    ConstructionInputs,
    DivideByCount,
    EqualWeighting,
    GrossExposureCap,
    InverseVolatilityWeighting,
    NormaliseSides,
    QuantileLongShort,
    ScoreWeighting,
    Selection,
    VolatilityScaling,
    Weighting,
)
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio


@dataclass(frozen=True)
class PortfolioConstructionMethod:
    name: str
    selection: Selection = AllAssets()
    weighting: Weighting = ScoreWeighting()
    adjustments: Tuple[Adjustment, ...] = ()

    def weights(self, inputs: ConstructionInputs) -> dict:
        sides = self.selection.select(inputs)
        weights = self.weighting.weigh(dict(sorted(sides.items())), inputs)
        for step in self.adjustments:
            weights = step.adjust(weights, inputs)
        return dict(sorted(weights.items()))

    def build(self, inputs: ConstructionInputs, as_of: Optional[datetime] = None, strategy_name: Optional[str] = None,
              asset_type: Optional[str] = None, asset_ids: Optional[Mapping[str, int]] = None,
              note: str = "") -> TargetPortfolio:
        return TargetPortfolio.from_weights(self.weights(inputs), as_of=as_of, asset_type=asset_type,
                                            asset_ids=asset_ids, strategy_name=strategy_name, construction=self.name,
                                            note=note)


def volatility_targeted_signals(target_vol: float = 0.15, gross_cap: Optional[float] = None,
                                periods_per_year: int = 252) -> PortfolioConstructionMethod:
    """Every signal, w = signal x target_vol / (vol x sqrt(P)) / N, then scaled down to ``gross_cap`` — the rule of
    spatio_temporal_momentum.stm_backtest.signals_to_weights (a signal without usable vol -> 0 weight, still in N)."""
    adjustments = [VolatilityScaling(target_vol, periods_per_year), DivideByCount()]
    if gross_cap:
        adjustments.append(GrossExposureCap(gross_cap))
    return PortfolioConstructionMethod("volatility_targeted_signals", AllAssets(), ScoreWeighting(),
                                       tuple(adjustments))


def quantile_long_short_inverse_volatility(quantile: float, gross: float) -> PortfolioConstructionMethod:
    """Long the top / short the bottom ``quantile`` (assets with a usable vol), inverse-vol inside each side, each
    side gross/2 — the rule of cross_sectional_momentum.csm_trading_cycle.long_short_weights."""
    return PortfolioConstructionMethod("quantile_long_short_inverse_volatility",
                                       QuantileLongShort(quantile, require_volatility=True),
                                       InverseVolatilityWeighting(), (NormaliseSides(gross / 2.0, gross / 2.0),))


def bucket_long_short(long_buckets=(5,), short_buckets=(1,), gross: float = 1.0) -> PortfolioConstructionMethod:
    """Scores that are bucket labels (quintile 1-5): equal weight long the ``long_buckets``, short the
    ``short_buckets``, each side gross/2 (long Q5 / short Q1 by default)."""
    return PortfolioConstructionMethod("bucket_long_short", Buckets(frozenset(long_buckets), frozenset(short_buckets)),
                                       EqualWeighting(), (NormaliseSides(gross / 2.0, gross / 2.0),))
