"""
Cross-sectional momentum algorithm for the Misbuffet engine (backtest and live).

initialize():
    portfolio registration (Misbuffet), then the trainer wires the
    CSMTradingCycle onto this algorithm's MarketDataService and
    MarketDataHistoryService (whose frontier blocks look-ahead).

on_data(data):
    cycle.step(bar time)  -> frontier advance, data update, retrain when due,
                             scores from the model valid for the session
    set_holdings(weights) -> UnifiedPortfolioManager (orders, transactions, positions)

Nothing here knows about LightGBM; the same code runs when the engine is live.
"""

import logging
from typing import Any, List

from src.application.managers.project_managers.cross_sectionnal_project.config import get_config
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class Algorithm(BaseProjectAlgorithm):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cycle = None
        self.cycle_results: List[Any] = []
        self.progress_tracker = None  # optional STMProgressTracker (Flask dashboard)

    def initialize(self):
        super().initialize()
        self.config = get_config()
        portfolio_config = self.config.get('Portfolio', {})
        if self._entity_service:
            portfolio_entity = self.register_portfolio(portfolio_config=portfolio_config)
            if portfolio_entity:
                self.portfolio_entity = portfolio_entity
            else:
                self.warning("Failed to register cross-sectional momentum portfolio")
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']

        if getattr(self, 'trainer', None) is not None and self._entity_service is not None:
            self.cycle = self.trainer.build_cycle(
                market_data_service=self._market_data_service,
                history_service=self._market_data_history_service,
                factory=self.repository_factory,
                log=self.progress_tracker.log if self.progress_tracker is not None else self.log,
            )
        else:
            self.warning("No trainer / entity service injected — cross-sectional momentum cycle disabled")

    def on_data(self, data):
        try:
            if not self.initialized or self.cycle is None:
                return
            bar_time = getattr(data, 'time', None) or getattr(self, 'time', None)
            if bar_time is None:
                return
            result = self.cycle.step(bar_time)
            self.cycle_results.append(result)
            if result.retrained:
                self.log(f"CSM model retrained at session {result.session.date()} (artifact {result.artifact_id})")
            if result.weights and self._unified_portfolio_manager:
                self._unified_portfolio_manager.set_holdings(
                    {CompanyShare: [{'name': t, 'weight': w} for t, w in result.weights.items()]},
                    data=data,
                )
            elif not result.weights:
                self.log(f"No CSM position change at {bar_time}: {result.note}")
            self._update_portfolio_value(data)
            self._update_performance_tracking(data)
            if self.progress_tracker is not None:
                self.progress_tracker.on_step(result, self.portfolio_value)
        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")
