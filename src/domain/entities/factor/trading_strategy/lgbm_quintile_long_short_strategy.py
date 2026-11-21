"""
LGBMQuintileLongShortStrategy — long Q5 / short Q1 of the LightGBM cross-sectional quintile ranking.

    Universe (eligible constituents in force)
      -> CompanyShareLGBMCSQuintileRankMomentumFactor (one value per constituent; the factor and its model provider
         produce it — nothing of the model or its scoring is repeated here)
      -> this strategy: the constituents' latest values as StrategySignals
      -> portfolio construction (construction_method):
           quintiles -> Q5 long, Q1 short, Q2-Q4 no position, equal weight inside each side, each side gross / 2
      -> TargetPortfolio

Two ways to read quintiles (``quintiles``):
  'factor'           the factor's own label (1-5, rounded: a model may return 4.6) — the default: the factor already
                     is a quintile classification;
  'cross_sectional'  rank the values across the constituents into 5 buckets (by value then symbol, the decile
                     project's rule) — for a continuous score.

Conventions (from the existing projects): a constituent without a value is left out of the ranking (and of the
target); when the long or the short side would be empty ('factor': no Q1 or no Q5 label; 'cross_sectional': fewer
than 5 scored constituents), the target is empty — the CSM rule (k < 1 -> no portfolio). The universe gives the constituents only; scores, ranks
and weights never go into it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (  # noqa: E501
    CompanyShareLGBMCSQuintileRankMomentumFactor,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from src.domain.entities.finance.portfolio.construction.construction_method import (
    PortfolioConstructionMethod,
    bucket_long_short,
    quantile_long_short,
)

FACTOR_QUINTILES, CROSS_SECTIONAL_QUINTILES = "factor", "cross_sectional"
SCORE_KEY = "score"
N_QUINTILES = 5


class LGBMQuintileLongShortStrategy(TradingStrategy):

    def __init__(self, name: str = "lgbm_cs_quintile_long_short", quintiles: str = FACTOR_QUINTILES,
                 gross: float = 1.0, score_group: str = "momentum", frequency: Optional[str] = "1d", **kwargs):
        if quintiles not in (FACTOR_QUINTILES, CROSS_SECTIONAL_QUINTILES):
            raise ValueError(f"quintiles must be '{FACTOR_QUINTILES}' or '{CROSS_SECTIONAL_QUINTILES}'")
        if gross <= 0:
            raise ValueError("gross exposure must be positive")
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.quintiles = quintiles
        self.gross = float(gross)
        self.score_group = score_group

    @property
    def calculate_dependencies(self) -> list:
        """The ranking factor's value for every constituent of the parent (per_entity), at the strategy's
        frequency, calculated values only."""
        return [DependencySpec(factor_type=CompanyShareLGBMCSQuintileRankMomentumFactor, group=self.score_group,
                               frequency=DependencySpec.SELF, source_in=["calculated"], per_entity=True,
                               key=SCORE_KEY)]

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        per_constituent = (dependencies or {}).get(SCORE_KEY) or {}
        scores = {symbol: float(values[-1]) for symbol, values in per_constituent.items() if values}
        return StrategySignals(as_of=as_of, values=scores, asset_type="CompanyShare",
                               context={"quintiles": self.quintiles},
                               note="" if scores else "no ranking value for any constituent")

    def construction_method(self) -> PortfolioConstructionMethod:
        if self.quintiles == FACTOR_QUINTILES:
            return bucket_long_short((N_QUINTILES,), (1,), gross=self.gross, round_labels=True,
                                     require_both_sides=True)
        return quantile_long_short(N_QUINTILES, gross=self.gross)
