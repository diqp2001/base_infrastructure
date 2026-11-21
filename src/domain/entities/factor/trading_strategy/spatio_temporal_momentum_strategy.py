"""
SpatioTemporalMomentumTradingStrategy — the STM model's signals as a TradingStrategy.

    STM model (provider.score_details) -> STM signal per constituent (+ its daily volatility at the session)
      -> this strategy: StrategySignals (signal per ticker, volatility in the context)
      -> portfolio construction (construction_method = volatility_targeted_signals):
           w_i = signal_i x target_vol / (vol_i x sqrt(periods_per_year)) / N, then scaled down to gross_cap
      -> TargetPortfolio -> rebalancing -> execution

The strategy holds STM's parameters (target volatility, gross cap, periods per year of the bar size); the
construction steps are the generic ones. Unchanged STM rules: the signal's sign is the side; a constituent without a
usable volatility gets weight 0 and still counts in N; N = every scored constituent; the gross cap only scales down.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import (  # noqa: E501
    CompanyShareSpatioTemporalMomentumFactor,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from src.domain.entities.finance.portfolio.construction.construction_method import (
    PortfolioConstructionMethod,
    volatility_targeted_signals,
)

SIGNAL_KEY = "signal"
VOLATILITY_KEY = "volatility"


class SpatioTemporalMomentumTradingStrategy(TradingStrategy):

    def __init__(self, name: str = "spatio_temporal_momentum", target_vol: float = 0.15,
                 gross_cap: Optional[float] = 1.0, periods_per_year: int = 252, frequency: Optional[str] = "1d",
                 **kwargs):
        if target_vol <= 0:
            raise ValueError("target volatility must be positive")
        super().__init__(name=name, frequency=frequency, **kwargs)
        self.target_vol = float(target_vol)
        self.gross_cap = gross_cap
        self.periods_per_year = int(periods_per_year)

    @property
    def calculate_dependencies(self) -> list:
        """The stored STM signal of every constituent (written by STMFeatureStore.write_signals). The trading cycle
        gives the signals straight from the model instead (evaluate with the same keys)."""
        return [DependencySpec(factor_type=CompanyShareSpatioTemporalMomentumFactor, group="momentum",
                               frequency=DependencySpec.SELF, source_in=["calculated"], per_entity=True,
                               key=SIGNAL_KEY)]

    def evaluate(self, dependencies: Dict[str, Any], as_of: Optional[datetime] = None) -> StrategySignals:
        """``dependencies``: {'signal': {ticker: [signal, ...]}, 'volatility': {ticker: per-row volatility}}.
        The volatilities are required (the vol scaling cannot run without them)."""
        dependencies = dependencies or {}
        if VOLATILITY_KEY not in dependencies:
            raise ValueError(f"{self.name}: no '{VOLATILITY_KEY}' input: the volatility scaling needs it")
        signals = {t: float(v[-1]) for t, v in (dependencies.get(SIGNAL_KEY) or {}).items() if v}
        volatility: Mapping[str, float] = dict(dependencies[VOLATILITY_KEY] or {})
        return StrategySignals(as_of=as_of, values=signals, asset_type="CompanyShare",
                               context={VOLATILITY_KEY: volatility})

    def signals(self, scores: Mapping[str, float], daily_vol: Mapping[str, float],
                as_of: Optional[datetime] = None) -> StrategySignals:
        """The model's scores (ticker -> signal) and their volatilities as StrategySignals."""
        return self.evaluate({SIGNAL_KEY: {t: [s] for t, s in scores.items()}, VOLATILITY_KEY: daily_vol},
                             as_of=as_of)

    def construction_method(self) -> PortfolioConstructionMethod:
        return volatility_targeted_signals(self.target_vol, gross_cap=self.gross_cap,
                                           periods_per_year=self.periods_per_year)
