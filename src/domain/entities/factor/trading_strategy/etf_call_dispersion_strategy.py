"""
ETFCallDispersionTradingStrategy — short the ETF's ATM call, long the ATM calls of the constituents the ranking does
not expect to fall (refactor phase P7: architectural readiness, not the production strategy).

    ETF (parent entity) -> its constituents (holdings) and their ETF weights ('weights', _related_weights)
      -> the constituents' ranking factor (STM signal, per_entity)            = what the model expects
      -> this strategy: StrategySignals (score per constituent; ETF weights in the context)
      -> dispersion construction (application/services/dispersion/dispersion_target_portfolio.py):
           1-2 select the constituents (model_selection: names expected to decline are excluded)
           3-5 size the ATM call legs: N short ETF calls fixed from the full basket, constituent calls replicating
               the ETF weights, premiums at bid / ask (DispersionPortfolioConstructionService)
           6-7 option deltas: net dollar delta of the legs reported; a delta limit is the next construction step
           8   -> TargetPortfolio of option contracts (target_quantity), never orders

The strategy only interprets factor values. Option prices, deltas and contracts are market inputs of the
construction (the legs), not of the strategy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import (  # noqa: E501
    CompanyShareSpatioTemporalMomentumFactor,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy

SCORE_KEY = "score"
WEIGHTS_KEY = "weights"           # what the resolution service adds for a parent with constituent weights (an ETF)


class ETFCallDispersionTradingStrategy(TradingStrategy):

    def __init__(self, name: str = "etf_call_dispersion", score_factor=CompanyShareSpatioTemporalMomentumFactor,
                 score_group: str = "momentum", frequency: Optional[str] = "1d", **kwargs):
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.score_factor = score_factor
        self.score_group = score_group

    @property
    def calculate_dependencies(self) -> list:
        """The ranking factor of every constituent of the ETF (per_entity); the ETF weights come with them."""
        return [DependencySpec(factor_type=self.score_factor, group=self.score_group, frequency=DependencySpec.SELF,
                               source_in=["calculated"], per_entity=True, key=SCORE_KEY)]

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        dependencies = dependencies or {}
        scores = {s: float(v[-1]) for s, v in (dependencies.get(SCORE_KEY) or {}).items() if v}
        weights = {s: float(w) for s, w in (dependencies.get(WEIGHTS_KEY) or {}).items()}
        return StrategySignals(as_of=as_of, values=scores, asset_type="CompanyShare",
                               context={"etf_weights": weights},
                               note="" if weights else "no ETF constituent weights")
