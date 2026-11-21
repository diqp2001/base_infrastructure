"""
Portfolio construction steps — pure rules that turn strategy scores into target weights.

A construction method (construction_method.py) is three stages:

    1. selection    scores -> sides      which assets are held and which way (+1 long, -1 short, 0 flat)
    2. weighting    sides  -> weights    how much of each, before constraints
    3. adjustments  weights -> weights   scaling and constraints, applied in order

Every step is deterministic (ties are broken by symbol) and knows nothing about quantities held, prices, orders,
positions or brokers. Missing inputs a step needs (a volatility, a loading) are an error or a 0 weight, as each step
documents; no step invents a default value.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Mapping, Optional


@dataclass(frozen=True)
class ConstructionInputs:
    """What construction reads: the strategy's score per asset, optional per-row volatilities (e.g. daily) and
    optional loadings per asset for exposure limits ({'delta': {'AAPL_C150': 0.42, ...}})."""
    scores: Mapping[str, float]
    volatility: Mapping[str, float] = field(default_factory=dict)
    loadings: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    def __post_init__(self):
        bad = sorted(a for a, s in self.scores.items() if s is None or not math.isfinite(float(s)))
        if bad:
            raise ValueError(f"non-finite scores for {bad}")
        object.__setattr__(self, "scores", {a: float(self.scores[a]) for a in sorted(self.scores)})

    def vol(self, asset: str) -> Optional[float]:
        """The asset's volatility when usable (finite, > 0), else None."""
        v = self.volatility.get(asset)
        if v is None:
            return None
        v = float(v)
        return v if math.isfinite(v) and v > 0 else None


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def _ranked(scores: Mapping[str, float]) -> list:
    """Assets from the lowest to the highest score; ties broken by symbol."""
    return sorted(scores, key=lambda a: (scores[a], a))


# -- 1. selection --------------------------------------------------------------------------------------------------

class Selection(ABC):
    @abstractmethod
    def select(self, inputs: ConstructionInputs) -> Dict[str, int]:
        """{asset: side} with side in (+1, -1, 0); assets left out are not part of the target."""


def _candidates(inputs: ConstructionInputs, require_volatility: bool) -> Dict[str, float]:
    if not require_volatility:
        return dict(inputs.scores)
    return {a: s for a, s in inputs.scores.items() if inputs.vol(a) is not None}


@dataclass(frozen=True)
class AllAssets(Selection):
    """Every scored asset, the side being the score's sign (a 0 score stays in the target, flat)."""

    def select(self, inputs):
        return {a: _sign(s) for a, s in inputs.scores.items()}


@dataclass(frozen=True)
class QuantileLongShort(Selection):
    """Long the top ``quantile`` and short the bottom ``quantile`` of the ranked scores: k = floor(n x quantile)
    assets per side. Fewer than 2 candidates or k < 1 -> nothing selected. ``require_volatility`` keeps only the
    assets with a usable volatility as candidates (n counts those only)."""
    quantile: float = 0.2
    require_volatility: bool = False
    long_only: bool = False

    def __post_init__(self):
        if not 0 < self.quantile <= 0.5:
            raise ValueError(f"quantile must be in (0, 0.5], got {self.quantile}")

    def select(self, inputs):
        candidates = _candidates(inputs, self.require_volatility)
        n = len(candidates)
        k = int(math.floor(n * self.quantile))
        if n < 2 or k < 1:
            return {}
        ranked = _ranked(candidates)
        sides = {a: 1 for a in ranked[-k:]}
        if not self.long_only:
            sides.update({a: -1 for a in ranked[:k]})
        return sides


@dataclass(frozen=True)
class TopBottomN(Selection):
    """Long the ``n_long`` highest and short the ``n_short`` lowest scores (no asset on both sides)."""
    n_long: int = 0
    n_short: int = 0
    require_volatility: bool = False

    def select(self, inputs):
        ranked = _ranked(_candidates(inputs, self.require_volatility))
        longs = ranked[max(len(ranked) - self.n_long, 0):] if self.n_long > 0 else []
        shorts = [a for a in ranked[:max(self.n_short, 0)] if a not in longs]
        return {**{a: -1 for a in shorts}, **{a: 1 for a in longs}}


@dataclass(frozen=True)
class Threshold(Selection):
    """Long the scores above ``long_above``, short those below ``short_below`` (strict); None disables a side."""
    long_above: Optional[float] = None
    short_below: Optional[float] = None

    def select(self, inputs):
        sides = {}
        for a, s in inputs.scores.items():
            if self.long_above is not None and s > self.long_above:
                sides[a] = 1
            elif self.short_below is not None and s < self.short_below:
                sides[a] = -1
        return sides


def _both_sides_or_nothing(sides: Dict[str, int]) -> Dict[str, int]:
    """A long/short selection with an empty side selects nothing (the CSM rule: k < 1 -> no portfolio)."""
    return sides if (1 in sides.values() and -1 in sides.values()) else {}


@dataclass(frozen=True)
class Buckets(Selection):
    """Scores that already are bucket labels (e.g. a quintile 1-5): long the ``long`` buckets, short the ``short``
    ones, e.g. long Q5 / short Q1. ``round_labels`` reads 4.6 as bucket 5 (a model's label output may be a float);
    ``require_both_sides``: nothing is selected when one side is empty."""
    long: FrozenSet[float] = frozenset({5.0})
    short: FrozenSet[float] = frozenset({1.0})
    round_labels: bool = False
    require_both_sides: bool = False

    def __post_init__(self):
        object.__setattr__(self, "long", frozenset(float(b) for b in self.long))
        object.__setattr__(self, "short", frozenset(float(b) for b in self.short))
        if self.long & self.short:
            raise ValueError(f"buckets {sorted(self.long & self.short)} are both long and short")

    def select(self, inputs):
        sides = {}
        for a, s in inputs.scores.items():
            label = float(round(s)) if self.round_labels else s
            if label in self.long:
                sides[a] = 1
            elif label in self.short:
                sides[a] = -1
        return _both_sides_or_nothing(sides) if self.require_both_sides else sides


def quantile_labels(scores: Mapping[str, float], n_buckets: int) -> Dict[str, int]:
    """{asset: bucket 1..n_buckets} (1 = lowest): ranked ascending by (score, symbol) — ties broken by the symbol —
    bucket = min(n, floor(i x n / N) + 1), the rule of portfolio_research.decile_portfolios.assign_deciles."""
    ranked = _ranked(scores)
    total = len(ranked)
    return {a: min(n_buckets, int(math.floor(i * n_buckets / total)) + 1) for i, a in enumerate(ranked)}


@dataclass(frozen=True)
class QuantileBuckets(Selection):
    """Rank the scores cross-sectionally into ``n_buckets`` (quantile_labels), long the ``long`` buckets and short the
    ``short`` ones. Fewer than ``n_buckets`` scored assets -> nothing selected (the top bucket would be empty)."""
    n_buckets: int = 5
    long: FrozenSet[int] = frozenset({5})
    short: FrozenSet[int] = frozenset({1})

    def __post_init__(self):
        if self.n_buckets < 2:
            raise ValueError("at least 2 buckets")
        if self.long & self.short:
            raise ValueError(f"buckets {sorted(self.long & self.short)} are both long and short")

    def select(self, inputs):
        if len(inputs.scores) < self.n_buckets:
            return {}
        sides = {}
        for a, bucket in quantile_labels(inputs.scores, self.n_buckets).items():
            if bucket in self.long:
                sides[a] = 1
            elif bucket in self.short:
                sides[a] = -1
        return _both_sides_or_nothing(sides)


# -- 2. weighting --------------------------------------------------------------------------------------------------

class Weighting(ABC):
    @abstractmethod
    def weigh(self, sides: Mapping[str, int], inputs: ConstructionInputs) -> Dict[str, float]:
        """{asset: signed weight} for the selected assets."""


@dataclass(frozen=True)
class EqualWeighting(Weighting):
    """Weight = side (+1 / -1 / 0); scale with Normalise / NormaliseSides afterwards."""

    def weigh(self, sides, inputs):
        return {a: float(side) for a, side in sides.items()}


@dataclass(frozen=True)
class ScoreWeighting(Weighting):
    """Weight = side x |score|: with AllAssets, the score itself."""

    def weigh(self, sides, inputs):
        return {a: side * abs(inputs.scores[a]) for a, side in sides.items()}


@dataclass(frozen=True)
class InverseVolatilityWeighting(Weighting):
    """Weight = side / volatility; an asset without a usable volatility gets 0."""

    def weigh(self, sides, inputs):
        return {a: (side / inputs.vol(a) if inputs.vol(a) is not None else 0.0) for a, side in sides.items()}


# -- 3. adjustments (scaling and constraints) ----------------------------------------------------------------------

class Adjustment(ABC):
    @abstractmethod
    def adjust(self, weights: Dict[str, float], inputs: ConstructionInputs) -> Dict[str, float]:
        """New weights (same assets)."""


@dataclass(frozen=True)
class VolatilityScaling(Adjustment):
    """w x target_vol / annualised vol, the volatility being per row (annualised by sqrt(periods_per_year)); an
    asset without a usable volatility gets 0 (it stays in the target, flat)."""
    target_vol: float = 0.15
    periods_per_year: int = 252

    def adjust(self, weights, inputs):
        out = {}
        for a, w in weights.items():
            vol = inputs.vol(a)
            out[a] = 0.0 if vol is None else w * self.target_vol / (vol * self.periods_per_year ** 0.5)
        return out


@dataclass(frozen=True)
class DivideByCount(Adjustment):
    """w / N, N being the number of assets in the target (the flat ones included)."""

    def adjust(self, weights, inputs):
        n = len(weights)
        return {a: w / n for a, w in weights.items()} if n else {}


@dataclass(frozen=True)
class Normalise(Adjustment):
    """Scale every weight so the gross exposure is exactly ``gross`` (all-zero weights stay zero)."""
    gross: float = 1.0

    def adjust(self, weights, inputs):
        total = sum(abs(w) for w in weights.values())
        return {a: w * self.gross / total for a, w in weights.items()} if total > 0 else dict(weights)


@dataclass(frozen=True)
class NormaliseSides(Adjustment):
    """Scale the longs to a gross of ``long`` and the shorts to a gross of ``short`` (a side with no weight stays
    empty)."""
    long: float = 0.5
    short: float = 0.5

    def adjust(self, weights, inputs):
        long_total = sum(w for w in weights.values() if w > 0)
        short_total = -sum(w for w in weights.values() if w < 0)
        out = {}
        for a, w in weights.items():
            if w > 0:
                out[a] = w * self.long / long_total
            elif w < 0:
                out[a] = w * self.short / short_total
            else:
                out[a] = 0.0
        return out


@dataclass(frozen=True)
class GrossExposureCap(Adjustment):
    """Scale every weight down (never up) so the gross exposure is at most ``cap``."""
    cap: float = 1.0

    def adjust(self, weights, inputs):
        gross = sum(abs(w) for w in weights.values())
        if self.cap and gross > self.cap:
            return {a: w * self.cap / gross for a, w in weights.items()}
        return dict(weights)


@dataclass(frozen=True)
class NetExposureLimit(Adjustment):
    """|net exposure| <= ``max_abs``: the dominant side is scaled down until the limit holds."""
    max_abs: float = 0.0

    def adjust(self, weights, inputs):
        long_total = sum(w for w in weights.values() if w > 0)
        short_total = -sum(w for w in weights.values() if w < 0)
        net = long_total - short_total
        if abs(net) <= self.max_abs:
            return dict(weights)
        if net > 0:      # longs dominate: long' = short + max_abs
            k = (short_total + self.max_abs) / long_total
            return {a: (w * k if w > 0 else w) for a, w in weights.items()}
        k = (long_total + self.max_abs) / short_total
        return {a: (w * k if w < 0 else w) for a, w in weights.items()}


@dataclass(frozen=True)
class AssetWeightLimit(Adjustment):
    """|w| <= ``max_abs`` per asset (clipped; the excess is not redistributed)."""
    max_abs: float = 0.1

    def adjust(self, weights, inputs):
        return {a: max(-self.max_abs, min(self.max_abs, w)) for a, w in weights.items()}


@dataclass(frozen=True)
class ExposureLimit(Adjustment):
    """|sum_i w_i x loading_i| <= ``max_abs`` for one loading (e.g. 'delta' of option positions): every weight is
    scaled down by the same factor when the limit is exceeded. A weighted asset without that loading is an error."""
    loading: str = "delta"
    max_abs: float = 0.0

    def adjust(self, weights, inputs):
        loadings = inputs.loadings.get(self.loading, {})
        missing = sorted(a for a, w in weights.items() if w != 0 and a not in loadings)
        if missing:
            raise ValueError(f"no '{self.loading}' loading for {missing}")
        exposure = sum(w * float(loadings[a]) for a, w in weights.items() if w != 0)
        if abs(exposure) <= self.max_abs:
            return dict(weights)
        k = self.max_abs / abs(exposure)
        return {a: w * k for a, w in weights.items()}
