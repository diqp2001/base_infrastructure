"""
PortfolioConstructionService — StrategySignals -> TargetPortfolio.

    Factor values -> TradingStrategy.evaluate -> StrategySignals
                  -> PortfolioConstructionService.construct(signals, method) -> TargetPortfolio

The rules are the domain's (src/domain/entities/finance/portfolio/construction): this service only gathers their
inputs (the scores from the signals, the volatilities and loadings from the caller or from the signals' context)
and names the result. It submits no order, reads or updates no position, creates no transaction and has no broker
code: the TargetPortfolio goes to rebalancing, which compares it with what the account holds.
"""

from __future__ import annotations

import logging
from typing import Mapping, Optional

from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals
from src.domain.entities.finance.portfolio.construction.construction_method import PortfolioConstructionMethod
from src.domain.entities.finance.portfolio.construction.steps import ConstructionInputs
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio


class PortfolioConstructionService:

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def construct(self, signals: StrategySignals, method: PortfolioConstructionMethod,
                  volatility: Optional[Mapping[str, float]] = None,
                  loadings: Optional[Mapping[str, Mapping[str, float]]] = None,
                  asset_ids: Optional[Mapping[str, int]] = None,
                  strategy_name: Optional[str] = None) -> TargetPortfolio:
        """The target of ``method`` on ``signals``. ``volatility`` / ``loadings`` default to the signals' context
        entries of the same name."""
        context = signals.context or {}
        inputs = ConstructionInputs(
            scores=dict(signals.values),
            volatility=dict(volatility if volatility is not None else context.get("volatility") or {}),
            loadings=dict(loadings if loadings is not None else context.get("loadings") or {}),
        )
        target = method.build(inputs, as_of=signals.as_of, strategy_name=strategy_name,
                              asset_type=signals.asset_type, asset_ids=asset_ids, note=signals.note)
        if signals.values and not len(target):
            self.logger.info(f"{method.name}: {len(signals)} signals, no asset selected at {signals.as_of}")
        return target
