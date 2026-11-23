"""
STMDecileLongShortTradingStrategy — the STM model's scores ranked into cross-sectional deciles, long the top decile and
short the bottom one (the monthly decile project's traded book).

    STM model (STMConstituentScorer, members in force at the period end) -> STM score per member
      -> this strategy: StrategySignals (score per symbol)
      -> portfolio construction (construction_method = quantile_long_short):
           rank by (score, symbol), decile = min(n, floor(i x n / N) + 1); Dn long, D1 short, equal weight inside
           each side, each side gross / 2; fewer than n scored members -> nothing
      -> TargetPortfolio -> rebalancing -> execution

The strategy holds the decile count and the gross exposure; the construction steps are the generic ones (the same
ranking rule as portfolio_research.decile_portfolios.assign_deciles).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import (  # noqa: E501
    CompanyShareSpatioTemporalMomentumFactor,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from src.domain.entities.finance.portfolio.construction.construction_method import (
    PortfolioConstructionMethod,
    quantile_long_short,
)

SCORE_KEY = "score"


class STMDecileLongShortTradingStrategy(TradingStrategy):

    def __init__(self, name: str = "stm_decile_long_short", n_deciles: int = 10, gross: float = 1.0,
                 frequency: Optional[str] = "1mth",**kwargs):
        if int(n_deciles) < 2:
            raise ValueError("at least two deciles")
        if gross <= 0:
            raise ValueError("gross exposure must be positive")
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.n_deciles = int(n_deciles)
        self.gross = float(gross)

    @property
    def calculate_dependencies(self) -> list:
        """The STM score of every member (per entity). The decile cycle gives the scores straight from its scorer
        instead (evaluate with the same key)."""
        return [DependencySpec(factor_type=CompanyShareSpatioTemporalMomentumFactor, group="momentum",
                               frequency=DependencySpec.SELF, source_in=["calculated"], per_entity=True,
                               key=SCORE_KEY)]

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        """``dependencies``: {'score': {symbol: [score, ...]}}. A non-finite score is left out (never ranked)."""
        scores = {s: float(v[-1]) for s, v in ((dependencies or {}).get(SCORE_KEY) or {}).items()
                  if v and v[-1] is not None and math.isfinite(float(v[-1]))}
        return StrategySignals(as_of=as_of, values=scores, asset_type="CompanyShare")

    def signals(self, scores: Mapping[str, float], as_of: Optional[datetime] = None) -> StrategySignals:
        return self.evaluate({SCORE_KEY: {s: [v] for s, v in scores.items()}}, as_of=as_of)

    def construction_method(self) -> PortfolioConstructionMethod:
        return quantile_long_short(self.n_deciles, self.gross)
