"""
TradingStrategyEvaluationService — evaluates a TradingStrategy factor at one time.

    signals = TradingStrategyEvaluationService(resolution_service).evaluate(strategy, universe, as_of)

1. the strategy's dependencies (its ranking / scoring factors, per constituent) are resolved on its parent entity —
   a Universe (its members in force at ``as_of``) or an ETF (its holdings) — by the existing
   FactorValueResolutionService (``resolve_dependencies``: no second dependency system, nothing stored for the
   strategy itself);
2. the strategy interprets them: ``TradingStrategy.evaluate`` -> StrategySignals.

The signals then go to portfolio construction. Nothing here sizes positions or creates orders.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy


class TradingStrategyEvaluationService:

    def __init__(self, resolution_service, logger: Optional[logging.Logger] = None):
        self.resolution = resolution_service
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def dependencies(self, strategy: TradingStrategy, parent_entity, as_of: datetime,
                     repository_type: str = "local") -> Dict[str, Any]:
        """The resolved inputs of ``strategy`` on ``parent_entity`` at ``as_of`` ({} when none could be resolved)."""
        resolved = self.resolution.resolve_dependencies(strategy, parent_entity, as_of,
                                                        repository_type=repository_type)
        return dict(resolved or {})

    def evaluate(self, strategy: TradingStrategy, parent_entity, as_of: datetime,
                 repository_type: str = "local") -> StrategySignals:
        if not isinstance(strategy, TradingStrategy):
            raise TypeError(f"{type(strategy).__name__} is not a TradingStrategy")
        inputs = self.dependencies(strategy, parent_entity, as_of, repository_type)
        if not inputs:
            self.logger.warning(f"{strategy.name}: no dependency resolved on {type(parent_entity).__name__} "
                                f"{getattr(parent_entity, 'id', '?')} at {as_of}")
        return strategy.evaluate(inputs, as_of=as_of)

    def target_portfolio(self, strategy: TradingStrategy, parent_entity, as_of: datetime, method=None,
                         construction_service=None, repository_type: str = "local", **construct_kwargs):
        """ranking factor -> strategy -> portfolio construction -> TargetPortfolio (never orders).

        ``method`` defaults to the strategy's own construction_method()."""
        from src.application.services.portfolio_construction.portfolio_construction_service import (
            PortfolioConstructionService,
        )
        method = method or strategy.construction_method()
        if method is None:
            raise ValueError(f"{strategy.name}: no construction method (pass one or define construction_method())")
        signals = self.evaluate(strategy, parent_entity, as_of, repository_type)
        service = construction_service or PortfolioConstructionService(self.logger)
        return service.construct(signals, method, strategy_name=strategy.name, **construct_kwargs)
