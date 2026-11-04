"""
Daily start and supervision of a live session (P.08.06). The session itself (one process per trading day, ending
after its last decision) is unchanged; the supervisor starts it on exchange trading days, restarts it after a crash
at most `max_restarts` times, and alerts (P.08.01) on every crash and when it gives up. Run by the compose service
`trader` (docker-compose.yml), whose own `restart: unless-stopped` covers a crash of the supervisor.

    sessions(start, end) -> [(date, close)]    exchange sessions, naive exchange time (NYSE calendar)
    run_session() -> exit code                 one session in a CHILD process: a hard crash (killed, out of memory)
                                               is seen like an exception, and the OS releases the session lock
    exit codes                                 0 = the session ended (normally or stopped by the operator: never
                                               restarted); ALREADY_RUNNING = another session holds the lock (not
                                               restarted, alerted once); REFUSED_DIRTY_TREE = the working tree
                                               is not a clean commit (P.08.11: not restarted, alerted once);
                                               anything else = crash -> restart

Alerts carry no account id: the strategy name, the exit code and what happens next. Details stay in the logs.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable, List, Optional, Tuple

ALREADY_RUNNING = 3                           # session.py exit code: SessionLockedError
REFUSED_DIRTY_TREE = 4                        # session.py exit code: run_manifest.DirtyWorkingTree (P.08.11)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupervisorConfig:
    start_time: time                          # launch time on a trading day (exchange time), before the open
    max_restarts: int                         # restarts after a crash, per day
    restart_delay_seconds: float
    # no (re)start this close to the close: the session's last decision is one bar before it, and a session started
    # after its last decision would wait for the NEXT day's session inside today's run
    no_start_before_close_minutes: float = 10.0
    heartbeat_seconds: float = 60.0           # longest sleep between two heartbeat writes

    @classmethod
    def from_config(cls, cfg: dict) -> "SupervisorConfig":
        return cls(start_time=datetime.strptime(cfg["start_time"], "%H:%M").time(),
                   max_restarts=int(cfg["max_restarts"]), restart_delay_seconds=float(cfg["restart_delay_seconds"]),
                   no_start_before_close_minutes=float(cfg["no_start_before_close_minutes"]),
                   heartbeat_seconds=float(cfg.get("heartbeat_seconds", 60.0)))


@dataclass
class DayOutcome:
    day: date
    status: str                               # 'ended' | 'already running' | 'gave up' | 'session closed' | 'stopped'
    attempts: int
    exit_codes: List[int]


class DailySupervisor:

    def __init__(self, name: str, config: SupervisorConfig, sessions: Callable[[date, date], List[Tuple[date, datetime]]],
                 run_session: Callable[[], int], now: Callable[[], datetime], notifier=None,
                 heartbeat_path: Optional[str] = None):
        self.name = name
        self.config = config
        self.sessions = sessions
        self.run_session = run_session
        self.now = now
        self.notifier = notifier                  # AlertNotifier or None (alerts logged only)
        self.heartbeat_path = heartbeat_path
        self.stop_event = threading.Event()
        self.state = "starting"

    # ------------------------------------------------------------------ calendar
    def next_session(self, now: datetime) -> Optional[Tuple[date, datetime, datetime]]:
        """(day, launch, close) of today's session if it has not closed yet, else of the next one."""
        for day, close in self.sessions(now.date(), now.date() + timedelta(days=10)):
            if close > now:
                return day, datetime.combine(day, self.config.start_time), close
        return None

    # ------------------------------------------------------------------ one day
    def run_day(self, day: date, close: datetime) -> DayOutcome:
        """Run today's session; restart it after a crash until max_restarts or the close."""
        codes: List[int] = []
        cutoff = close - timedelta(minutes=self.config.no_start_before_close_minutes)
        while not self.stop_event.is_set():
            if self.now() >= cutoff:
                if codes:
                    self._alert("session down", f"exit code {codes[-1]}; too close to the close for a restart",
                                "urgent")
                else:
                    logger.info(f"{self.name}: {day} too close to the close ({close:%H:%M}), not started")
                return DayOutcome(day, "session closed", len(codes), codes)
            self._heartbeat(f"session running ({day})", attempt=len(codes) + 1)
            code = self.run_session()
            codes.append(code)
            if code == 0 or self.stop_event.is_set():
                return DayOutcome(day, "ended" if code == 0 else "stopped", len(codes), codes)
            if code == ALREADY_RUNNING:
                self._alert("not started", "another session of this strategy is already running "
                            "(session lock): the supervisor did not start a second one", "high")
                return DayOutcome(day, "already running", len(codes), codes)
            if code == REFUSED_DIRTY_TREE:
                self._alert("not started", "the working tree has uncommitted changes: a live session trades "
                            "committed code only. Commit, then start it by hand (RUNBOOK section 2)", "high")
                return DayOutcome(day, "refused: dirty working tree", len(codes), codes)
            restarts = len(codes) - 1
            if restarts >= self.config.max_restarts:
                self._alert("session down for the day",
                            f"exit code {code}; {restarts} restart(s) used, no more today. Start it by hand after "
                            "checking the logs (RUNBOOK section 6)", "urgent")
                return DayOutcome(day, "gave up", len(codes), codes)
            resume = self.now() + timedelta(seconds=self.config.restart_delay_seconds)
            if resume >= cutoff:
                self._alert("session down", f"exit code {code}; too close to the close for a restart", "urgent")
                return DayOutcome(day, "session closed", len(codes), codes)
            self._alert("session crashed, restarting",
                        f"exit code {code}; restart {restarts + 1}/{self.config.max_restarts} in "
                        f"{self.config.restart_delay_seconds:.0f} s", "urgent")
            self._sleep_until(resume, f"restart {restarts + 1} at {resume:%H:%M:%S}")
        return DayOutcome(day, "stopped", len(codes), codes)

    # ------------------------------------------------------------------ loop
    def run_once(self) -> Optional[DayOutcome]:
        """Today only: None on a day without a session (or once today's has closed), else today's outcome.
        Waits for the launch time when started before it."""
        now = self.now()
        found = self.next_session(now)
        if found is None or found[0] != now.date():
            logger.info(f"{self.name}: no trading session today ({now:%Y-%m-%d}), nothing to start")
            self._heartbeat("no session today")
            return None
        day, launch, close = found
        self._sleep_until(launch, f"waiting for {launch:%Y-%m-%d %H:%M}")
        return None if self.stop_event.is_set() else self.run_day(day, close)

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            found = self.next_session(self.now())
            if found is None:
                raise RuntimeError("no exchange session in the next 10 days: calendar problem")
            day, launch, close = found
            logger.info(f"{self.name}: next session {day}, start {launch:%H:%M}, close {close:%H:%M}")
            self._sleep_until(launch, f"next session {day} at {launch:%H:%M}")
            if self.stop_event.is_set():
                break
            outcome = self.run_day(day, close)
            logger.info(f"{self.name}: {day} {outcome.status} after {outcome.attempts} run(s), exit codes "
                        f"{outcome.exit_codes}")
            # never start the same day twice: wait for its close before looking for the next session
            self._sleep_until(max(close, self.now()), f"{day} done ({outcome.status})")
        self._heartbeat("stopped")

    def stop(self) -> None:
        self.stop_event.set()

    # ------------------------------------------------------------------ helpers
    def _sleep_until(self, when: datetime, state: str) -> None:
        while not self.stop_event.is_set():
            left = (when - self.now()).total_seconds()
            self._heartbeat(state)
            if left <= 0:
                return
            self.stop_event.wait(min(left, self.config.heartbeat_seconds))

    def _alert(self, title: str, message: str, priority: str) -> None:
        logger.error(f"{self.name} {title}: {message}")
        if self.notifier is not None:
            self.notifier.event(title, message, priority=priority)

    def _heartbeat(self, state: str, **extra) -> None:
        """<heartbeat_path> = what the supervisor is doing, rewritten at least every heartbeat_seconds (the compose
        healthcheck reads its age)."""
        self.state = state
        if not self.heartbeat_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.heartbeat_path)), exist_ok=True)
            tmp = self.heartbeat_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"name": self.name, "state": state, "at": f"{self.now():%Y-%m-%d %H:%M:%S}",
                           "pid": os.getpid(), **extra}, f)
            os.replace(tmp, self.heartbeat_path)
        except OSError as e:
            logger.warning(f"heartbeat not written: {e}")


def heartbeat_age_seconds(path: str) -> Optional[float]:
    """Age of the heartbeat file (compose healthcheck); None when it does not exist."""
    try:
        return max(0.0, datetime.now().timestamp() - os.path.getmtime(path))
    except OSError:
        return None
