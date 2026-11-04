"""
P.08.06 daily start and supervision of the STM 10m live session (compose service `trader`, RUNBOOK section 2).

    python -m src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.supervise daily
        forever: start the session at config supervisor.start_time on every NYSE trading day, restart a crashed
        session at most supervisor.max_restarts times, alert every crash (ntfy, P.08.01)
    ... supervise once      today only (waits for the start time); exits 0 at once on a day without a session
    ... supervise session   one session = SpatioTemporalMomentum10mLiveProjectManager().run(); the supervisor runs
                            it as a child process. SIGTERM / SIGINT end it cleanly before its next step
    ... supervise health    compose healthcheck: exit 0 while the supervisor's heartbeat is fresh

Exit codes of `session`: 0 ended (normally or stopped), ALREADY_RUNNING another session holds the lock, 1 crash.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as project_config
from src.application.services.misbuffet.live.daily_supervisor import (
    ALREADY_RUNNING,
    DailySupervisor,
    SupervisorConfig,
    heartbeat_age_seconds,
)

MODULE = "src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.supervise"
logger = logging.getLogger("stm10m_live_supervisor")


def heartbeat_path(config) -> str:
    return os.path.join(config['results_dir'], f"{config['live']['strategy']}.supervisor.json")


def exchange_now(config) -> datetime:
    return datetime.now(ZoneInfo(config['live']['exchange_timezone'])).replace(tzinfo=None)


def notifier(config):
    """Supervisor alerts through ntfy (NTFY_TOPIC); None (logged) without a topic."""
    from src.application.services.monitoring.alert_notifier import AlertNotifier, sender_from_env
    sender = sender_from_env()
    if sender is None:
        logger.warning("NTFY_TOPIC not set: supervisor alerts are NOT pushed (logs only)")
        return None
    mode = "paper" if str(config['live']['account']).startswith("D") else "LIVE"
    return AlertNotifier(sender, source=f"{config['live']['strategy']} {mode}")


class ChildSession:
    """Runs `supervise session` in a child process; stop() forwards SIGTERM so the session ends cleanly."""

    def __init__(self, argv=None):
        self.argv = argv or [sys.executable, "-m", MODULE, "session"]
        self.process: Optional[subprocess.Popen] = None

    def __call__(self) -> int:
        self.process = subprocess.Popen(self.argv)
        try:
            return self.process.wait()
        finally:
            self.process = None

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()


def build_supervisor(config=None, run_session: Optional[Callable[[], int]] = None, now=None, sessions=None,
                     alerts="env") -> DailySupervisor:
    config = config or project_config.get_config()
    if sessions is None:
        from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
            _nyse_sessions as sessions,
        )
    return DailySupervisor(
        name=config['live']['strategy'],
        config=SupervisorConfig.from_config(config['supervisor']),
        sessions=sessions,
        run_session=run_session or ChildSession(),
        now=now or (lambda: exchange_now(config)),
        notifier=notifier(config) if alerts == "env" else alerts,
        heartbeat_path=heartbeat_path(config),
    )


def run_session() -> int:
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
        SpatioTemporalMomentum10mLiveProjectManager,
    )
    from src.application.services.misbuffet.live.session_lock import SessionLockedError
    manager = SpatioTemporalMomentum10mLiveProjectManager()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: manager.stop("stopped by the supervisor / operator"))
    try:
        manager.run()
    except SessionLockedError as e:
        logger.error(str(e))
        return ALREADY_RUNNING
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="supervise")
    parser.add_argument("command", choices=("daily", "once", "session", "health"))
    args = parser.parse_args(argv)
    config = project_config.get_config()
    if args.command == "session":
        return run_session()
    if args.command == "health":
        age = heartbeat_age_seconds(heartbeat_path(config))
        limit = 3 * float(config['supervisor'].get('heartbeat_seconds', 60))
        return 0 if age is not None and age <= limit else 1

    supervisor = build_supervisor(config)

    def on_signal(*_):
        supervisor.stop()
        if isinstance(supervisor.run_session, ChildSession):
            supervisor.run_session.stop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, on_signal)
    if args.command == "once":
        outcome = supervisor.run_once()
        return 0 if outcome is None or outcome.status in ("ended", "stopped") else 1
    supervisor.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
