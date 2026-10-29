"""
SpatioTemporalMomentum10mLiveProjectManager — runs the intraday Spatio-Temporal Momentum strategy LIVE (paper
account by default) through the Misbuffet engine and build_live_stack.

    manager = SpatioTemporalMomentum10mLiveProjectManager()
    manager.check()     # connect, register / resume the book, build the live stack, start-up recovery; no order
    manager.run()       # one session: from the next 10-minute decision to the session's last one (15:50)

Everything that decides happens inside the engine, bar by bar (Algorithm.on_data -> STMTradingCycle.step), with
every read clipped by the frontier; the LiveClock holds each step until its bar has closed. The manager only
picks the session window, connects the order connection and launches the run.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as project_config
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting.base_project_algorithm import (
    TIMINGS_FILE,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting.live_runner import (
    LiveRunner,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
    STMProgressTracker,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_report_store import progress_path
from src.application.services.misbuffet.live.live_clock import LiveClock
from src.application.services.timing.step_timings import summarise as summarise_step_timings

DASHBOARD_URL = "http://127.0.0.1:5000/stm/?project=10m_live"      # decisions of the running session
MONITOR_URL = "http://127.0.0.1:5000/monitor/trading"              # orders, executions, controls, discrepancies


def session_window(now: datetime, config: Dict[str, Any], calendar=None) -> Tuple[datetime, datetime]:
    """(first decision, last decision) of the session to run, in naive exchange time.

    Today's session when its last decision is still ahead (first decision = the next 10-minute step whose bar
    will have closed), otherwise the next exchange session. Early closes end the session earlier (last decision =
    close - one bar). ``calendar(start_date, end_date)`` -> DataFrame of market_open / market_close (naive exchange
    time); default the NYSE calendar."""
    interval = config['config_interval']
    minutes = int(interval['custom_interval_minutes'])
    first = datetime.strptime(interval['session_start'], "%H:%M").time()
    last = datetime.strptime(interval['session_end'], "%H:%M").time()
    grace = timedelta(seconds=config['live'].get('bar_close_grace_seconds', 0))
    sessions = (calendar or _nyse_sessions)(now.date(), now.date() + timedelta(days=10))
    for day, close in sessions:
        end = min(datetime.combine(day, last), close - timedelta(minutes=minutes))
        start = datetime.combine(day, first)
        if end + grace < now:
            continue                                            # this session's last decision has passed
        if start + grace < now:                                 # session under way: next step not yet due
            step = pd.Timestamp(now - grace).ceil(f"{minutes}min").to_pydatetime()
            start = max(start, step)
        return start, end
    raise RuntimeError(f"no exchange session in the 10 days after {now}")


def _nyse_sessions(start, end):
    import pandas_market_calendars as mcal
    schedule = mcal.get_calendar("NYSE").schedule(start_date=start, end_date=end)
    tz = project_config.LIVE['exchange_timezone']
    return [(idx.date(), row.market_close.tz_convert(tz).tz_localize(None).to_pydatetime())
            for idx, row in schedule.iterrows()]


class SpatioTemporalMomentum10mLiveProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, database_service=None, progress=None,
                 broker=None, clock: Optional[LiveClock] = None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or project_config.get_config()
        self.stm_config = project_config.build_stm_configuration(self.config)
        if database_service is None:
            from src.application.services.database_service.database_service import DatabaseService
            database_service = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
            database_service.set_ext_db()
        self.setup_database_service(database_service)
        self.results_dir = self.config['results_dir']
        if progress is None:
            progress = STMProgressTracker(persist_path=progress_path(self.results_dir))
        elif not progress.persist_path:
            progress.persist_path = progress_path(self.results_dir)
        self.progress = progress
        live = self.config['live']
        self.clock = clock or LiveClock(live['exchange_timezone'], grace_seconds=live['bar_close_grace_seconds'],
                                        max_lag_seconds=live['max_step_lag_seconds'])
        self.broker = broker
        self.runner = LiveRunner(self.database_service)
        self.runner.progress_tracker = progress
        self.results: Dict[str, Any] = {}

    # ------------------------------------------------------------------ broker
    def connect_broker(self):
        """The order connection (its own client id; the data connection is the repository factory's)."""
        if self.broker is not None and self.broker.is_connected():
            return self.broker
        from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import (
            InteractiveBrokersBroker,
        )
        live = self.config['live']
        self.broker = InteractiveBrokersBroker({'host': live['host'], 'port': live['port'],
                                                'client_id': live['client_id'], 'paper_trading': True})
        if not self.broker.connect():
            raise RuntimeError(f"IBKR order connection failed ({live['host']}:{live['port']}, client "
                               f"{live['client_id']}): is TWS / IB Gateway running with the API enabled?")
        return self.broker

    def session_config(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """The config with this session's dates: first / last decision and the rolling history start."""
        now = now or self.clock.exchange_now()
        start, end = session_window(now, self.config)
        history_start = (pd.Timestamp(start).normalize()
                         - pd.Timedelta(days=int(self.config['history_calendar_days'])))
        return {**self.config, 'backtest_start': start, 'backtest_end': end,
                'price_history_start': history_start.strftime('%Y-%m-%d')}

    # ------------------------------------------------------------------ check (no order)
    def check(self) -> Dict[str, Any]:
        """Connect, resume the live book, build the live stack and run start-up recovery — no order, no data
        import, no model. Returns LiveStack.status()."""
        broker = self.connect_broker()
        runner = self.runner
        runner.config, runner.broker = self.session_config(), broker
        if not runner.setup_components(runner.config):
            raise RuntimeError("Component setup failed")
        algorithm = runner.create_algorithm_instance()
        algorithm.set_live_mode(True)                      # live: the book is resumed, never reset
        if not algorithm.register_portfolio(portfolio_config=runner.config['Portfolio']):
            raise RuntimeError("live book could not be registered")
        stack = None
        try:
            stack = runner.build_stack(algorithm)
            return stack.status()
        finally:
            if stack is not None:
                stack.shutdown("check", cancel_working=False)
            broker.disconnect()

    # ------------------------------------------------------------------ run
    def run(self) -> Dict[str, Any]:
        """One session live: the next decision .. the session's last decision. Ctrl+C or clock.request_stop()
        ends it early; working orders are cancelled at the end (config live.cancel_working_on_shutdown)."""
        config = self.session_config()
        start, end = config['backtest_start'], config['backtest_end']
        live = self.config['live']
        bars = int((end - start).total_seconds() // (60 * self.stm_config.bar_minutes)) + 1
        self.progress.start("live", bars_total=bars)
        self.progress.log(f"[live] account {live['account']} strategy {live['strategy']} decisions "
                          f"{start:%Y-%m-%d %H:%M} .. {end:%H:%M} — dashboard {DASHBOARD_URL}, orders {MONITOR_URL}")
        print(f"Live STM 10m: account {live['account']}, decisions {start} .. {end}. "
              f"Track: {DASHBOARD_URL} and {MONITOR_URL}", flush=True)
        timings_csv = os.path.join(self.results_dir, TIMINGS_FILE)
        if os.path.exists(timings_csv):
            os.remove(timings_csv)
        broker = self.connect_broker()
        try:
            self.progress.phase("live session (train / score / trade on each closed bar)")
            self.results = self.runner.run_live(config, broker, self.clock)
        except BaseException as e:
            self.progress.fail(repr(e))
            raise
        finally:
            summary = summarise_step_timings(timings_csv)
            if summary:
                self.logger.info(summary)
                self.progress.log(summary)
            broker.disconnect()
        self.progress.log(f"[live] ended: {self.results['reason']}, {self.results['decisions']} decision(s), "
                          f"{len(self.results['skipped_steps'])} step(s) skipped; still open: "
                          f"{(self.results['shutdown'] or {}).get('open_orders')}")
        self.progress.complete()
        return self.results

    def stop(self, reason: str = "stop requested") -> None:
        """Ends the run before its next step (from another thread, e.g. a dashboard or a signal handler)."""
        self.clock.request_stop(reason)
