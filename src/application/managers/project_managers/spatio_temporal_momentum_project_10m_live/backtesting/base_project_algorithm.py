"""
Spatio-Temporal Momentum algorithm for the Misbuffet engine — LIVE deployment (paper or live IBKR account).

initialize():
    refuses to run outside live mode (this project's book is a live book: a backtest must never reset it);
    portfolio registration (live: the existing book is resumed); live stack (build_live_stack through the
    runner's factory: order ledger, start-up recovery, reconciliation, pre-trade gate); then the trainer wires the
    STMTradingCycle onto this algorithm's MarketDataService and MarketDataHistoryService (frontier).

on_data(data):
    cycle.step(bar time)  -> frontier advance, data update, retrain when due,
                             scores from the model valid for the bar
    set_holdings(weights) -> UnifiedPortfolioManager: ledger drain, recovery, reconciliation, then orders through
                             the pre-trade gate to IBKR

Nothing here knows about PyTorch or IBKR.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.config import get_config
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.shortable_inventory import (
    ShortableInventory,
)
from src.application.services.data.entities.factor import preloaded_coverage
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm
from src.application.services.timing.step_timings import StepTimings, record as record_step_timings
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.order.pre_trade_risk import PriceSnapshot


TIMINGS_FILE = "timings.csv"            # per-bar time spent in slice / cycle / orders / valuation (results_dir)


class Algorithm(BaseProjectAlgorithm):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cycle = None
        self.cycle_results: List[Any] = []
        self.progress_tracker = None  # optional STMProgressTracker (Flask dashboard)
        self.project_config: Optional[Dict[str, Any]] = None       # the runner's config (rolling dates)
        self.live_stack_factory: Optional[Callable[["Algorithm"], Any]] = None
        self.live_stack = None
        self.connection_guard = None          # LiveConnectionGuard, set by the runner (reconnect + rebuild, P.04.07)
        self.shortable: Optional[ShortableInventory] = None       # set by the runner (config live.shortable_check)
        self._last_bars: Dict[str, tuple] = {}                    # ticker -> (close, bar close time) known at the step

    def initialize(self):
        super().initialize()
        if not getattr(self, "live_mode", False):
            raise RuntimeError("spatio_temporal_momentum_project_10m_live trades a live book: run it through "
                               "LiveRunner.run_live (live mode), never as a backtest")
        self.config = self.project_config or get_config()
        if self._entity_service is None:
            raise RuntimeError("No entity service injected — cannot register the live book")
        portfolio_entity = self.register_portfolio(portfolio_config=self.config.get('Portfolio', {}))
        if not portfolio_entity:
            raise RuntimeError(f"Live book {self.config['Portfolio']['name']!r} could not be registered")
        self.portfolio_entity = portfolio_entity
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']

        # Order path before anything slow (history import, factors): a wrong account / missing connection fails now
        if self.live_stack_factory is None:
            raise RuntimeError("No live stack factory injected — orders would have no ledger, recovery or gate")
        self.live_stack = self.live_stack_factory(self)

        if getattr(self, 'trainer', None) is None:
            raise RuntimeError("No trainer injected — Spatio-Temporal Momentum cycle disabled")
        self.cycle = self.trainer.build_cycle(
            market_data_service=self._market_data_service,
            history_service=self._market_data_history_service,
            factory=self.repository_factory,
            log=self.progress_tracker.log if self.progress_tracker is not None else self.log,
        )
        # the engine builds its data slice for these: only the tickers with an entity (an IBKR contract)
        self.universe = {CompanyShare: list(self.cycle.ticker_to_entity)}

    def before_step(self, step_time):
        """Called by the engine (live clock) once the step is due, BEFORE it builds the data slice: import the bar
        that just closed (one '1 D' request per ticker) and mark the series complete up to the step, so the slice,
        the cycle, the valuation and the order pricing read locally instead of each asking IBKR for a week of bars
        (paper smoke run 2026-10-29: 88 requests and 11 minutes for one decision)."""
        if self.connection_guard is not None:
            stack = self.connection_guard.check(self.live_stack)
            if stack is not None:
                self.live_stack = stack
        if self.cycle is None or self.cycle.data_updater is None:
            return
        status = self.cycle.data_updater(step_time)
        failed = sorted(t for t, ok in (status or {}).items() if not ok)
        if failed:
            self.logger.warning(f"{step_time}: new bar not imported for {failed}")
        preloaded_coverage.extend(step_time)
        self._last_bars = self.latest_closed_bars(step_time)

    def latest_closed_bars(self, step_time) -> Dict[str, tuple]:
        """{ticker: (close, bar close time)} of the newest bar stored and closed at ``step_time``, read through the
        cycle's frontier. The bar time is the real one: on a login without real-time data IBKR serves 10-minute
        bars ~10-15 minutes late (2026-10-29), so the newest bar is often the one BEFORE the step's bar."""
        step = pd.Timestamp(step_time)
        minutes = self.cycle.config.bar_minutes
        self.cycle.history_service.set_frontier(step.to_pydatetime())
        id_to_ticker = {eid: t for t, eid in self.cycle.ticker_to_entity.items()}
        closes = self.cycle.reader.load_close_panel(id_to_ticker, start=step.normalize() - pd.Timedelta(days=5))
        out = {}
        for ticker in getattr(closes, "columns", []):
            series = closes[ticker].dropna()
            if len(series):
                out[ticker] = (float(series.iloc[-1]),
                               (pd.Timestamp(series.index[-1]) + pd.Timedelta(minutes=minutes)).to_pydatetime())
        return out

    def bar_price(self, symbol: str) -> PriceSnapshot:
        """PAPER pre-trade gate prices (build_live_stack bar_prices): the close of the newest stored bar known at the
        step, dated at that bar's REAL close — no IBKR request per order; the gate's quote age limit judges it."""
        bar = self._last_bars.get(symbol)
        if bar is None:
            return PriceSnapshot(None, None, unusable_reason=f"no stored 10-minute bar for {symbol} at this step")
        tz = ZoneInfo(self.config['live']['exchange_timezone'])
        return PriceSnapshot(bar[0], bar[1].replace(tzinfo=tz))

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
            self.cycle_results.append(result)
            if result.retrained:
                self.log(f"STM model retrained at bar {result.session} (artifact {result.artifact_id})")
            weights = dict(result.weights or {})
            if weights and self.shortable is not None:
                weights, cut = self.shortable.restrict(weights)
                if cut:
                    self.logger.warning(f"{bar_time}: IBKR cannot lend {cut}: short targets set to 0")
            if weights and self._unified_portfolio_manager:
                with timings.section("orders"):
                    placed = self._unified_portfolio_manager.set_holdings(
                        {CompanyShare: [{'name': t, 'weight': w} for t, w in weights.items()]},
                        data=data,
                        max_gross_weight=self.config.get('gross_exposure_cap', 1.0),
                    )
                refused = sorted(t for t, ok in (placed or {}).items() if not ok)
                if refused:
                    self.logger.warning(f"{bar_time}: orders not placed for {refused}")
            elif not weights:
                self.log(f"No STM position change at {bar_time}: {result.note}")
            with timings.section("valuation"):
                self._update_portfolio_value(data)
                self._update_performance_tracking(data)
            line = record_step_timings(timings, os.path.join(self.config['results_dir'], TIMINGS_FILE))
            self.logger.info(line)
            if self.progress_tracker is not None:
                self.progress_tracker.log(line)
                self.progress_tracker.on_step(result, self.portfolio_value)
        except Exception as e:
            self.logger.error(f"Error in on_data at {getattr(data, 'time', None)}: {e!r}")
