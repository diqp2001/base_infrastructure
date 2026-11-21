"""
src/domain/entities/factor/trading_strategy/trading_strategy.py

TradingStrategy — a tradable investment strategy defined with one or more factors, as a Factor.

A ranking / scoring factor answers "how attractive is this asset?"; a TradingStrategy answers "how is that
information used to build a tradable strategy?". It is a Factor so that it takes part in the existing dependency
graph: ``calculate_dependencies`` declares the factors it reads (``DependencySpec``, usually ``per_entity=True`` so
that it sees every constituent of its parent entity — a Universe, or an ETF for dispersion), and the existing
FactorValueResolutionService resolves them.

Its output is not one number but a view over the constituents (``StrategySignals``), which portfolio construction
turns into a target portfolio. So a strategy has no scalar ``calculate`` value: ``calculate`` returns None (nothing
is persisted as a factor value), and ``evaluate`` gives the signals.

It never creates orders, never sizes positions in quantities and knows nothing about brokers or persistence.
Concrete strategies (LGBM quintile, STM, ETF call dispersion) subclass it and implement ``evaluate``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from src.domain.entities.factor.factor import Factor


@dataclass(frozen=True)
class StrategySignals:
    """What a strategy concludes for each constituent at one time: {asset key: value}.

    The value's meaning is the strategy's (a long / short side, a vol-scaled signal, a selected leg...); portfolio
    construction interprets it. ``asset_type`` is the domain class name of the constituents (e.g. 'CompanyShare');
    ``context`` carries extra inputs construction needs (e.g. per-asset volatility), never orders.
    """
    as_of: Optional[datetime]
    values: Mapping[str, float]
    asset_type: Optional[str] = None
    context: Mapping[str, Any] = field(default_factory=dict)
    note: str = ""

    def __post_init__(self):
        bad = {k: v for k, v in self.values.items() if not isinstance(v, (int, float)) or not math.isfinite(v)}
        if bad:
            raise ValueError(f"strategy signals must be finite numbers: {bad}")

    def __len__(self) -> int:
        return len(self.values)

    def assets(self) -> List[str]:
        return list(self.values)


class TradingStrategy(Factor):
    """Base of every trading strategy. Subclasses declare their factor dependencies and implement ``evaluate``;
    ranking, selection and weighting rules belong to the concrete strategy / portfolio construction, not here."""

    def __init__(
        self,
        name: str = "trading_strategy",
        group: str = "strategy",
        subgroup: Optional[str] = "trading_strategy",
        frequency: Optional[str] = "1d",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition or f"Trading strategy: {name}",
            factor_id=factor_id,
        )

    @property
    def calculate_dependencies(self) -> list:
        """The factors the strategy reads (DependencySpec). None by default: a concrete strategy declares them."""
        return []

    def calculate(self, dependencies: dict) -> Optional[float]:
        """A strategy has no scalar value: nothing is stored as a factor value (use ``evaluate``)."""
        return None

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        """The strategy's view over the constituents from its resolved dependencies.

        ``dependencies`` is what the resolution service gives a factor: per-entity specs as
        {result_key: {asset key: [values]}}, plus 'weights' of the parent's constituents when it defines them."""
        raise NotImplementedError(f"{type(self).__name__} must implement evaluate()")

    def construction_method(self):
        """The portfolio construction this strategy's signals go through (a PortfolioConstructionMethod), or None
        when the caller chooses one. Construction turns the signals into a TargetPortfolio; never into orders."""
        return None
