"""
Monthly model-filtered dispersion algorithm for the Misbuffet engine (backtest).

initialize():
    portfolio registration (Misbuffet), then the trainer wires the DispersionTradingCycle onto this algorithm's
    MarketDataService, MarketDataHistoryService (frontier) and repository factory.

on_data(data):
    cycle.step(bar time)  -> settle the expiring trade / open the next one at the latest known close
    set_holdings(TargetPortfolio)   -> UnifiedPortfolioManager (orders, transactions, positions): option contracts,
                                       the DIA calls as ETFShareOption, the members' calls as CompanyShareOption
    portfolio value / performance tracking (BaseProjectAlgorithm)

_resolve_asset_price(ticker):
    an option leg of the cycle -> its MODELLED price at the latest known close (its intrinsic value once settled):
    the price set_holdings fills at and the daily valuation reads. Anything else -> the engine's own price.
"""

import logging
import os
from typing import Any, List, Optional

from src.application.managers.project_managers.etf_dispersion_stm_project.config import get_config
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm
from src.application.services.timing.step_timings import StepTimings, record as record_step_timings

TIMINGS_FILE = "timings.csv"            # per-bar time spent in cycle / orders / valuation (results_dir)


class Algorithm(BaseProjectAlgorithm):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cycle = None
        self.step_results: List[Any] = []
        self.value_history: List[tuple] = []
        self.run_status = None          # optional RunStatus (the /dispersion-stm page)

    def _log(self, message: str) -> None:
        self.log(message)
        if self.run_status is not None:
            self.run_status.log(message)

    def initialize(self):
        super().initialize()
        self.config = get_config()
        if self._entity_service:
            portfolio_entity = self.register_portfolio(portfolio_config=self.config.get('Portfolio', {}))
            if portfolio_entity:
                self.portfolio_entity = portfolio_entity
            else:
                self.warning("Failed to register the dispersion portfolio")
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']
        if getattr(self, 'trainer', None) is not None and self._entity_service is not None:
            self.cycle = self.trainer.build_cycle(
                market_data_service=self._market_data_service,
                history_service=self._market_data_history_service,
                factory=self.repository_factory,
                log=self._log,
            )
        else:
            self.warning("No trainer / entity service injected - dispersion cycle disabled")

    def _resolve_asset_price(self, ticker: str) -> Optional[float]:
        if self.cycle is not None and self.cycle.is_leg(ticker):
            return self.cycle.option_price(ticker)
        return super()._resolve_asset_price(ticker)

    def on_data(self, data):
        try:
            if not self.initialized or self.cycle is None:
                return
            bar_time = getattr(data, 'time', None) or getattr(self, 'time', None)
            if bar_time is None:
                return
            timings = getattr(self, "step_timings", None) or StepTimings(label=str(bar_time))
            with timings.section("cycle"):
                result = self.cycle.step(bar_time)
            self.step_results.append(result)
            if result.targets and self._unified_portfolio_manager:
                with timings.section("orders"):
                    # TargetPortfolio (contracts; legs settled this step at 0) -> rebalancing -> TradeManager
                    sent = self._unified_portfolio_manager.set_holdings(
                        result.target_portfolio, data=data, liquidate_unlisted=False, max_gross_weight=None)
                refused = sorted(s for s, ok in (sent or {}).items() if ok is False)
                if refused:
                    self._log(f"[DISP-STM] {bar_time}: orders refused for {refused}")
            with timings.section("valuation"):
                self._update_portfolio_value(data)
                self._update_performance_tracking(data)
            self.value_history.append((bar_time, float(self.portfolio_value or 0.0)))
            line = record_step_timings(timings, os.path.join(self.config['results_dir'], TIMINGS_FILE))
            self.logger.info(line)
            if self.run_status is not None:
                self.run_status.on_step(self.cycle, result, self.portfolio_value)
        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")
            self._log(f"[DISP-STM] on_data error at {getattr(data, 'time', '?')}: {e!r}")
