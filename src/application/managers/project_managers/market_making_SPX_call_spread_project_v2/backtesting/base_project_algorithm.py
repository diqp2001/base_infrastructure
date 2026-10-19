"""
SPX call spread market-making algorithm for the Misbuffet engine (backtest and live).

initialize():
    portfolio registration (Misbuffet), then the trainer wires the
    SPXCallSpreadTradingCycle onto this algorithm's MarketDataService,
    MarketDataHistoryService (frontier) and repository factory.

on_data(data):
    cycle.step(bar time, data, portfolio gateway)
        -> factor refresh at the bar, option entry, greeks, delta hedge
    portfolio value / performance tracking (BaseProjectAlgorithm)

Nothing SPX-specific is decided here; the same cycle runs when the engine is live.
"""

import logging
from typing import Any, List, Tuple

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.config import get_config
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm


class PortfolioGateway:
    """What the trading cycle needs from the portfolio: current quantity and target holdings."""

    def __init__(self, unified_portfolio_manager):
        self.upm = unified_portfolio_manager

    def quantity(self, ticker: str) -> int:
        return self.upm._get_current_position_qty(ticker)

    def set_holdings(self, targets, data=None):
        return self.upm.set_holdings(targets, data=data)

    def session(self):
        return self.upm.portfolio_repo.session


class Algorithm(BaseProjectAlgorithm):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cycle = None
        self.gateway = None
        self.cycle_results: List[Any] = []
        self.value_history: List[Tuple[Any, float]] = []   # (bar time, portfolio value) every bar
        self.progress_tracker = None  # optional MMProgressTracker (progress.json)

    def initialize(self):
        super().initialize()
        self.config = get_config()
        portfolio_config = self.config.get('Portfolio', {})
        if self._entity_service:
            portfolio_entity = self.register_portfolio(portfolio_config=portfolio_config)
            if portfolio_entity:
                self.portfolio_entity = portfolio_entity
            else:
                self.warning("Failed to register SPX call spread v2 portfolio")
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']

        if (getattr(self, 'trainer', None) is not None and self._entity_service is not None
                and self._unified_portfolio_manager is not None):
            self.gateway = PortfolioGateway(self._unified_portfolio_manager)
            self.cycle = self.trainer.build_cycle(
                market_data_service=self._market_data_service,
                history_service=self._market_data_history_service,
                factory=self.repository_factory,
                session_provider=self.gateway.session,
                log=self.progress_tracker.log if self.progress_tracker is not None else self.log,
                strategy=self.strategy,
            )
        else:
            self.warning("No trainer / entity service / portfolio manager — SPX v2 trading cycle disabled")

    def on_data(self, data):
        try:
            if not self.initialized or self.cycle is None:
                return
            bar_time = getattr(data, 'time', None) or getattr(self, 'time', None)
            if bar_time is None:
                return
            result = self.cycle.step(bar_time, data, self.gateway)
            self.cycle_results.append(result)
            if result.error:
                self.logger.error(f"SPX v2 cycle at {bar_time}: {result.error}")
            self._update_portfolio_value(data)
            self._update_performance_tracking(data)
            self.value_history.append((bar_time, self.portfolio_value))
            if self.progress_tracker is not None:
                self.progress_tracker.on_step(result, self.portfolio_value)
            if self._is_end_of_day(data):
                self._log_daily_summary()
        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")
        finally:
            self._save_data_report()

    def _save_data_report(self) -> None:
        """Rewrite results_dir/data_report.txt after every bar (missing data so far and why)."""
        report = getattr(getattr(self.cycle, 'position_book', None), 'report', None)
        if report is None:
            return
        try:
            report.bars = len(self.cycle_results)
            report.save()
        except Exception as e:
            self.logger.error(f"Could not write the data report: {e}")
