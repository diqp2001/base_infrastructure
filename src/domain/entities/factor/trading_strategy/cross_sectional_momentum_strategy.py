"""
CrossSectionalMomentumTradingStrategy — the cross-sectional momentum (CSM) classifier's scores as a TradingStrategy.

    CSM LightGBM model -> probability of beating the cross-sectional median, per constituent (+ its daily volatility)
      -> this strategy: StrategySignals (probability per ticker, volatility in the context)
      -> portfolio construction (construction_method = quantile_long_short_inverse_volatility):
           candidates = the scored assets with a usable volatility; k = floor(n x quantile) per side;
           long the top k / short the bottom k, inverse volatility inside each side, each side gross / 2
      -> TargetPortfolio -> rebalancing -> execution

The strategy holds CSM's parameters (quantile, gross exposure); the construction steps are the generic ones.
Ties in the ranking are broken by symbol (the CSM dataset already gives the scores in symbol order, so the
pre-refactor stable sort chose the same names).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (  # noqa: E501
    CompanyShareCrossSectionalMomentumFactor,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from src.domain.entities.finance.portfolio.construction.construction_method import (
    PortfolioConstructionMethod,
    quantile_long_short_inverse_volatility,
)

SCORE_KEY = "score"
VOLATILITY_KEY = "volatility"


class CrossSectionalMomentumTradingStrategy(TradingStrategy):

    def __init__(self, name: str = "cross_sectional_momentum", quantile: float = 0.2, gross: float = 1.0,
                 frequency: Optional[str] = "1d", **kwargs):
        if not 0 < quantile <= 0.5:
            raise ValueError(f"quantile must be in (0, 0.5], got {quantile}")
        if gross <= 0:
            raise ValueError("gross exposure must be positive")
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.quantile = float(quantile)
        self.gross = float(gross)

    @property
    def calculate_dependencies(self) -> list:
        """The stored CSM signal of every constituent (written by CSMSignalStore). The trading cycle gives the
        scores straight from the model instead (evaluate with the same keys)."""
        return [DependencySpec(factor_type=CompanyShareCrossSectionalMomentumFactor, group="momentum",
                               frequency=DependencySpec.SELF, source_in=["calculated"], per_entity=True,
                               key=SCORE_KEY)]

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        """``dependencies``: {'score': {ticker: [probability, ...]}, 'volatility': {ticker: daily volatility}}.
        The volatilities are required (inverse-volatility weights). A non-finite score is left out (never ranked)."""
        dependencies = dependencies or {}
        if VOLATILITY_KEY not in dependencies:
            raise ValueError(f"{self.name}: no '{VOLATILITY_KEY}' input: the inverse-volatility weights need it")
        scores = {t: float(v[-1]) for t, v in (dependencies.get(SCORE_KEY) or {}).items()
                  if v and v[-1] is not None and math.isfinite(float(v[-1]))}
        volatility: Mapping[str, float] = dict(dependencies[VOLATILITY_KEY] or {})
        return StrategySignals(as_of=as_of, values=scores, asset_type="CompanyShare",
                               context={VOLATILITY_KEY: volatility})

    def signals(self, scores: Mapping[str, float], daily_vol: Mapping[str, float],
                as_of: Optional[datetime] = None) -> StrategySignals:
        """The model's scores (ticker -> probability) and their volatilities as StrategySignals."""
        return self.evaluate({SCORE_KEY: {t: [s] for t, s in scores.items()}, VOLATILITY_KEY: daily_vol},
                             as_of=as_of)

    def construction_method(self) -> PortfolioConstructionMethod:
        return quantile_long_short_inverse_volatility(self.quantile, self.gross)
